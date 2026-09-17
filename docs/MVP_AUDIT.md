# MVP Audit — MECHORA (pre-improvement pass)

Audit date: baseline before the "structural precursor strength" pass.
Source of truth: `project.txt` (PRD v1.0). Frozen eval set: `data/evaluation/eval_set.json` (216 records, synthetic/representative).

## Baseline state (measured, provider=rules)

| Metric | Value |
| --- | --- |
| schema_valid | 1.000 |
| activity | 1.000 |
| task_phase | 0.995 |
| energy | 0.954 |
| barrier | 0.977 |
| barrier_state | 1.000 |
| exposure | 0.968 |
| potential_consequence | 0.958 |
| location | 1.000 |
| sif exact / macro-F1 | 0.977 / 0.896 |
| lsr exact-set | 0.968 |
| family tag | 0.972 |
| isolation verified-vs-not (n=40) | 1.000 |
| hard negatives (n=30) | 1.000 |
| same-family grouping (n=1) | 1.000 |

Tests: `pytest` 25 passed.

## What is already correct

1. **Structural weights already match the PRD prototype table.** `weights.py`:
   barrier 0.20 + barrier_state 0.10 = 0.30, energy 0.25, exposure 0.20,
   task_phase 0.15, activity 0.10, with an assert on the 0.30 sum.
2. **Negation is authoritative and works on the 4 required phrases** (logic
   verified by code reading; tests to be added):
   - "Isolation was verified" → verified; "Isolation was NOT verified" → not_verified.
   - "Zero pressure was confirmed" → verified; "Zero pressure was NOT confirmed" → not_verified.
3. **Hard grouping rule exists** (`similarity.py`): if either side is `verified`
   and states differ, similarity is forced to 0.0 — verified and not_verified
   can never merge into one family.
4. **SafetyEvent model is complete** — all 16 required attributes exist with
   canonical Literals, `extra="forbid"`, evidence with sentence_index/status,
   SIFAssessment (classification + confidence + reason + supporting_evidence +
   model_note), LSRMapping (rules + confidence + basis + evidence + needs_review).
5. **Attention signal** is a documented 0-100 prototype with factor weighting
   and a basis list; never labelled as an OIL risk score.
6. **No fabricated metrics** — every eval number comes from the live run.

## Gaps found (ordered by PRD priority)

1. **Extraction quality (activity).** The user example
   *"During routine flange tightening on the gas line …"* returns
   `activity=unknown` because `pipeline_maintenance` synonyms do not include
   *flange tightening*, *gas line*, *joint*, *line repair*. Synonym list is too
   sparse for real HSE wording. (Energy/barrier/state were correct.)
   - Root cause: activities.json is curated short-form only; no equipment/asset
     phrase coverage, no fallback mapping.
2. **No control-path evidence map.** Per-field evidence spans exist in
   `ExtractionOutput.matched` but are not persisted on the event, so the UI
   cannot show "exact supporting text per field" (PRD FR-03 / requirement 3).
3. **WHY GROUPED? not implemented.** `family.py` computes a dominant-value
   description string but no per-dimension explanation
   (✓ same energy / ✓ same barrier / △ different activity) generated from
   actual comparison data.
4. **WHY NOT GROUPED? not implemented.** No mechanism to show which structural
   dimensions differ when similar reports are correctly separated
   (PRD SC-06, eval Category 4).
5. **Recurring threshold implicit.** `recurring = len(group) >= 2` hardcoded;
   not surfaced in API/UI ("1 family / 0 recurring" unexplained).
6. **Attention-signal basis always lists all factors** even when a factor
   contributes ~nothing; requirement states only contributing factors should be
   shown.
7. **SIF result not surfaced** in the UI (classification only shown; confidence,
   reason, supporting evidence, model note hidden).
8. **Evidence not surfaced** in the UI (narrative shown, spans hidden).
9. **Similar-wording-different-mechanism demo case missing** from the seed
   experience (Category 4 of PRD §20) — eval set has 6 categories but not an
   explicit opposite-meaning-pair demo record set; demo relies on
   hard-negative category only.
10. **Docs**: `docs/MVP_AUDIT.md`, `ARCHITECTURE.md`, `EVALUATION.md`,
    `DEMO_FLOW.md` do not exist yet.

## Negation-priority note (reviewed, left unchanged)

`absent` (priority 8) precedes `negated` (priority 7) so that "guard was not
in place / not installed" classify as absent, not not_verified. This means the
generic `missing` cue can pre-empt the specific `verification missing`
(negated-7) cue; acceptable for now, tracked for calibration.

## Scope of this improvement pass

Extraction coverage, field-evidence persistence, WHY GROUPED / WHY NOT GROUPED
as first-class family data, explicit recurring threshold, contributing-factors-
only attention basis, SIF/evidence UI, demo seed with Category-4 cases, docs,
and a final measured evaluation.