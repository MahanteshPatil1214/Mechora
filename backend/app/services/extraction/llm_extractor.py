"""Gemini LLM extraction service (google.genai).

Used when a GEMINI_API_KEY is present and the provider config allows it. The
model must reply with JSON that conforms to the strict LLMExtraction schema.
Output is normalized at the boundary before validation so a single invalid
canonical value (for example an exposure code leaked into
``potential_consequence``) can never abort the whole LLM path: the value
degrades to ``unknown`` and the deterministic safety layers stay authoritative.
Only genuinely malformed responses raise, so the pipeline can fall back to the
rule extractor.
"""

from __future__ import annotations

import json
import logging
from typing import Any, get_args

from app.config import Settings
from app.models.safety_event import (
    ACTIVITY_CODES,
    BARRIER_CODES,
    BARRIER_STATE_CODES,
    CONSEQUENCE_CODES,
    ENERGY_CODES,
    EXPOSURE_CODES,
    LLMExtraction,
    LSR_CODES,
    LOCATION_CODES,
    TASK_PHASE_CODES,
)
from app.services.normalization.ontology import Ontology

logger = logging.getLogger("mechora.extraction.llm")

_SYSTEM_INSTRUCTION = """You are the extraction component of MECHORA, a
safety-intelligence platform. Convert the safety observation narrative into a
structured safety event using ONLY the canonical codes supplied in the prompt.
Fill every field you can support; leave genuinely unsupported fields "unknown".
Do not invent codes and do not guess on missing evidence.

IMPLICIT-CONCEPT MAPPING. Safety reports often describe a hazard through
contextual wording instead of naming a code. Map that wording to the existing
vocabulary whenever the narrative supports it:

1. ENERGY (stored/pressurized energy). Pressure and containment wording is
   energy evidence: "stored pressure", "pressure had been released", "residual
   pressure", "no pressure was confirmed", "flange/joint/line under pressure",
   "depressurized". The contained SUBSTANCE selects the code: a liquid or
   liquid-like substance (crude oil, oil, hydrocarbon liquid, hot liquid, hot
   fluid, slurry, acid, caustic) -> pressurized_liquid; a gas or vapour ->
   pressurized_gas; pressurized steam / steam line -> thermal_energy. "Hot
   fluid" / "hot liquid" describe a hot liquid substance; they do NOT by
   themselves mean thermal energy.

2. EXPOSURE (uncontrolled release). Escape/release wording is exposure
   evidence: "fluid escaped", "fluid escaped from the connection",
   "hot fluid escaped", "release", "leak", "spill". The SUBSTANCE that escaped
   selects the code: liquid/hydrocarbon/hot fluid -> uncontrolled_liquid_release;
   gas -> uncontrolled_gas_release; steam -> uncontrolled_steam_release.

3. A "hissing sound" is a corroborating sign that pressurized containment was
   breached and something escaped; treat it as supporting release evidence, not
   as a code, and classify the release by the escaped substance.

4. If the narrative reports a release of a hot/pressurized liquid during
   maintenance work, energy = pressurized_liquid and exposure =
   uncontrolled_liquid_release are the EXPECTED codes. Do not fall back to
   "unknown" when those facts are stated.

5. Honest unknown: if the narrative genuinely does not state the substance or
   the release, return "unknown" rather than guessing. Prefer the supported
   canonical code over "unknown" when the underlying facts are present.

6. BARRIER = the REQUIRED safety control/mechanism that should protect against
   the hazard, taken from the BARRIER list. Reports usually name the control's
   PURPOSE or its FAILURE instead of the code. Map a described control to an
   EXISTING canonical barrier when the surrounding narrative supports it:
   - vessel/pit/tank/silo entry context: "entry controls", "entry permit",
     "confined space controls", "atmosphere testing", "atmosphere was checked",
     "gas monitoring", "oxygen checked", "space was safe for entry", "standby
     attendant", ventilation FOR THE ENTRY -> confined_space_procedure.
   - "isolation", "lockout/tagout", "zero energy", "depressurized" ->
     energy_isolation.
   - "permit to work", "authorization", "approval" -> work_permit.
   - guardrails, harness, lifelines, anchor points -> fall_protection.
   - "fire watch", hot-work gas testing -> hot_work_controls.
   - machine guards, interlocks -> machinery_guarding.
   - lift/crane/exclusion-zone plans -> lifting_controls.
   A described control that was MISSING, SKIPPED, UNVERIFIED, FAILED, ABSENT or
   INEFFECTIVE is STILL that canonical barrier: the failure belongs in
   barrier_state (not_verified/failed/absent/partially_effective), while
   barrier keeps the control that SHOULD have been in place. Do not return
   "unknown" for the barrier merely because the control failed.

7. Reason barrier from NARRATIVE evidence, not from the Life-Saving Rules - the
   LSR is the outcome, not the cause. Correct order: narrative evidence ->
   required control -> canonical barrier -> barrier state -> life_saving_rules.
   Never derive the barrier from the Life-Saving Rules. When the narrative says
   the entry controls were not verified, "required entry controls had not been
   verified" is the entry-control evidence that makes barrier =
   confined_space_procedure (the confined_space_entry rule alone is not enough).

8. barrier evidence must be a verbatim narrative span that names or describes
   the control (e.g. "required entry controls had not been verified", widened
   with the surrounding vessel-entry/atmosphere context when useful) and MUST
   be added to the "evidence" array (one verbatim span per filled field).
   Never invent a span. When the narrative offers no evidence for any
   canonical barrier, keep barrier "unknown" rather than guessing.

OTHER RULES:
- Preserve safety-critical negation: "isolation was not verified" MUST produce
  barrier_state "not_verified"; "isolation was verified" MUST produce "verified".
- barrier_state must be one of: verified, not_verified, failed,
  partially_effective, absent, unknown.
- EXPOSURE and CONSEQUENCE are DIFFERENT fields with DIFFERENT vocabularies:
  exposure = what could reach people or equipment (uncontrolled_liquid_release,
  uncontrolled_gas_release, uncontrolled_steam_release, thermal_burn). It comes
  from the EXPOSURE list.
  potential_consequence = the possible outcome for people/assets, using ONLY
  the CONSEQUENCE list (injury, fatality, fire, explosion). NEVER copy an
  EXPOSURE code into potential_consequence: thermal_burn and
  uncontrolled_steam_release are exposure codes, NOT consequences. If no
  CONSEQUENCE code maps cleanly, set potential_consequence to "unknown".
- life_saving_rules: choose the most relevant IOGP Life-Saving Rule codes only.
- confidence: your self-assessed confidence for the whole extraction (0..1).
- NEVER fabricate evidence. Evidence must be verbatim or near-verbatim spans
  from the narrative, and every filled field deserves a supporting span.
"""


