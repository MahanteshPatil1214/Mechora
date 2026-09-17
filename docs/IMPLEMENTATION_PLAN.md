# MECHORA — Implementation Plan (MVP)

**Document**: `docs/IMPLEMENTATION_PLAN.md`
**Sources**: `project.txt` (PRD v1.0), SIH26165 / Oil India Limited
**Status**: MVP Development

---

## 1. Understanding of the PRD

MECHORA is an AI-assisted safety intelligence platform. Its core differentiator is **not** "an AI that classifies reports" but a **mechanism-level intelligence layer**: unstructured safety narratives are converted into structured **Safety Events**, which are then compared structurally to discover **recurring precursor mechanisms / barrier failures** across apparently unrelated reports.

The core representation:

```
Activity → Hazard/Energy → Required Barrier → Barrier State → Exposure → Potential Consequence
```

Product principle:

> **We don't cluster stories. We cluster safety mechanisms.**

### 1.1 Objectives (from PRD §3)

1. Understand — extract structured safety information from free text.
2. Structure — convert into a canonical Safety Event.
3. Assess — SIF-potential indicators and IOGP Life-Saving Rules.
4. Discover — recurring precursor mechanisms.
5. Explain — evidence for every extracted attribute and relationship.
6. Prioritize — surface patterns requiring HSE review.

### 1.2 Key constraints / principles

- **Hybrid AI**: LLM does language understanding + structured extraction only. All reasoning-critical steps (schema validation, normalization, negation, structural similarity, clustering, aggregation, analytics) are **deterministic/algorithmic**.
- **Evidence is mandatory**: no attribute may be fabricated; if a narrative is insufficient → `unknown` / `needs_review`.
- **Negation is critical**: `verified` vs `not_verified` must be treated as distinct safety states.
- **Structural similarity is primary**; embeddings only a supporting signal.
- **Prototype honesty**: weights, SIF logic and the attention signal are labelled as prototypes, never "official OIL" values.
- **Decision support, not prediction**: no claim of accident prediction or guaranteed SIF detection.

---

## 2. Assumptions (documented engineering choices)

Where the PRD left details unspecified, we make the following assumptions. **No PRD requirement is weakened.**

| # | Topic | Assumption / decision |
|---|-------|------------------------|
| A1 | LLM availability | The pipeline is hybrid: a Gemini-based extractor is used when `GEMINI_API_KEY` is set; a deterministic **rule-based extractor** is the offline fallback so the full pipeline, tests and evaluation run without network/keys. Both produce the same strict JSON schema. |
| A2 | Database | **PostgreSQL** (SQLAlchemy 2.0 + JSONB) is the MVP store — the structured, aggregation-heavy model (categorical dimensions, family↔observation joins, dashboard analytics, transactional family reassignment) fits SQL far better than the PRD's MongoDB. The full SafetyEvent payload is stored as JSONB with indexed summary columns. When Postgres is unreachable, `store=auto` falls back to a local **SQLite** file so tests and offline demos work; the same SQLAlchemy code serves both. A repository layer abstracts persistence for future swaps. |
| A3 | Embeddings | `sentence-transformers` is optional (`MECHORA_EMBEDDING_MODEL`). Precursor grouping uses **structural similarity only** in the default configuration; an embedding boost is a configurable supporting signal and is never the sole clustering criterion. |
| A4 | SIF potential | Classified into `high`, `medium`, `low`, `needs_review` via a transparent deterministic rule set (energy severity × exposure × consequence indicators). Documented as a prototype assessment. |
| A5 | Attention signal | Called **"Prototype Precursor Attention Signal"** (0–100), composed of recurrence, barrier-failure frequency, exposure characteristics, cross-activity spread and SIF-potential evidence. Never called an "OIL risk score". |
| A6 | Family naming | Family names are generated from the dominant mechanism, e.g. `barrier` + `barrier_state` → "Energy Isolation Verification Failure". Deterministic and explainable. |
| A7 | Task phase ontology | Added because the PRD signature schema includes `task_phase`; values like `maintenance`, `pre-job`, `repair`, `operation`, `installation`, `hot_work`, `confined_space_entry`, `height_work`, `lifting`, `testing`. |
| A8 | Barrier states | Exact PRD set: `verified`, `not_verified`, `failed`, `partially_effective`, `absent`, `unknown`. These are **distinct canonical states and are never merged by normalization**. |
| A9 | Evidence representation | An `Evidence` object has `span`, `sentence_index`, `source` ("narrative"). `evidence_status ∈ {"grounded","unknown","needs_review"}`. |
| A10 | Life-Saving Rules | IOGP's 12 rules used as the rule set; mapping is a deterministic explainable table `barrier → rule`, gated by confidence. Low confidence → `needs_review`. |
| A11 | Evaluation set | 200+ hand-styled labelled narratives generated deterministically and **frozen** to disk (`data/evaluation/eval_set.json`). Used only for evaluation metrics, not tuning. |

