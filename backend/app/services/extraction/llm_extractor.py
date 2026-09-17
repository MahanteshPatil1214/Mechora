"""Gemini LLM extraction service.

Used when a GEMINI_API_KEY is present and the provider config allows it. The
model must reply with JSON that conforms to the strict LLMExtraction schema
(extra fields forbidden). Any failure raises so the pipeline can fall back to
the deterministic rule extractor.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import Settings
from app.models.safety_event import LLMExtraction
from app.services.normalization.ontology import Ontology

logger = logging.getLogger("mechora.extraction.llm")

_SYSTEM_INSTRUCTION = """You are the structured-extraction component of MECHORA,
a safety-intelligence platform. Convert the safety observation narrative into a
structured safety event using ONLY canonical codes from the provided vocabulary.

Rules:
- Use canonical codes exactly as provided; do not invent new codes.
- If the narrative does not contain enough information, use "unknown".
- NEVER fabricate evidence. Evidence must be verbatim or near-verbatim spans from
  the narrative.
- Preserve safety-critical negation: "isolation was not verified" MUST produce
  barrier_state "not_verified"; "isolation was verified" MUST produce "verified".
- barrier_state must be one of: verified, not_verified, failed,
  partially_effective, absent, unknown.
- life_saving_rules: choose the most relevant IOGP Life-Saving Rule codes only.
- confidence: your self-assessed confidence for the whole extraction (0..1).
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
EXPOSURE: {_join('exposure')}
CONSEQUENCE (actual + potential): {_join('consequence')}
LOCATION: {_join('location')}
LIFE_SAVING_RULES: {_join('lsr')}

Return JSON with exactly these keys (all strings except life_saving_rules/evidence
arrays and confidence number):
activity, task_phase, hazard, energy, unsafe_action, unsafe_condition, barrier,
barrier_state, exposure, actual_consequence, potential_consequence, location,
life_saving_rules, evidence, confidence

NARRATIVE:
{{narrative}}
"""


class LLMExtractor:
    """Gemini-backed extractor. Provider is 'llm'."""

    def __init__(self, ontology: Ontology, settings: Settings) -> None:
        self.ontology = ontology
        self.settings = settings
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import google.generativeai as genai  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("google-generativeai not installed") from exc
        if not self.settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")
        genai.configure(api_key=self.settings.gemini_api_key)
        self._client = genai.GenerativeModel(
            self.settings.gemini_model,
            system_instruction=_SYSTEM_INSTRUCTION,
        )
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
            "lsr": list(ontology.lsr_table().get("rules", [])),
        }

    def extract(self, report_id: str, narrative: str) -> tuple[LLMExtraction, dict]:
        client = self._get_client()
        prompt = _build_prompt(self._vocab(self.ontology)).format(
            narrative=narrative
        )
        resp = client.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.0,
            },
        )
        raw = resp.text
        if not raw:
            raise ValueError("empty LLM response")
        # Some Gemini variants wrap JSON in ```json fences.
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        data = json.loads(cleaned)
        extraction = LLMExtraction.model_validate(data)
        if not isinstance(data.get("life_saving_rules", []), list):
            raise ValueError("malformed life_saving_rules")
        return extraction, {"provider": "llm"}

    def available(self) -> bool:
        try:
            self._get_client()
            return True
        except Exception:  # noqa: BLE001
            return False