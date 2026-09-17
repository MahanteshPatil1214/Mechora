"""Seed the demo database with representative precursor narratives.

Deterministic, curateilded: combines realistic observation narratives that
exercise the differentiator — "different stories, same failed barrier,
recurring precursor" — plus verified positives (hard negatives), a similar
wording / different mechanism pair (WHY NOT GROUPED), and watch-list items.

The dataset is SYNTHETIC / representative (not production OIL data). It is
labelled as such in the UI. No evaluation metrics are produced here.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.database import repos  # noqa: E402
from app.database.engine import backend_name, dispose, init_db  # noqa: E402
from app.services.normalization.ontology import get_ontology  # noqa: E402
from app.services.pipeline import AnalysisPipeline  # noqa: E402

DEMO_NARRATIVES: list[tuple[str, str, str]] = [
    # -- Group A: same failed barrier, different equipment / wording ----
    ("A1", "FLANGE-01",
     "During routine flange tightening on the gas line, the fitter did not "
     "confirm zero energy before loosening the joint and a small gas release "
     "occurred."),
    ("A2", "COMP-01",
     "Compressor servicing: the crew opened the casing without zero-energy "
     "verification; isolation had not been done and a small gas release was "
     "observed."),
    ("A3", "VALVE-01",
     "Valve replacement: zero energy was never checked before the joint was "
     "opened and leaking was noticed."),
    ("A4", "PUMP-01",
     "Pump maintenance near the transfer station: no one verified isolation "
     "before the flange was disconnected; a small hydrocarbon release was "
     "noticed."),
    # -- Group B: hot work / gas testing not completed ---------------------
    ("B1", "HOTW-01",
     "Hot work area: gas testing had not been completed before grinding "
     "started; a flash fire ignited nearby rags."),
    ("B2", "HOTW-02",
     "Grinding operations over the tank opening: the flammable gas test was "
     "skipped and sparks could have ignited the vapours."),
    # -- Group C: verified positives (hard negatives) ----------------------
    ("C1", "VER-01",
     "Pipeline maintenance: zero pressure was confirmed and isolation "
     "verified before the joint was opened. No issue."),
    ("C2", "VER-02",
     "Compressor maintenance: lockout was checked and the system proven "
     "depressurized before work. Everything was safe."),
    # -- Group D: similar wording / different mechanism (WHY NOT GROUPED) --
    ("D1", "GASLN-01",
     "Pipeline repair: energy isolation was NOT verified before the joint "
     "was opened; a gas leak was observed."),
    ("D2", "GASLN-02",
     "Pipeline repair: the preliminary flammable gas test was skipped before "
     "the line was cracked open; a flash could occur."),
    # -- Group E: ambiguous watch-list -------------------------------------
    ("E1", "WATCH-01",
     "An area watch noted a strange noise near the compressor during a "
     "routine meeting; no work was in progress."),
]


def main() -> int:
    settings = get_settings()

    # Reset the backing store for a deterministic demo. In auto/sqlite mode
    # the SQLite fallback file is the backing store: remove it before the
    # engine opens it. (backend_name() is unavailable before init_db(), so
    # decide from the configured store mode.)
    if settings.store.lower() == "postgres":
        postgres_reset = True
    else:
        postgres_reset = False
        db_path = Path(settings.sqlite_fallback_path)
        try:
            if db_path.exists():
                db_path.unlink()
                for suffix in ("-wal", "-shm"):
                    d = Path(str(db_path) + suffix)
                    if d.exists():
                        d.unlink()
                print(f"reset sqlite demo db: {db_path}")
        except OSError as exc:
            print(f"  (warning: could not remove {db_path}: {exc})")
        dispose()

    init_db()

    if postgres_reset:
        from sqlalchemy import delete
        from app.database.engine import get_session
        from app.database.tables import ObservationRow, PrecursorFamilyRow
        with get_session() as s:
            s.execute(delete(PrecursorFamilyRow))
            s.execute(delete(ObservationRow))
            s.commit()

    pipeline = AnalysisPipeline(get_ontology(), settings)
    observations = []
    for _tag, report_id, narrative in DEMO_NARRATIVES:
        obs = pipeline.to_observation(report_id, narrative)
        obs.id = report_id
        observations.append(obs)

    repos.bulk_create_observations(observations)

    print(f"seeded {len(observations)} observations -> "
          f"{repos.count_observations()} in store ({backend_name()})")
    summary = repos.dashboard_summary()
    print(f"precursor families: {summary['precursor_families']} "
          f"(recurring {summary['recurring_precursor_families']})")
    for fam in repos.list_families(limit=20):
        print(f"  {fam.id}  {fam.name:<42} n={len(fam.observation_ids)} "
              f"recurring={fam.recurring} attention={fam.attention_signal:5.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())