def _build_prompt(vocab: dict[str, list[str]]) -> str:
    def _join(key: str) -> str:
        return ", ".join(vocab.get(key, []))

    return f"""Extract the structured safety event from the narrative below.

Allowed canonical codes:

ACTIVITY: {_join('activity')}
TASK_PHASE: {_join('task_phase')}
ENERGY (hazardous energy): {_join('energy')}
BARRIER (required safety barrier): {_join('barrier')}
EXPOSURE (what could reach people/equipment): {_join('exposure')}
CONSEQUENCE (possible outcome; potential_consequence uses ONLY these codes):
  {_join('consequence')}
LOCATION: {_join('location')}
LIFE_SAVING_RULES: {_join('lsr')}

Implicit-concept hints (contextual wording -> existing codes):
- "stored pressure", "pressure had been released", "flange/joint under pressure",
  "depressurized" indicate stored/pressurized energy; choose pressurized_liquid
  for a liquid substance (crude oil, hot liquid, hydrocarbon liquid) or
  pressurized_gas for a gas/vapour (steam under pressure -> thermal_energy).
- "fluid escaped", "hot fluid escaped", "release", "leak", "spill" indicate an
  uncontrolled release exposure; choose uncontrolled_liquid_release for
  liquid/hydrocarbon/hot fluid, uncontrolled_gas_release for gas,
  uncontrolled_steam_release for steam. A "hissing sound" corroborates a release
  but is not a code.
- A maintenance release of a hot/pressurized liquid should report energy =
  pressurized_liquid and exposure = uncontrolled_liquid_release.
- BARRIER = the required safety control/mechanism that should protect against
  the hazard, chosen from the BARRIER list. A described control that was
  MISSING, SKIPPED, UNVERIFIED, FAILED, ABSENT or INEFFECTIVE is still that
  canonical barrier; record its failure separately in barrier_state. Vessel/
  pit/tank entry context ("entry controls", "entry permit", "atmosphere tested
  or checked", "gas monitoring", "space was safe for entry", confined-space
  ventilation) -> confined_space_procedure; isolation/lockout/depressurization
  -> energy_isolation; permit/authorization -> work_permit; guardrails/harness/
  lifelines -> fall_protection; fire watch/gas testing -> hot_work_controls.
  Ground barrier in a verbatim evidence span such as
  "required entry controls had not been verified". Never derive the barrier from the Life-Saving Rules.
- Map a phrase to a code only when the narrative supports it. If evidence is
  genuinely insufficient, return "unknown" rather than guessing.

Field contract:
- exposure and potential_consequence are SEPARATE fields with SEPARATE
  vocabularies. Never place an EXPOSURE value (e.g. thermal_burn,
  uncontrolled_steam_release) into potential_consequence.
- potential_consequence must be exactly one of the CONSEQUENCE codes above; if
  none maps cleanly, return "unknown".
- actual_consequence is short free text (verbatim outcome stated in the
  narrative, or "unknown").

Return JSON with exactly these keys (all strings except life_saving_rules/evidence
arrays and confidence number):
activity, task_phase, hazard, energy, unsafe_action, unsafe_condition, barrier,
barrier_state, exposure, actual_consequence, potential_consequence, location,
life_saving_rules, evidence, confidence

NARRATIVE:
{{narrative}}
"""


