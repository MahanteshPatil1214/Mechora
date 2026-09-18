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

## Measured performance (deterministic pipeline, frozen set, n = 216)

| Field / suite | Accuracy | Target |
| --- | ---: | ---: |
| Schema validity | 1.000 | 1.000 |
| Activity | 1.000 | ≥ 0.95 |
| Task phase | 0.995 | ≥ 0.90 |
| Energy | 0.981 | ≥ 0.90 |
| Barrier | 0.977 | ≥ 0.92 |
| Barrier state | 1.000 | ≥ 0.95 |
| Exposure | 0.954 | ≥ 0.92 |
| Potential consequence | 0.949 | ≥ 0.90 |
| Location | 1.000 | ≥ 0.95 |
| SIF (exact / macro-F1) | 1.000 / 1.000 | ≥ 0.95 / ≥ 0.85 |
| LSR (exact rule set) | 0.968 | ≥ 0.90 |
| Precursor family tag | 0.972 | ≥ 0.90 |
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