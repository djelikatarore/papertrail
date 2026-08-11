"""One-off maintenance script: regenerates the Contribution/Methodology/Key
Results/Limitations summary for every READY paper whose stored summary still
reflects the old, short format (pre-2026-08-07 prompt: 1-3 sentences per
block) or is missing/incomplete for any block — via
summary_service.generate_summary, the exact same call the real upload
pipeline makes (paper_router.py), not a separate copy. Reuses each paper's
already-stored TextBlock chunks rather than re-extracting/re-chunking the
PDF — this only touches the summary fields, nothing else about the paper.

A paper qualifies for backfill if the shortest of its four summary fields is
under SHORT_SUMMARY_THRESHOLD_CHARS chars (or missing) — comfortably above
the old format's typical 150-900 char range and below the new format's
1000-2400+ char range, so it reliably catches stale pre-fix summaries without
touching ones already regenerated under the new prompt.

Run from backend/ with the venv active:
    python scripts/backfill_summary_lengths.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: F401
from app.database import SessionLocal
from app.models.models import Paper, TextBlock
from app.services.llm_service import LlmError
from app.services.summary_service import generate_summary, is_real_summary_content

SHORT_SUMMARY_THRESHOLD_CHARS = 900
FIELD_NAMES = ["contribution", "methodology", "key_results", "limitations"]


def _shortest_field_length(p: Paper) -> int:
    fields = [p.contribution, p.methodology, p.key_results, p.limitations]
    return min(len(f or "") for f in fields)


async def main() -> None:
    db = SessionLocal()
    try:
        candidates = [
            p
            for p in db.query(Paper).filter(Paper.status == "READY").order_by(Paper.id).all()
            if _shortest_field_length(p) < SHORT_SUMMARY_THRESHOLD_CHARS
        ]
        print(f"Regenerating summaries for {len(candidates)} papers with a short/incomplete block...")

        for p in candidates:
            safe_title = (p.title or p.filename or "")[:60].encode("ascii", "replace").decode("ascii")
            blocks = db.query(TextBlock).filter(TextBlock.paper_id == p.id).order_by(TextBlock.id).all()
            if not blocks:
                print(f"  paper {p.id} ({safe_title!r}): no stored text chunks, skipping")
                continue

            chunks = [(b.section_reference or "Unknown", b.text) for b in blocks]
            before = (len(p.contribution or ""), len(p.methodology or ""), len(p.key_results or ""), len(p.limitations or ""))

            try:
                summary, flagged_fields = await generate_summary(chunks, p.review_type)
            except LlmError as exc:
                print(f"  paper {p.id} ({safe_title!r}): LLM call failed, skipping: {exc}")
                continue

            # A regenerated block can come back empty, or as the model's own
            # "Not clearly stated" placeholder, even though the paper already
            # had real, if shorter, content there — confirmed happening on
            # this exact script's first two runs (7 papers lost blocks to an
            # empty result; paper 88 later lost 1093 chars of real
            # key_results to the placeholder specifically, because a plain
            # truthiness check treated that non-empty string as an
            # "improvement"). is_real_summary_content excludes both, so
            # neither can ever look better than existing content.
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

            after = (len(p.contribution or ""), len(p.methodology or ""), len(p.key_results or ""), len(p.limitations or ""))
            notes = []
            if final_flagged:
                notes.append(f"flagged: {final_flagged}")
            if kept_stale:
                notes.append(f"kept previous value for: {kept_stale}")
            note = f", {'; '.join(notes)}" if notes else ""
            print(f"  paper {p.id} ({safe_title!r}): {before} -> {after}{note}")

        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