---

## 3. Architecture

```
                              ┌──────────────────────────────┐
   Narrative ───────────────► │    Extraction Service        │
                              │  • LLM extractor (Gemini)    │
                              │  • Rule-based extractor      │
                              └──────────────┬───────────────┘
                                             ▼
                              ┌──────────────────────────────┐
                              │   Strict schema validation    │
                              │   (Pydantic SafetyEvent)      │
                              └──────────────┬───────────────┘
                                             ▼
                    ┌────────────┬─────────────┬─────────────┐
                    ▼            ▼             ▼             ▼
              Negation       Evidence     Canonical      LLM drift
              Engine         Grounding    Normalizer     guard
                    └────────────┴─────────────┴─────────────┘
                                             ▼
                                    PRECURSOR SIGNATURE
                                             ▼
                          STRUCTURAL PRECURSOR ENGINE
                          • dimension weights (configurable)
                          • pairwise similarity
                          • connectivity clustering
                                             ▼
                    ┌────────────┬─────────────┬─────────────┐
                    ▼            ▼             ▼             ▼
              SIF Potential  LSR Mapping   Precursor     Attention
              Assessment                  Families      Signal
                    └────────────┴─────────────┴─────────────┘
                                             ▼
                                     HSE INTELLIGENCE
                                    (REST API + React UI)
```

Concern separation (PRD NFR-06):

| Stage | Owner |
|-------|-------|
| Language understanding | LLM (Gemini) + deterministic lexicon extraction |
| Safety event representation | Strict Pydantic models + ontology |
| Safety reasoning | Negation, normalization, SIF, LSR (deterministic) |
| Structural similarity | Precursor engine (weighted, deterministic) |
| Precursor discovery | Clustering + family generation |
| Analytics | Aggregation layer + dashboard endpoints |

---

## 4. Modules

### Backend (`backend/app`)

| Module | Responsibility |
|--------|---------------|
| `models/` | Strict Pydantic models: `Evidence`, `SafetyEvent`, `Observation`, `PrecursorFamily`, SIF/LSR result models |
| `schemas/` | Request/response API schemas |
| `services/extraction/` | `BaseExtractor`, `LLMExtractor` (Gemini, structured JSON), `RuleBasedExtractor` (deterministic fallback) |
| `services/negation/` | Negation cue detection + barrier-state classifier |
| `services/normalization/` | Ontology-driven canonical mapping (`canonical.py`, `ontology.py`) |
| `services/evidence/` | Sentence/span-level evidence grounding |
| `services/sif/` | Deterministic SIF-potential assessment |
| `services/lsr/` | IOGP Life-Saving Rule mapping |
| `services/precursor/` | `signature.py`, `weights.py`, `similarity.py`, `clustering.py`, `family.py`, `attention.py` |
| `services/pipeline.py` | Orchestrates analysis + persistence |
| `database/` | SQLAlchemy engine (Postgres default, SQLite fallback) + repositories |
| `api/routes/` | `observations`, `precursors`, `dashboard`, `ontology`, `evaluation` |
| `config.py` | Pydantic-settings env config |

### Data (`data/`)

- `ontology/*.json` — canonical vocab + synonym maps + LSR table + SIF rules.
- `evaluation/eval_set.json` — frozen 200+ labelled set.
- `synthetic/dev_set.json` — larger development set.
- `evaluation/results/` — evaluation run outputs (JSON metrics).

### Frontend (`frontend`)

- React + Vite + Tailwind. Pages: Dashboard, Observation Analysis, Precursor Families, Precursor Detail.

---

## 5. Data Model (canonical Safety Event)

Pydantic-strict; the LLM may only output these fields, in a constrained schema (see `models/safety_event.py`):

```json
{
  "report_id": "OBS-001",
  "narrative": "...",
  "activity": "compressor_maintenance",
  "task_phase": "maintenance",
  "hazard": "pressurized_energy",
  "energy": "pressurized_gas",
  "unsafe_action": "work_started_without_zero_energy_check",
  "unsafe_condition": "unknown",
  "barrier": "energy_isolation",
  "barrier_state": "not_verified",
  "exposure": "uncontrolled_gas_release",
  "actual_consequence": "no_injury",
  "potential_consequence": "serious_injury_or_fatality",
  "location": "compressor_room",
  "life_saving_rules": ["energy_isolation"],
  "evidence": ["before zero pressure was verified"],
  "confidence": 0.87,
  "precursor_signature": {
    "activity": "compressor_maintenance",
    "task_phase": "maintenance",
    "energy": "pressurized_gas",
    "barrier": "energy_isolation",
    "barrier_state": "not_verified",
    "exposure": "gas_release",
    "potential_consequence": "serious_injury_or_fatality"
  }
}
```

