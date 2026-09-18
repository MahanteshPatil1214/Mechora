# MECHORA Demo Flow

A repeatable demonstration of the MVP. Everything runs locally with the
deterministic rules provider — no API key required.

## 1. Reset & seed

```powershell
cd E:\Mecora
.\\.venv\Scripts\python scripts\seed_demo.py
```

If `STORE=editing/sqlite` this resets the local demo DB and writes 12 curated
observations. Expected result:

```
precursor families: 4 (recurring 3)
  PFAM-A7CC6  Energy Isolation Verification Failure      n=5 recurring=True attention=84.71
  PFAM-05AF8  Hot Work Controls Verification Failure     n=3 recurring=True attention=78.88
  PFAM-F36C4  Energy Isolation Failure                   n=1 recurring=False attention=64.44
  PFAM-418BD  Energy Isolation Verified                  n=2 recurring=True attention=21.52
```

Family ids (`PFAM-<5-hex>`) are derived deterministically from each family's
structural mechanism signature (barrier + barrier_state + energy + exposure),
so they are stable across seeding cycles, observation insertions and ordering
changes.

If the store is Postgres (not the local SQLite fallback) seeding resets its
`mechora` tables instead.

## 2. Start

```powershell
cd E:\Mecora\backend
..\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000    # backend
cd E:\Mecora\frontend
npm run dev                                                              # frontend (localhost:5173)
```

No running uvicorn leftover is required for seeding — the seed opens its own
store connection.

## 3. The 30-second walkthrough

Open the dashboard (dark HSE style). Three beats:

**Beat 1 — Analyze an observation.**
Paste the flange narrative (or click a Sample button):

> "During routine flange tightening on the gas line, the fitter did not
> confirm zero energy before loosening the joint and a small gas release
> occurred."

Expected: activity = pipeline maintenance · task phase = maintenance ·
energy = pressurized gas · barrier = energy isolation ·
barrier state = **Not Verified** (rose) · exposure = uncontrolled gas
release · consequence = serious injury or fatality;
SIF panel: **HIGH** at 95%, with reason, supporting evidence lines and the
prototype note; evidence chips show the exact spans returned by extraction
("loosening the joint", "zero energy", "did not confirm", "release occurred");
family: PFAM-A7CC6.

**Beat 2 — Precursor families panel.**
Toggle "Recurring only" to show PFAM-A7CC6/PFAM-05AF8/PFAM-418BD.

- **PFAM-A7CC6** is the strongest signal: attention 84.7/100, basis lines
  (Recurrence 5, Failed-barrier 5/5, Max exposure 4/5, Cross-activity 4
  distinct, SIF 5/5, Max energy 5/5) and the prototype disclaimer.
- **WHY GROUPED** chips: barrier = energy isolation ✓100%, barrier state =
  not verified ✓100%, exposure = uncontrolled gas release ✓100%, task phase ✓,
  energy mixed 80%, activity distinct 40% — the *different stories →
  same failed barrier → recurring precursor* story.
- **WHY NOT GROUPED** on PFAM-A7CC6 vs PFAM-05AF8: differs barrier,
  energy, exposure. Group D is a gas-line narrative whose failed energy
  isolation is kept separate in PFAM-F36C4.

**Beat 3 — Observations list.**
Filter "All states" → observations show SIF badges with confidence and the
`field_evidence` span chips per row. The verified positives (Group C) carry
state = verified and never appear in the not-verified family.

## 4. Demo seed groups

| Group | Family | Count | Purpose |
| --- | --- | --- | --- |
| A | PFAM-A7CC6 | 5 | Energy-isolation-not-verified across different equipment (pipeline flange, pump, valve, compressor) → recurring precursor family |
| B | PFAM-05AF8 | 3 | Hot-work gas-testing-not-completed narratives → recurring precursor family |
| C | PFAM-418BD | 2 | Verified positives (energy isolation proven, tank entry checked) → controlled family, never merged with failures |
| D | PFAM-F36C4 | 1 | Failed energy isolation (hardware failure state) kept separate from the verification-omission family → WHY NOT GROUPED |

## 5. What not to demo

- Do not call any output a "risk score". SIF = prototype decision support;
  Attention = Prototype Precursor Attention Signal, not an official OIL score
  (both disclaimers are rendered in the UI).
- `verified` and `not_verified` are hard-separated: a verified observation
  never merges into a failure family (this is the hard grouping rule).