# Canonical-code fields and the exact values each may take. Normalization uses
# these sets (mirroring the Literal types) to degrade outliers to "unknown".
_CANONICAL_ALLOWED: dict[str, frozenset[str]] = {
    "activity": frozenset(get_args(ACTIVITY_CODES)),
    "task_phase": frozenset(get_args(TASK_PHASE_CODES)),
    "energy": frozenset(get_args(ENERGY_CODES)),
    "barrier": frozenset(get_args(BARRIER_CODES)),
    "barrier_state": frozenset(get_args(BARRIER_STATE_CODES)),
    "exposure": frozenset(get_args(EXPOSURE_CODES)),
    "potential_consequence": frozenset(get_args(CONSEQUENCE_CODES)),
    "location": frozenset(get_args(LOCATION_CODES)),
}

_LSR_ALLOWED = frozenset(get_args(LSR_CODES))

_TEXT_FIELDS_MAX: dict[str, int] = {
    "hazard": 300,
    "unsafe_action": 500,
    "unsafe_condition": 500,
    "actual_consequence": 300,
}

_EVIDENCE_MAX = 40


def _normalize_payload(data: Any) -> dict[str, Any]:
    """Normalize raw Gemini JSON so LLMExtraction can always validate it.

    Preserves every usable value but degrades gracefully instead of raising on
    common failure modes (invalid canonical code, wrong type, overlong text or
    a leaked exposure-as-consequence). One bad field must never discard the
    whole extraction; the deterministic layers re-derive safety semantics.
    """
    if not isinstance(data, dict):
        raise ValueError("Gemini response is not a JSON object")

    normalized: dict[str, Any] = {}
    for key, value in data.items():
        if key not in LLMExtraction.model_fields:
            logger.warning("Gemini returned unexpected key=%r; dropped.", key)
            continue
        if key in _CANONICAL_ALLOWED:
            normalized[key] = (
                value
                if isinstance(value, str) and value in _CANONICAL_ALLOWED[key]
                else "unknown"
            )
        elif key == "life_saving_rules":
            values = value if isinstance(value, list) else []
            normalized[key] = [
                item for item in values
                if isinstance(item, str) and item in _LSR_ALLOWED
            ]
        elif key == "evidence":
            values = value if isinstance(value, list) else []
            normalized[key] = [
                item for item in values if isinstance(item, str)
            ][:_EVIDENCE_MAX]
        elif key == "confidence":
            normalized[key] = (
                value
                if isinstance(value, (int, float)) and not isinstance(value, bool)
                else 0.0
            )
        elif key in _TEXT_FIELDS_MAX:
            text = value if isinstance(value, str) else "unknown"
            normalized[key] = text[:_TEXT_FIELDS_MAX[key]]
        else:
            normalized[key] = value
    return normalized


class LLMExtractor:
    """Gemini-backed extractor (google.genai). Provider is 'llm'."""

    def __init__(self, ontology: Ontology, settings: Settings) -> None:
        self.ontology = ontology
        self.settings = settings
        self._client: Any = None
        self._genai_types: Any = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from google import genai  # type: ignore
            from google.genai import types as genai_types  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("google-genai not installed") from exc
        if not self.settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")
        self._genai_types = genai_types
        self._client = genai.Client(api_key=self.settings.gemini_api_key)
        return self._client

    @staticmethod
    def _vocab(ontology: Ontology) -> dict[str, list[str]]:
        return {
            "activity": ontology.codes("activity"),
            "task_phase": ontology.codes("task_phase"),
            "energy": ontology.codes("energy"),
            "barrier": ontology.codes("barrier"),
            "exposure": ontology.codes("exposure"),
            "consequence": ontology.codes("consequence"),
            "location": ontology.codes("location"),
            "lsr": [r.get("code", "") for r in ontology.lsr_table().get("rules", []) if r.get("code")],
        }

    def extract(self, report_id: str, narrative: str) -> tuple[LLMExtraction, dict]:
        client = self._get_client()
        prompt = _build_prompt(self._vocab(self.ontology)).format(
            narrative=narrative
        )
        if self._genai_types is None:  # client was mocked; import normally
            from google.genai import types as genai_types  # type: ignore

            self._genai_types = genai_types
        resp = client.models.generate_content(
            model=self.settings.gemini_model,
            contents=prompt,
            config=self._genai_types.GenerateContentConfig(
                system_instruction=_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        raw = resp.text
        if not raw:
            raise ValueError("empty LLM response")
        # Some model variants wrap JSON in ```json fences.
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        if not cleaned:
            raise ValueError("empty LLM response")
        data = json.loads(cleaned)
        extraction = LLMExtraction.model_validate(_normalize_payload(data))
        return extraction, {"provider": "llm"}

    def available(self) -> bool:
        try:
            self._get_client()
            return True
        except Exception:  # noqa: BLE001
            return False