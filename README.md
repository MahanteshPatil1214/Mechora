# MECHORA — Precursor Attention Signal Engine

Deterministic HSE precursor-attention engine for pipeline safety observation
narratives. Reads **untrusted** report text, extracts a canonical safety
event, assesses Serious Injury or Fatality (SIF) potential, maps **life-saving
rules**, and groups recurring precursors into structural families with an
attention signal.

> Naming: the primary output is the **Prototype Precursor Attention Signal**,
> never a "risk score". SIF and LSR outputs are decision-support only.

## Guardrails

- **Deterministic by default.** No API key → the rule-based extractor runs
  (fully reproducible). An LLM may be configured, but the negation engine is
  **authoritative** for barrier state regardless of extractor.
- **Closed state set for barriers:** `verified, not_verified, failed,
  partially_effective, absent, unknown`. `verified` and `not_verified` are
  never merged.
- **Hard grouping rule:** an observation with a `verified` barrier never
  groups into the same precursor family as a non-verified one, even with
  identical activity/energy wording.
- **Contextual inference, never keyword stuffing.** A narrative rarely quotes a
  canonical code, so the rule extractor detects generic *situations* and
  resolves them **only to codes that already exist in the ontology**. A named
  entry control outranks a broad ambient one, polarity always comes from the
  negation engine rather than keyword presence, and every field keeps a
  verbatim quote as evidence. See
  [Deterministic extraction](#deterministic-extraction).

## Storage

`STORE=auto` (default): tries PostgreSQL, falls back to a self-contained
SQLite file `data/mechora_dev.db`. Set `STORE=sqlite` for offline-only.

## Quickstart

```powershell
# backend
cd E:\Mecora\backend
..\.venv\Scripts\python -m pip install -r requirements.txt
..\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000

# run the acceptance suite
..\.venv\Scripts\python -m pytest -q

# evaluate the rule pipeline against the frozen 216-record set
cd E:\Mecora
.\.venv\Scripts\python scripts\run_evaluation.py
```

Copy `.env.example` → `.env` and edit to taste. Without a `GEMINI_API_KEY`
the deterministic extractor is used automatically.

## API (`/docs` for interactive OpenAPI)

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/analyze` | Analyze a narrative; persists an observation |
| GET | `/api/v1/observations` | List/filter observations |
| GET | `/api/v1/observations/{id}` | Single observation |
| PATCH | `/api/v1/observations/{id}/validation` | Human validation state |
| GET | `/api/v1/families` | Precursor families (recurring filter) |
| GET | `/api/v1/families/{id}` | Single family |
| GET | `/api/v1/dashboard` | Summary counters |
| GET | `/api/v1/aggregates/{kind}` | barrier / activity / location / lsr / sif |
| GET | `/api/v1/ontology` | Canonical concepts for dropdown/autocomplete |
| GET | `/api/v1/evaluation/latest` | Last stored evaluation metrics |
| GET | `/api/v1/health` | Service + store probe |

Example:

```powershell
$body = @{ report_id="RPT-1001";
  narrative="During flange maintenance work, no one confirmed zero energy
  before the job began; gas was heard leaking from the flange at the pipeline
  section. A worker sustained a minor cut.";
  provider="rules" } | ConvertTo-Json
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/analyze `
  -ContentType "application/json" -Body $body
```

## Deterministic extraction

The rule extractor resolves a narrative to canonical codes in two layers.

**Layer 1 — verbatim ontology matching.** `Canonicalizer.map()` and
`_best_synonym_match()` search the narrative for ontology synonyms as literal
substrings (tolerant of hyphen/slash/whitespace variation). A literal match is
**authoritative**: an activity that literally reads "tank entry" is never
overridden by inference.

**Layer 2 — contextual inference.** Real narratives rarely quote a code. They
say "entering the storage vessel" and "the atmosphere was not confirmed safe",
neither of which contains any ontology synonym. Layer 2 detects a generic
*situation* and applies existing codes to it.

### Enclosure-entry context

Confined-space context is established when a narrative names both an enclosure
and an act of being inside it. The cue sets are morphological families, not
sentences, so the same detector serves a vessel, a tank, a pit, a silo or a
reactor:

| Signal | Cue family |
| --- | --- |
| Enclosure | vessel, tank, pit, silo, reactor, drum, vat, boiler, hopper, bunker, manway, hatch, confined space |
| Entry | enter, entered, entering, entry, inside, interior, internal, within, climbed, descended, stepped, crawled |
| Atmosphere | atmosphere, atmospheric, ventilation, ventilated, ventilating, oxygen, purge, purged, flammable, vapour, vapor |
| Interior inspection | inspect / inspected / inspection / examined / examination / survey **plus** interior / inside / internal / within |

Matching is case-insensitive with word boundaries. Morphological variants are
listed explicitly because the trailing boundary means `enter` must not silently
swallow `entering`.

### What the context is allowed to change

| Field | Resolves to | Guard |
| --- | --- | --- |
| `activity` | `confined_space_entry` | only when activity is otherwise **unresolved** |
| `energy` | `flammable_atmosphere` | only when energy is **unresolved**, an atmosphere cue is present, and that atmosphere is **not verified** |
| `exposure` | `confined_space_atmosphere` | exactly the same three conditions as `energy` |
| `task_phase` | `inspection` | an inspection word **and** an interior word in the **same sentence** |
| `barrier` | prefer `confined_space_procedure` | only when the narrative **names the entry control** |

Every rule **fills a gap or breaks a tie**. None overrides a verbatim match,
and none can introduce a code absent from the ontology. Entry-control evidence
is read from `barriers.json` itself, so the ontology stays the single source of
truth.

### Control precedence

`chemical_handling_controls` owns the bare synonym `ventilation`, and
`hot_work_controls` owns the bare synonym `gas testing` — both of which collide
with entry narratives. When two controls match with the same verification
weight, the existing tie-break prefers the **shortest** matched span
(`sort(key=(weight, -len(span)), reverse=True)`), so the shorter and broader
mention wins: `ventilation` (11 chars) beat `required entry checks` (21 chars).

Resolution: a competing control is dropped **only** when its match rests
entirely on ambiguous terms *and* nothing independently proves that control
(`_CS_AMBIGUOUS_CONTROLS` in `rule_extractor.py`). A narrative that genuinely
involves hot work still resolves to `hot_work_controls`.

### Polarity comes from the negation engine

Atmosphere *vocabulary* is not a hazard. "The vessel atmosphere was tested and
ventilation was running" and "the atmosphere was not confirmed safe" use the
same words for opposite situations. The detector therefore asks the
authoritative engine —
`NegationEngine.classify_barrier("confined_space_procedure", …)` — and a
`verified` verdict means the space was controlled, so no atmospheric energy or
exposure is inferred. Polarity is never tracked a second time.

### Evidence

Evidence is always a verbatim quote from the narrative, never a canonical
value. Spans are computed in original narrative coordinates:

- **activity** — entry cue → interior cue, so the span names the entry *and*
  the work done inside.
- **energy** — the clause containing the first atmosphere cue.
- **exposure** — the *contiguous run of atmospheric clauses*, deliberately not
  the whole sentence. In a run-on chain the tail is the cause ("and the worker
  entered the vessel without completing the required entry checks"), which is
  barrier evidence; widening to the sentence would blur two distinct fields.
- **barrier** — the phrase that names the control.
- **barrier_state** — the full causal sentence, owned by the negation engine.

### What it must not do

| Narrative | Result |
| --- | --- |
| Ventilation only, no entry ("ventilation in the process area was not adequate…") | stays `chemical_handling_controls`; no `confined_space_procedure` |
| Routine maintenance mentioning ventilation | unchanged classification |
| Entry with no control evidence ("entered the tank to measure the level") | no barrier invented |
| Entry with no atmosphere evidence | no energy, no exposure |
| Atmosphere **was** tested / purged / ventilated | no atmospheric hazard (`unknown`) |

### Worked example

> Before entering the storage vessel to inspect its interior, the maintenance
> team did not verify that the vessel had been properly isolated and made safe
> for entry. The atmosphere was not confirmed safe, ventilation had not been
> established, and the worker entered the vessel without completing the
> required entry checks.

| Field | Value | Evidence |
| --- | --- | --- |
| `activity` | `confined_space_entry` | "entering the storage vessel to inspect its interior" |
| `task_phase` | `inspection` | "inspect its interior" |
| `energy` | `flammable_atmosphere` | "The atmosphere was not confirmed safe" |
| `barrier` | `confined_space_procedure` | "required entry checks" |
| `barrier_state` | `not_verified` | full causal sentence |
| `exposure` | `confined_space_atmosphere` | "The atmosphere was not confirmed safe, ventilation had not been established" |
| `potential_consequence` | `serious_injury_or_fatality` | model-inferred from grounded hazard/exposure |
| `location` | `unknown` | — |
| `sif` | `high` | — |

Note that "the **maintenance** team" names who was on site, not what the job
was, so the explicit internal inspection outranks the incidental
`maintenance` match. The `not_verified` state and its evidence both come from
the second sentence — the negated verification clauses ("the atmosphere was not
confirmed safe", "ventilation had not been established", "without completing
the required entry checks").

## Measured performance (deterministic pipeline, frozen set, n = 216)

| Field / suite | Accuracy | Target |
| --- | ---: | ---: |
| Schema validity | 1.000 | 1.000 |
| Activity | 1.000 | ≥ 0.95 |
| Task phase | 0.995 | ≥ 0.90 |
| Energy | 0.981 | ≥ 0.90 |
| Barrier | 0.991 | ≥ 0.92 |
| Barrier state | 1.000 | ≥ 0.95 |
| Exposure | 0.972 | ≥ 0.92 |
| Potential consequence | 0.949 | ≥ 0.90 |
| Location | 1.000 | ≥ 0.95 |
| SIF (exact / macro-F1) | 1.000 / 1.000 | ≥ 0.95 / ≥ 0.85 |
| LSR (exact rule set) | 0.981 | ≥ 0.90 |
| Precursor family tag | 0.986 | ≥ 0.90 |
| Negation: isolation verified-vs-not | 1.000 (n=40) | ≥ 0.98 |
| Hard negatives (no false negation) | 1.000 (n=30) | ≥ 0.95 |
| Same-family grouping suite | 1.000 (n=50) | ≥ 0.95 |
| Cross-activity same precursor | 1.000 (n=50) | ≥ 0.95 |
| Verified-vs-failure separation | 1.000 (n=30) | ≥ 0.95 |

## Layout

```
backend/app/
  api/routes/        FastAPI routes (health, analyze, observations, families, ontology, evaluation)
  database/          SQLAlchemy engine + repos (SQLite fallback)
  models/            canonical SafetyEvent / Observation / PrecursorFamily
  schemas/           request/response models
  services/
    extraction/      deterministic rule extractor (+ optional Gemini)
    negation/        authoritative barrier-state engine
    normalization/   ontology loader + canonicalizer
    evidence/        span grounding
    precursor/       signature → structural similarity → family/attention
    sif/             SIF assessment
    lsr/             life-saving-rule mapping
    pipeline.py      orchestrator
backend/tests/       pytest suite incl. frozen-set acceptance thresholds
data/ontology/       JSON concept banks + aux tables (negation, lsr, sif, family)
data/evaluation/     frozen eval_set.json (216) + results
scripts/             generate_dataset.py, run_evaluation.py
```

## Evaluation

`scripts/generate_dataset.py` regenerates the frozen synthetic eval/dev sets
(the pairing invariants and SIF/LSR ground truth are generated by the same
deterministic rules the engine evaluates, keeping GT and engine aligned).
`scripts/run_evaluation.py` runs the 216-record set and persists metrics for
`/api/v1/evaluation/latest`.

Because the frozen set is small (216), a headline accuracy can hide a
regression. When changing inference, capture a real A/B rather than trusting
the committed table:

```powershell
# 1. baseline detail
git stash push -- backend/app/services/extraction/rule_extractor.py
.\.venv\Scripts\python scripts\run_evaluation.py
Copy-Item data\evaluation\results\latest.json baseline.json
git stash pop

# 2. candidate detail
.\.venv\Scripts\python scripts\run_evaluation.py

# 3. compare per-record rows in the two latest.json files
```

`data/evaluation/results/latest.json` holds per-record expected/predicted rows,
so a diff names the exact `report_id`s that flipped rather than only moving an
average.

### Test suite

```powershell
cd E:\Mecora
.\.venv\Scripts\python -m pytest backend\tests -q
```

`backend/tests/test_rules_confined_space_context.py` pins the contextual
inference described above: the worked example, tank / internal-inspection /
gas-testing rewordings, three verified-atmosphere hard negatives, and the
entry-without-control and entry-without-atmosphere guards.
