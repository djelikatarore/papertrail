"""One-off maintenance script: normalizes typeset ligature characters
(U+FB00-FB06, e.g. "ﬃ" -> "ffi") in already-stored Paper.raw_text,
Paper.title, and TextBlock.text — extract_text()/extract_title() in
pdf_service.py now do this at extraction time (see _normalize_ligatures),
but rows extracted before that fix still hold the raw ligature codepoints,
which never byte-match a citation an LLM writes back in plain ASCII (e.g.
stored "coeﬃcient" vs. a citation naming "Coefficient"), wrongly rejecting
an otherwise well-grounded summary claim.

After normalizing, regenerates the summary for any affected paper that
currently has an empty/flagged block, via summary_service.generate_summary
— same guard as backfill_summary_lengths.py: a regenerated block that comes
back empty never overwrites existing content.

Run from backend/ with the venv active:
    python scripts/backfill_ligature_normalization.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: F401
from app.database import SessionLocal
from app.models.models import Paper, TextBlock
from app.services.llm_service import LlmError
from app.services.pdf_service import _normalize_ligatures
from app.services.summary_service import generate_summary, is_real_summary_content

FIELD_NAMES = ["contribution", "methodology", "key_results", "limitations"]
LIGATURES = ["ﬀ", "ﬁ", "ﬂ", "ﬃ", "ﬄ", "ﬅ", "ﬆ"]


def _has_ligature(text: str | None) -> bool:
    return bool(text) and any(ch in text for ch in LIGATURES)


async def main() -> None:
    db = SessionLocal()
    try:
        affected_paper_ids: set[int] = set()

        papers = db.query(Paper).filter(Paper.raw_text.isnot(None)).all()
        for p in papers:
            changed = False
            if _has_ligature(p.raw_text):
                p.raw_text = _normalize_ligatures(p.raw_text)
                changed = True
            if _has_ligature(p.title):
                p.title = _normalize_ligatures(p.title)
                changed = True
            if changed:
                affected_paper_ids.add(p.id)

        blocks = db.query(TextBlock).all()
        for b in blocks:
            if _has_ligature(b.text):
                b.text = _normalize_ligatures(b.text)
                affected_paper_ids.add(b.paper_id)

        db.commit()
        print(f"Normalized ligatures for {len(affected_paper_ids)} papers: {sorted(affected_paper_ids)}")

        candidates = [
            p
            for p in db.query(Paper).filter(Paper.id.in_(affected_paper_ids), Paper.status == "READY").all()
            if any(not is_real_summary_content(getattr(p, f)) for f in FIELD_NAMES)
        ]
        print(f"Regenerating summaries for {len(candidates)} of those with an empty/placeholder block...")

        for p in candidates:
            safe_title = (p.title or p.filename or "")[:60].encode("ascii", "replace").decode("ascii")
            chunks_qs = db.query(TextBlock).filter(TextBlock.paper_id == p.id).order_by(TextBlock.id).all()
            chunks = [(b.section_reference or "Unknown", b.text) for b in chunks_qs]
            before = tuple(len(getattr(p, f) or "") for f in FIELD_NAMES)

            try:
                summary, flagged_fields = await generate_summary(chunks, p.review_type)
            except LlmError as exc:
                print(f"  paper {p.id} ({safe_title!r}): LLM call failed, skipping: {exc}")
                continue

            kept_stale = []
            for name in FIELD_NAMES:
                new_value = summary[name]
                if is_real_summary_content(new_value):
                    setattr(p, name, new_value)
                elif getattr(p, name):
                    kept_stale.append(name)

            final_flagged = [f for f in flagged_fields if f not in kept_stale]
            p.summary_flagged_fields = ", ".join(final_flagged) if final_flagged else None
            db.commit()

            after = tuple(len(getattr(p, f) or "") for f in FIELD_NAMES)
            notes = []
            if final_flagged:
                notes.append(f"still flagged: {final_flagged}")
            if kept_stale:
                notes.append(f"kept previous for: {kept_stale}")
            note = f" ({'; '.join(notes)})" if notes else " (fully clean)"
            print(f"  paper {p.id} ({safe_title!r}): {before} -> {after}{note}")

        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
