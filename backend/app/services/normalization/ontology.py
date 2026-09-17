"""Ontology loader: canonical vocabulary + synonym lookup.

The ontology is the single source of canonicalization. It is stored as JSON in
``data/ontology`` and loaded once at startup.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.config import get_settings


@dataclass(frozen=True)
class Concept:
    code: str
    label: str
    category: str
    synonyms: tuple[str, ...] = ()
    meta: dict = None

    def __post_init__(self) -> None:
        if self.meta is None:
            object.__setattr__(self, "meta", {})


_NORM_RE = re.compile(r"[^a-z0-9 ]+")


def normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    return _NORM_RE.sub(" ", text.lower())


class Ontology:
    """Holds every canonical concept and a synonym index per category."""

    CONCEPT_FILE_KEYS = {
        "activity": "activities",
        "task_phase": "task_phases",
        "energy": "energies",
        "barrier": "barriers",
        "barrier_state": "barrier_states",
        "exposure": "exposures",
        "consequence": "consequences",
        "location": "locations",
    }

    def __init__(self, root: Path | None = None) -> None:
        root = root or get_settings().ontology_root
        self._root = root
        self._concepts: dict[str, dict[str, Concept]] = {}
        self._synonyms: dict[str, list[tuple[str, str, str]]] = {}
        self._load()

    def _load(self) -> None:
        for category, filename in self.CONCEPT_FILE_KEYS.items():
            path = self._root / f"{filename}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            items = data[filename] if isinstance(data, dict) else data
            self._concepts[category] = {}
            syn_index: list[tuple[str, str, str]] = []
            for item in items:
                code, label = item["code"], item["label"]
                synonyms = list(item.get("synonyms", []))
                meta = {k: v for k, v in item.items() if k not in ("code", "label", "synonyms")}
                concept = Concept(code=code, label=label, category=category,
                                  synonyms=tuple(sorted({label.lower(), *synonyms}, key=len)),
                                  meta=meta)
                self._concepts[category][code] = concept
                for syn in concept.synonyms:
                    norm = normalize_text(syn)
                    if norm:
                        syn_index.append((len(norm), norm, code))
            syn_index.sort(reverse=True)
            self._synonyms[category] = syn_index

        # LSR + family templates + SIF rules are loaded on demand.
        self._lsr: dict = {}
        self._family_templates: dict = {}
        self._sif_rules: dict = {}
        self._negation_cues: dict = {}
        self._load_aux()

    def _load_aux(self) -> None:
        def _read(name: str) -> dict:
            path = self._root / name
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
            return {}

        self._lsr = _read("lsr_map.json")
        self._family_templates = _read("family_templates.json")
        self._sif_rules = _read("sif_rules.json")
        self._negation_cues = _read("negation_cues.json")

    # ------------------------------------------------------------------ API

    def concept(self, category: str, code: str) -> Concept | None:
        return self._concepts.get(category, {}).get(code)

    def codes(self, category: str) -> list[str]:
        return list(self._concepts.get(category, {}))

    def labels(self, category: str) -> dict[str, str]:
        return {c: self._concepts[category][c].label
                for c in self._concepts.get(category, {})}

    def concepts(self, category: str) -> list[Concept]:
        return list(self._concepts.get(category, {}).values())

    def label(self, category: str, code: str) -> str:
        c = self.concept(category, code)
        return c.label if c else code.replace("_", " ").title()

    def is_known(self, category: str, code: str) -> bool:
        return code in self._concepts.get(category, {})

    def is_known_lsr(self, code: str) -> bool:
        return any(r.get("code") == code for r in self._lsr.get("rules", []))

    def map(self, text: str, category: str) -> tuple[str, str]:
        """Return (canonical_code, matched_synonym); ('',' ') if no match."""
        norm = normalize_text(text)
        if not norm:
            return "", ""
        padded = f" {norm} "
        for span_len, syn, code in self._synonyms.get(category, []):
            token = f" {syn} "
            if token in padded:
                return code, syn.strip()
        return "", ""

    def lsr_table(self) -> dict:
        return self._lsr

    def family_templates(self) -> dict:
        return self._family_templates

    def sif_rules(self) -> dict:
        return self._sif_rules

    def negation_cues(self) -> dict:
        return self._negation_cues

    def energy_rank(self, code: str) -> int:
        c = self.concept("energy", code)
        return int(c.meta.get("severity_rank", 1)) if c else 1

    def exposure_rank(self, code: str) -> int:
        c = self.concept("exposure", code)
        return int(c.meta.get("severity_rank", 1)) if c else 1


@lru_cache
def get_ontology() -> Ontology:
    return Ontology()