All categorical fields are canonical **snake-case codes** validated against the ontology. Unknowns use `unknown` / `none_identified` / `needs_review`.

---

## 6. AI Pipeline

1. **Extraction** — LLM (Gemini, `response_mime_type=application/json` with a strict output schema) or rule-based fallback. The output is validated against the Pydantic `LLMExtraction` schema; malformed output is rejected and retried once, then falls back to the rule extractor.
2. **Negation / barrier-state** — deterministic: for each detected barrier mention, collect the clause, look for negation cues and verification cues, and classify into one of the six states. **This stage overrides any LLM `barrier_state` (the LLM proposes, the engine disposes).**
3. **Evidence grounding** — every extracted valued attribute is searched for in the narrative sentences (exact/normalized phrase match). If no span matches → `unknown`/`needs_review` instead of invention.
4. **Canonical normalization** — synonyms → canonical codes. Synonym mapping is **per-concept**: synonym groups never cross `verified ↔ not_verified` boundaries.
5. **Precursor signature** — compact structural tuple (activity, task_phase, energy, barrier, barrier_state, exposure, potential_consequence).
6. **Structural Precursor Engine** — see §8.
7. **SIF + LSR + Attention** — deterministic rules.

---

## 7. Database Plan

**PostgreSQL** via SQLAlchemy 2.0 (`psycopg` driver), with automatic SQLite fallback for offline/tests.

Tables:

- `observations` — full `SafetyEvent` payload in a JSONB column plus indexed summary columns (`report_id` unique, `activity`, `task_phase`, `barrier`, `barrier_state`, `energy`, `exposure`, `location`, `sif_classification`, `potential_consequence`, `life_saving_rules` JSONB, `precursor_family_id` FK, `validation`, `created_at`).
- `precursor_families` — family id/name/description, common mechanism fields, `observation_ids` JSONB references (narratives are not duplicated), attention signal + basis, aggregated activities/locations, `created_at`.
- `evaluation_results` — per-run metrics + category breakdowns (JSONB).
- `ontology` — optional snapshot of the canonical vocabulary for audit/HSE feedback.

Indexes target dashboard filters: activity, barrier, barrier_state, energy, exposure, location, family id, created_at.

---

## 8. Structural Precursor Engine

### 8.1 Signature

`precursor_signature` = tuple of canonical codes. Machine-comparable.

### 8.2 Weights (configurable, PRD §12)

```python
STRUCTURAL_WEIGHTS = {
    "barrier":     0.20,   # barrier codes match
    "barrier_state":0.10,  # state match (verified != not_verified)
    "energy":      0.25,   # hazard/energy dimension
    "exposure":    0.20,
    "task_phase":  0.15,
    "activity":    0.10,
}
```

- `barrier` + `barrier_state` sum to `0.30` as required by the PRD.
- **Hard rule**: differing `barrier_state` where either state is a *non-failure* (`verified`) blocks grouping — verified vs anything else can never fall in the same family, matching PRD §14.
- `unknown`/`needs_review` components contribute 0 similarity on that dimension (conservative).

### 8.3 Similarity

Weighted dimension matches → `structural_similarity ∈ [0,1]`. Embedding cosine similarity (optional) blended at `5%` max as a supporting signal (configurable), never the primary criterion.

### 8.4 Clustering

- Pairwise similarity → unweighted graph, edges above `FAMILY_ASSIGN_THRESHOLD` (default 0.65) → connected components → candidate families.
- A family is "recurring" when ≥ 2 observations share the mechanism; singletons are retained as candidates.
- Family name from mechanism template (`barrier` + `barrier_state` → e.g. "Energy Isolation Verification Failure").

---

## 9. SIF Potential (prototype)

Deterministic table evaluation over `energy`, `barrier_state` (failed/absent/not_verified/partially_effective raise risk), `exposure`, `potential_consequence`:

- `high` — high-energy + failed/absent barrier + serious-exposure/consequence indicators.
- `medium` — moderate energy or partial barrier.
- `low` — verified barriers / benign exposure.
- `needs_review` — insufficient or conflicting evidence.

Output: `classification, confidence, reason, supporting_evidence`. Explicit UI/API messages: *decision support, not prediction*.

---

## 10. LSR Mapping

