"""One-off maintenance script: (re)computes citation_count for every READY
paper with a title, via citation_service.get_citation_count (Semantic
Scholar, falling back to CrossRef) — same fallback logic used by the real
upload pipeline in paper_router.py, not a separate copy. A fresh result only
overwrites what's already stored when citation_service.should_replace_citation
says it's actually an improvement (never lets a rate-limited attempt wipe out
a known count with None, and never lets a CrossRef fallback result overwrite
an existing Semantic Scholar one — both observed happening in practice before
this guard existed). Does not touch anything else about the paper — no
re-extraction, no re-chunking, no re-running summary/keywords/paper-type.

Run from backend/ with the venv active:
    python scripts/backfill_citation_counts.py
"""

import asyncio
import os
import sys

# Makes `app` importable when run directly as a script (python
# scripts/backfill_citation_counts.py) rather than as a package — matches how
# every other entry point in this project expects to run from backend/, but a
# plain script invocation doesn't put backend/ on sys.path by itself.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importing app.main (rather than just app.database/app.models.models)
# registers every model class up front — SQLAlchemy needs that to resolve the
# string-based relationship() references between them (e.g. Paper -> Project),
# which otherwise fail with "expression 'Project' failed to locate a name"
# the moment this script queries anything.
from app.main import app  # noqa: F401
from app.database import SessionLocal
from app.models.models import Paper
from app.services.citation_service import get_citation_count, should_replace_citation
from app.services.crossref_service import CrossrefLookupError


async def main() -> None:
    db = SessionLocal()
    try:
        papers = (
            db.query(Paper)
            .filter(Paper.status == "READY", Paper.title.isnot(None))
            .order_by(Paper.id)
            .all()
        )
        print(f"Refreshing citation_count for {len(papers)} papers via Semantic Scholar (CrossRef fallback)...")

        for p in papers:
            # Windows consoles can't always encode PDF-extracted titles
            # (ligatures, typographic punctuation) — fall back rather than
            # crash mid-backfill and lose progress on the remaining papers.
            safe_title = p.title[:60].encode("ascii", "replace").decode("ascii")
            try:
                count, source = await get_citation_count(p.title)
                previous_count, previous_source = p.citation_count, p.citation_count_source
                if should_replace_citation(previous_count, previous_source, count, source):
                    p.citation_count = count
                    p.citation_count_source = source
                    db.commit()
                    print(f"  paper {p.id} ({safe_title!r}): {previous_count} ({previous_source}) -> {count} ({source})")
                else:
                    print(
                        f"  paper {p.id} ({safe_title!r}): keeping {previous_count} ({previous_source}), "
                        f"ignoring worse result {count} ({source})"
                    )
            except CrossrefLookupError as exc:
                print(f"  paper {p.id} ({safe_title!r}): lookup FAILED on both providers: {exc}")

        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
