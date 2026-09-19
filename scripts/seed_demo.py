"""Seed the demo database with the curated SIH demo dataset.

Thin CLI over the curated-demo service. Deterministic: resets observation and
precursor-family tables, then loads the 7-report curated dataset (segments
plus the excluded NON-REPORT block) through the same pipeline/document path
used by uploaded files. The dataset is SYNTHETIC / representative (not
production OIL data) and is labelled as such in the UI.

Optional flags:
  --no-reset   keep existing observations (skips the explicit reset step)
  --counts     print only the deterministic summary counts (for scripting)

Usage:
    .\\.venv\\Scripts\\python scripts\\seed_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.services.demo.seed import (  # noqa: E402
    demo_summary,
    reset_demo,
    seed_curated_demo,
)


def main() -> int:
    args = [a for a in sys.argv[1:]]
    reset = "--no-reset" not in args
    counts_only = "--counts" in args

    settings = get_settings()
    if reset:
        reset_demo()
    result = seed_curated_demo(settings)

    if counts_only:
        print(f"seeded {result['observations_seeded']} observations -> "
              f"{demo_summary()['observations']} in store "
              f"({result['backend']})")
        summary = demo_summary()
        print(f"precursor families: {summary['precursor_families']} "
              f"(recurring {summary['recurring_families']})")
        for fam in summary["families"]:
            print(f"  {fam['id']}  {fam['name']:<42} n={fam['n']} "
                  f"recurring={fam['recurring']} type={fam['family_type']} "
                  f"attention={fam['attention_signal']:5.2f}")
        return 0

    print(f"seeded {result['observations_seeded']} observations -> "
          f"{demo_summary()['observations']} in store ({result['backend']})")
    summary = demo_summary()
    print(f"precursor families: {summary['precursor_families']} "
          f"(recurring {summary['recurring_families']})")
    for doc in result["documents"]:
        print(f"  {doc['report_segment_id']:<24} "
              f"({doc['heading']:<35}) {doc['character_count']} chars")
    for fam in summary["families"]:
        print(f"  {fam['id']}  {fam['name']:<42} n={fam['n']} "
              f"recurring={fam['recurring']} type={fam['family_type']} "
              f"attention={fam['attention_signal']:5.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())