Static explainable table `barrier → IOGP Life-Saving Rule` (energy_isolation → Energy Isolation; confined_space → Confined Space Entry; height_work → Working at Height; hot_work → Hot Work; lifting_ops → Lifting Operations; permit/authorization → Work Authorization; electrical isolation → Electrical Isolation; etc.). When barrier confidence is low or no rule applies → `needs_review`.

---

## 11. API Plan (`/api/v1`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/observations/analyze` | Analyze narrative, return structured event (no persist) |
| POST | `/observations` | Analyze + persist observation |
| GET | `/observations` | List/filter (activity, barrier, barrier_state, energy, location, sif_potential, q) + pagination |
| GET | `/observations/{id}` | Observation detail |
| PATCH | `/observations/{id}/validation` | Human-in-the-loop validation |
| POST | `/observations/batch` | Batch CSV/JSON upload |
| GET | `/precursors` | List precursor families (sorted by attention signal) |
| GET | `/precursors/{id}` | Family detail incl. supporting observations |
| GET | `/dashboard/summary` | Overview KPIs |
| GET | `/dashboard/barriers` | Barrier failure aggregates |
| GET | `/dashboard/activities` | Activity aggregates |
| GET | `/ontology` | Canonical vocabulary |
| GET | `/evaluation/results` | Latest evaluation metrics |
| POST | `/evaluation/run` | Run evaluation against frozen eval set |
| POST | `/ingest/synthetic` | Load synthetic/dev sets into DB |

Consistent error envelope `{"detail": {...}}`; no unhandled exceptions leak.

---

## 12. Dataset Plan

- `scripts/generate_dataset.py` produces the **frozen evaluation set (200+ narratives)** with mandated distribution: 50+ same-mechanism/different-wording, 30+ negation (positive vs negative pairs of identical wording), 30+ different-activity/same-precursor, 30+ hard negatives, 20+ multi-hazard, 20+ ambiguous.
- A larger supplementary **development set** (`data/synthetic/dev_set.json`) is generated separately.
- Every record carries ground-truth labels: `report_id`, `category`, `activity`, `task_phase`, `energy`, `barrier`, `barrier_state`, `exposure`, `potential_consequence`, `sif_potential`, `life_saving_rules`, `family_tag`.

---

## 13. Testing Plan

Unit: schema validation, normalization (incl. no ver/notver merge), negation (all six states), evidence grounding, similarity math, weights, grouping (same-mechanism recall / different-mechanism precision), SIF logic, LSR mapping, family naming, attention signal.

**Critical safety suite** (PRD §28): isolation verified vs NOT verified; zero-pressure confirmed vs NOT confirmed — target ≥ 95%.

Integration: narrative → extraction → normalization → signature → DB round-trip (SQLite + real Postgres if available).

API: all endpoints via FastAPI TestClient.

Evaluation: `scripts/run_evaluation.py` computes acceptance-metric table against the frozen set; thresholds listed in §14; nothing reported unless actually measured.

---

## 14. Acceptance Thresholds (engineering targets)

| Metric | Target |
|-------|-------|
| Core structured extraction | ≥ 90% F1 |
| Barrier extraction | ≥ 92% F1 |
| Barrier-state classification | ≥ 95% accuracy |
| Negation handling | ≥ 98% accuracy |
| Evidence grounding | ≥ 95% |
| LSR mapping | ≥ 90% |
| SIF potential | ≥ 85% F1 |
| Same-mechanism recall | ≥ 85% |
| Different-mechanism precision | ≥ 90% |
| Critical-case suite | ≥ 95% |
| Schema validity | ≥ 99% |

*Prototype engineering targets; not OIL/SIH official requirements.*

---

## 15. Implementation Order

1. Ontology + models → 2. normalization + negation + evidence → 3. extractors → 4. signature + similarity + clustering → 5. SIF + LSR + attention → 6. pipeline orchestrator → 7. dataset generator (eval + dev) → 8. DB layer + repositories → 9. REST API → 10. tests → 11. evaluation → 12. frontend → 13. README/.env.example/.gitignore (Docker intentionally deferred per decision).

---

## 16. Known Limitations

- Synthetic data only; no claim of OIL data representation.
- Rule-based fallback extractor is weaker than the LLM on open vocabulary, but deterministic and testable; LLM path available with a key.
- Structural similarity assumes canonical codes are correct; ontology gaps → `unknown`/`needs_review`.
- Prototype weights/SIF/attention formulas require OIL-data calibration before production use (documented in UI).
- No auth/RBAC/multi-tenant (out of MVP scope per PRD §24).
- SIF potential is decision support, not prediction.