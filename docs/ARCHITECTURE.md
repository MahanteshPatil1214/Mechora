# MECHORA Backend Architecture (MVP)

Deterministic HSE precursor-attention engine. The only way text becomes a
canonical safety event is through strict extraction → normalization; LLM
output (when configured) enters through a Pydantic schema with
`extra="forbid"`, and the negation engine is **authoritative** for barrier
state regardless of extractor.

## Pipeline (`backend/app/services/pipeline.py`)

```
raw narrative
   │
   ▼
[1] EXTRACTION  ── rules (default)  ── rule_extractor.py
                   llm (optional)   ── llm.py -> strict LLMExtraction
   │  Hazard segmentation: unsafe condition / unsafe action / actual
   │  consequence / potential consequence / location / activity / energy /
   │  barrier / exposure, each grounded to a matched span.
   ▼
[2] NORMALIZATION ── normalization/canonical.py + ontology.py
   │  Every value mapped to a canonical code. Unknown if no match.
   ▼
[3] NEGATION ── negation/engine.py   (AUTHORITATIVE, §N)
   │  barrier_state is re-derived at sentence/clause level from the
   │  canonical barrier + narrative. verified/not_verified hard-separated.
   ▼
[4] SIF ASSESSMENT ── sif/sif.py
   │  energy_rank + exposure_rank + barrier-state penalty → high/medium/
   │  low/needs_review, with confidence + reason + supporting_evidence.
   ▼
[5] LSR MAPPING ── lsr/lsr.py
   │  IOGP Life-Saving Rule codes + basis.
   ▼
[6] EVENT ── SafetyEvent (models/safety_event.py)
   │  canonical event + evidence[] + field_evidence{} (attribute→span)
   ▼
[7] PRECURSOR ENGINE ── precursor/
   │  signature → structural similarity → clustering → family
   │  → recurrence/attention → WHY GROUPED / WHY NOT GROUPED
   ▼
[8] STORE ── database/(tables,repos).py  (SQLite fallback / Postgres)
   │  observation + precursor_family + assignment persisted
   ▼
API ── api/routes/  (analyze, observations, families, dashboard, ontology, evaluation, health)
```

## Key modules

| Module | Responsibility |
| --- | --- |
| `extraction/rule_extractor.py` | Deterministic extractor; returns `ExtractionOutput` with `matched{field→span}`. |
| `extraction/llm.py` | Optional Gemini provider → strict `LLMExtraction` model. |
| `negation/engine.py` | Sentence/clause barrier-state classifier (priority cues). |
| `normalization/ontology.py` | Loads `data/ontology/*.json`; canonicalizer; energy/exposure ranks; SIF rules. |
| `normalization/canonical.py` | Code normalization with a closed code set per category. |
| `evidence/evidence.py` | Span grounding into `Evidence(span, sentence_index, status)`. |
| `precursor/signature.py` | `PrecursorSignature` — the machine-comparable structural vector. |
| `precursor/similarity.py` | Weighted structural similarity + optional embedding blend. |
| `precursor/clustering.py` | Greedy pairwise clustering over signatures. |
| `precursor/family.py` | Group → `PrecursorFamily` incl. grouping evidence aggregation. |
| `precursor/attention.py` | Prototype 0-100 Attention Signal (factors + basis). |
| `precursor/engine.py` | Orchestrates clustering, exclusions, persistence. |
| `sif/sif.py` | SIF-potential assessment (decision support). |
| `lsr/lsr.py` | Life-saving-rule mapping with basis. |
| `database/tables.py` | SQLAlchemy tables (`observations`, `precursor_families`, `family_assignments`). |
| `database/repos.py` | Repository layer; serializes/validates models into/out of rows. |

## Precursor engine

### Structural similarity

Weights (asserted in `precursor/weights.py`, matches PRD section 12):

| Dimension | Weight |
| --- | ---: |
| barrier | 0.20 |
| barrier_state | 0.10 |
| energy | 0.25 |
| exposure | 0.20 |
| task_phase | 0.15 |
| activity | 0.10 |

Hard rules that zero a dimension score:
- `barrier_state` verified-vs-not-verified → `0.00` (never merges).
- Any verified barrier against a non-verified barrier → family excluded outright (`hard_rule`).

Optional sentence-transformer cosine can be blended at `embedding_blend=0.05`
when configured; the structural score dominates.

### Grouping (WHY GROUPED)

`family.build()` computes, for every member comparison inside a group, the
per-dimension `GROUPING_DIMENSIONS` evidence:
- `status`: `same` (uniform value, e.g. 5/5) · `mixed` (dominant value + count, e.g. 4/5 · 1 differ) · `distinct` (no clear dominant value).
- `coverage`: share of members holding the dominant value.
- `note`: human-readable summary.

This is derived from the **actual** per-observation comparison — never
hardcoded.

### Exclusion (WHY NOT GROUPED)

After families are formed, `engine._attach_exclusions()` compares every
family against the nearest other family via **max pairwise** structural
similarity:
- If `max_similarity ≥ family_exclusion_floor (0.35)` the pair is recorded.
- `similarity`, `differing_dimensions` (dimensions where the pair scored 0,
  excluding the `hard_rule`), and a `basis` string are stored on both
  families.

This is how similarly-worded reports that fail *different* barriers are shown
to stay separate.

### Recurrence & attention

- `recurring = members ≥ recurring_min_observations (2)`. The threshold is
  persisted on each family and shown in the UI.
- `attention.py`: 0-100 Prototype Precursor Attention Signal with weights
  `recurrence 0.25 · barrier_failure 0.20 · exposure 0.20 ·
  cross_activity 0.15 · sif_evidence 0.15 · energy_severity 0.05`, each
  normalized 0-1 and clamped. `basis` only lists factors whose contribution
  ≥ `FACTOR_MIN_CONTRIBUTION (0.02)`; the recurrence line only appears when
  ≥ 2 observations. `ATTENTION_DISCLAIMER` is exposed to the UI.
- **Never an official OIL risk score** — decision-support signal only.

## Configuration (`backend/app/config.py`)

| Setting | Default | Purpose |
| --- | --- | --- |
| `store` | `auto` | Postgres → SQLite fallback |
| `family_assign_threshold` | `0.65` | Structural similarity to join a family |
| `embedding_blend` | `0.05` | Max embedding weight |
| `recurring_min_observations` | `2` | Explicit recurring threshold |
| `family_exclusion_floor` | `0.35` | Min similarity to record a WHY-NOT pair |

## Storage

`STORE=auto` tries Postgres, falls back to `data/mechora_dev.db` (SQLite).
`precursor_family` rows persist `attention_factors`, `recurring_threshold`,
`grouping_evidence` (JSON), and `exclusions` (JSON); repo reads validate each
model via `model_validate` so a manual DB edit fails loudly instead of
silently corrupting state.