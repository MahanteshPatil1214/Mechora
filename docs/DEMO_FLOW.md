# MECHORA Demo Flow

A repeatable demonstration of the MVP. Everything runs locally with the
deterministic rules provider — no API key required.

## 1. Reset & seed

The curated SIH demo dataset lives in ONE place:

```
data/demo/demo_reports_7.txt
```

It contains **exactly 7 logical reports** (Report 1–7) plus a trailing
`NON-REPORT / Expected Test Signals / instructions` block that the segmenter
excludes from analysis — it demos the exclusion rule, never the data.

```powershell
cd E:\Mecora
.\\.venv\Scripts\python scripts\seed_demo.py
```

This explicitly resets the observation + precursor-family tables (operator
action; production data is never auto-deleted), then loads the 7 curated
reports through the same pipeline/document path used for uploaded files
(document id `DEMO-CURATED`, report segments `DEMO-CURATED-SEG1..7`).

Expected result (deterministic):

```
seeded 7 observations -> 7 in store (postgresql)
precursor families: 3 (recurring 1)
  PFAM-A7CC6  Energy Isolation Verification Failure      n=4 recurring=True type=precursor attention=83.22
  PFAM-781A4  Energy Isolation Verification Failure      n=1 recurring=False type=precursor attention=64.44
  PFAM-F36C4  Energy Isolation Failure                   n=1 recurring=False type=precursor attention=60.69
  PFAM-418BD  Energy Isolation Verified                  n=1 recurring=False type=controlled attention=14.44
```

`--counts` prints only the summary block; `--no-reset` skips the reset.

Family ids (`PFAM-<5-hex>`) are derived deterministically from each family's
structural mechanism signature (barrier + barrier_state + energy + exposure),
so they are stable across seeding cycles.

If the store is SQLite (offline demo, not the local Postgres) seeding resets
its `mechora` tables instead.

## 2. Start

```powershell
cd E:\Mecora\backend
..\.venv\Scripts\python -m uvicorn app.main:app --port 8080    # backend
cd E:\Mecora\frontend
npm run dev                                                      # frontend (localhost:5173)
```

No running uvicorn leftover is required for seeding — the seed opens its own
store connection.

## 3. The 30-second walkthrough

Open the dashboard (dark HSE style). Three beats:

**Beat 1 — Analyze the document.**
Upload `data/demo/demo_reports_7.txt` via **Analyze → Upload document**. The
document list shows 7 report segments and excludes the NON-REPORT instructions
block. Open the observation for REPORT 1 (Pipeline Maintenance).

Expected: activity = **Pipeline Maintenance** (evidence: "gas pipeline") ·
task phase = maintenance · energy = **Pressurized Gas** · barrier = **Energy
Isolation** (evidence: "before confirming complete isolation and zero-energy
verification") · barrier state = **Not Verified** (rose) · exposure =
**Uncontrolled Gas Release** · consequence = **Serious Injury or Fatality**;
family: **PFAM-A7CC6**. The badge reads **Recurring Precursor** and the
WHY-GROUPED panel title is **WHY THESE REPORTS FORM ONE PRECURSOR PATTERN**.

**Beat 2 — Precursor families panel.**
Toggle "Recurring Only (≥ 2 reports)" → **PFAM-A7CC6** (attention 83.2/100).

- **WHY GROUPED**: energy, barrier, barrier state, exposure, task phase all
  100% `same`; activity is `distinct` over 4 different activities
  (Pipeline / Compressor / Pump / Valve Maintenance) — the *different stories
  → same failed barrier → recurring precursor* story.
- **WHY NOT GROUPED**: vs `PFAM-F36C4` (Not Verified ≠ **Failed** →
  procedural-verification omission vs physical hardware failure), vs
  `PFAM-418BD` (Not Verified ≠ **Verified** → hard-negation control), and vs
  `PFAM-781A4` (Pressurized Gas ≠ **Pressurized Liquid** → the crude-slurry
  release never merges into the gas family).
- Open REPORT 5 (Pump Maintenance Liquid): badge **Precursor Candidate**,
  family `PFAM-781A4` — identical verification story, different energy →
  different mechanism, kept separate.
- Open REPORT 7 (Failed Barrier): family `PFAM-F36C4` — "was not effective"
  is **Failed**, never downgraded to Not Verified.
- REPORT 6 (Verified Control) is `PFAM-418BD`, family_type `controlled`:
  verified compliance stays out of every precursor count.

**Beat 3 — Observations list.**
All 7 curated observations show SIF badges with confidence and `field_evidence`
span chips per row. The verified control (Report 6) shows exposure = Unknown
(negated outcome "No release occurred" is never converted into a release) and
never appears in any failure family — including via the precursor engine.

## 4. Demo dataset map

| Report | Report Segment | Family | Purpose |
| --- | --- | --- | --- |
| 1 Pipeline Maintenance | DEMO-CURATED-SEG1 | PFAM-A7CC6 | Gas-isolation-not-verified, pipeline flanges → recurring member |
| 2 Compressor Maintenance | DEMO-CURATED-SEG2 | PFAM-A7CC6 | Same mechanism, different equipment & wording (barrier evidence = full "before confirming complete isolation…" clause) |
| 3 Pump Maintenance | DEMO-CURATED-SEG3 | PFAM-A7CC6 | Same mechanism, process pump |
| 4 Valve Replacement | DEMO-CURATED-SEG4 | PFAM-A7CC6 | Same mechanism, valve work → 4 distinct activities |
| 5 Pump Maintenance (Liquid) | DEMO-CURATED-SEG5 | PFAM-781A4 | Crude/sour-water slurry release → different energy → WHY NOT GROUPED |
| 6 Verified Control | DEMO-CURATED-SEG6 | PFAM-418BD | Verified positive → controlled, excluded from precursor counts |
| 7 Failed Barrier | DEMO-CURATED-SEG7 | PFAM-F36C4 | "was not effective" → Failed, kept separate from omission family |
| (NON-REPORT footer) | excluded | — | Demos non-report exclusion in segmentation |

Extraction hardening in this round: Report 2's barrier evidence is the whole
verbatim verification clause (`before confirming complete isolation of the
pressurized gas line`) instead of the truncated synonym `isolation of`;
Report 7's `was not effective` now resolves to **Failed**; the three activity
synonyms (`gas pipeline`, `gas compressor`, `process pump`) keep Reports 1–3
grounded. All values are confirmed on both the rules path and the LLM path.

## 5. What not to demo

- Do not call any output a "risk score". SIF = prototype decision support;
  Attention = Prototype Precursor Attention Signal, not an official OIL score
  (both disclaimers are rendered in the UI).
- `verified` and `not_verified` are hard-separated: a verified observation
  never merges into a failure family (this is the hard grouping rule), and the
  verified control is `family_type = controlled`, never a precursor.
- Do not upload the demo file via **Analyze** and hand the live dataset a
  second time: uploading creates `DOC-DEMO-REPORTS-7-SEG<n>` observations with
  their own ids. If you did, re-run `scripts\seed_demo.py` to restore the
  pristine 7-observation demo state.