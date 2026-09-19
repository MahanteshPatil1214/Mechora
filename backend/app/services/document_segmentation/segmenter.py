"""Document segmentation for uploaded HSE observation reports.

The extraction layer returns raw multi-observation text (a PDF/DOCX may
contain several independent reports plus non-report material).  This layer
splits it into *report segments* so each observation is analyzed independently
and persisted separately:

- blocks that are NOT report body (report heading runs, page headers/footers,
  metadata ``Label:`` lines, ``Expected Test Signals`` instructional blocks,
  template instructions) are classified ``non_report`` and are excluded from
  analysis, evidence and traceability;
- consecutive report-body blocks are grouped into one segment per report.

Structural cues used (no NLP):
    blank-line paragraph splits,
    report heading patterns (``Report 2``), metadata-label lines (``Label:``),
    instructional headings (``Expected Test Signals``) and sentence-boundary
    fragments that follow them.

An instructional heading swallows everything that follows it up to the NEXT
report heading, so the "Expected Test Signals" block (heading + bullets/table
fragments) never leaks into any report's analysis or evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

MIN_REPORT_CHARACTERS = 8

_RE_REPORT_HEADING = re.compile(
    r"^\s*(?:(?:report|incident|observation|record)|hse report|safety report)\b"
    r"[\s#:.\-]*(?=\d|[A-Z0-9])",
    re.IGNORECASE,
)
_RE_INSTRUCTIONAL_HEADING = re.compile(
    r"^\s*(?:expected test signals|expected signals|test signals|"
    r"instructions?|template|mock|simulation|synthetic|demo|"
    r"for demonstration|this document|example.?only|sample)", 
    re.IGNORECASE,
)
# Explicit document boundary markers: everything from such a heading onward is
# non-report material. Matches the "NON-REPORT" heading used in uploaded demo
# documents ("NON-REPORT / Expected Test Signals / instructions") as well as
# other "excluded section" phrasings.
_RE_NON_REPORT_HEADING = re.compile(
    r"^\s*(?:non[- ]?report|non[- ]?relevant|not part of(?: the)? report|"
    r"not a report|excluded|excluded content|excluded material|"
    r"do not analyze|not for analysis|unrelated|appendix)"
    r"[:\s.]?(?:$|[A-Z0-9])",
    re.IGNORECASE,
)
_RE_METADATA_LABEL = re.compile(
    r"^\s*label\s*:\s+.*$", re.IGNORECASE,
)
_KNOWN_METADATA_KEYS = frozenset(
    {
        "plant", "facility", "date", "time", "shift", "team", "area",
        "location", "equipment", "equipment id", "unit", "report no",
        "report number", "reference", "observer", "reporter", "supervisor",
        "name", "company", "reviewer", "status", "document no",
        "document number", "version", "revision", "page",
    }
)
_RE_METADATA_KEY = re.compile(
    r"^\s*([A-Za-z][A-Za-z0-9 /\-]*?)\s*:\s+\S.*$"
)
_RE_PAGE_FOOTER = re.compile(
    r"^\s*(?:page\s+\d+\s+(?:of\s+(?:\d+|x))?|\d+\s*/\s*\d+|\bpage\b\s*\d+|\d+[.]?|[IVX]+)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Block:
    """A maximal run of non-blank lines that share a kind."""

    kind: str
    heading: str = ""
    lines: tuple[str, ...] = ()

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    @property
    def character_count(self) -> int:
        return len(self.text)


@dataclass
class ReportSegment:
    index: int
    kind: str
    heading: str = ""
    text: str = ""
    character_count: int = 0

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "kind": self.kind,
            "heading": self.heading,
            "text": self.text,
            "character_count": self.character_count,
        }


def _split_paragraphs(text: str) -> list[list[str]]:
    """Split normalized text into paragraphs (runs separated by blank lines).

    A UTF-8 BOM on the first line is stripped: it is file furniture, not part
    of the document wording, and would otherwise glue the first heading to its
    body.
    """
    cleaned = (text or "").lstrip("\ufeff")
    paragraphs: list[list[str]] = []
    current: list[str] = []
    for line in cleaned.splitlines():
        if not line.strip():
            if current:
                paragraphs.append(current)
                current = []
        else:
            current.append(line)
    if current:
        paragraphs.append(current)
    return paragraphs


def _classify_line(line: str) -> str | None:
    """Kind for a standalone line, or ``None`` for plain report body."""
    if _RE_PAGE_FOOTER.match(line):
        return "non_report"
    if _RE_METADATA_LABEL.match(line):
        return "non_report"
    m = _RE_METADATA_KEY.match(line)
    if m and m.group(1).strip().lower() in _KNOWN_METADATA_KEYS:
        return "non_report"
    return None


def _split_metadata_lines(paragraph: list[str]) -> list[Block]:
    """Isolate metadata/label/footer lines as their own non-report blocks."""
    blocks: list[Block] = []
    run: list[str] = []
    for line in paragraph:
        if _classify_line(line) == "non_report":
            if run:
                blocks.append(Block(kind="report", lines=tuple(run)))
                run = []
            blocks.append(Block(kind="non_report", lines=(line,)))
        else:
            run.append(line)
    if run:
        blocks.append(Block(kind="report", lines=tuple(run)))
    return blocks


def _opens_non_report(line: str) -> bool:
    """True if ``line`` is a NON-REPORT marker or an instructional heading."""
    return bool(
        _RE_NON_REPORT_HEADING.match(line) or _RE_INSTRUCTIONAL_HEADING.match(line))

def _split_non_report_boundaries(block: Block) -> list[Block]:
    """Split a REPORT block at any NON-report marker.

    A NON-REPORT marker or instructional heading anywhere inside a report
    paragraph terminates the report run: the lines up to the marker stay part
    of the report, the marker line and everything after it in the paragraph
    become a single non-report block.
    """
    sub: list[Block] = []
    run: list[str] = []
    for i, line in enumerate(block.lines):
        if _opens_non_report(line):
            if run:
                sub.append(Block(kind="report", lines=tuple(run)))
            sub.append(Block(
                kind="non_report",
                heading=line,
                lines=tuple(block.lines[i:]),
            ))
            return sub
        run.append(line)
    if run:
        sub.append(Block(kind="report", lines=tuple(run)))
    return sub


class ReportSegmenter:
    """Structural segmentation of one extracted document into reports."""

    def split_blocks(self, text: str) -> list[Block]:
        """Classified blocks, .report/non_report, in document order."""
        blocks: list[Block] = []
        for paragraph in _split_paragraphs(text or ""):
            for blk in _split_metadata_lines(paragraph):
                if blk.kind == "non_report":
                    blocks.append(blk)
                    continue
                for sub in _split_non_report_boundaries(blk):
                    if sub.kind == "non_report":
                        blocks.append(sub)
                        continue
                    first = sub.lines[0] if sub.lines else ""
                    if _RE_REPORT_HEADING.match(first):
                        blocks.append(Block(
                            kind="report", heading=first, lines=sub.lines))
                    else:
                        blocks.append(Block(kind="report", lines=sub.lines))
        return blocks

    def segment(self, text: str) -> list[ReportSegment]:
        """All segments (report and non_report) in document order."""
        blocks = self.split_blocks(text)
        segments: list[ReportSegment] = []
        # State machine: an instructional heading swallows everything up to the
        # next report heading. A report heading closes any open segment and
        # starts a new one. Metadata/label/page blocks are TRANSPARENT: they do
        # not break the open segment, so "Report 1" + metadata + body still
        # form a single report segment (metadata itself is dropped).
        consuming: bool = False
        current: dict | None = None
        for blk in blocks:
            if blk.kind == "non_report":
                if blk.heading:
                    # boundary marker (NON-REPORT section / instructional
                    # heading): close any open report and swallow everything
                    # after it up to the next report heading.
                    if current is not None:
                        segments.append(_finish(current, index=len(segments)))
                        current = None
                    consuming = True
                    segments.append(ReportSegment(
                        index=len(segments), kind="non_report",
                        heading=blk.heading, text=blk.text,
                        character_count=blk.character_count))
                    continue
                # transparent surface material: keep the open segment intact.
                segments.append(ReportSegment(
                    index=len(segments), kind="non_report",
                    heading=blk.heading, text=blk.text,
                    character_count=blk.character_count))
                continue
            # report block
            if current is not None and not blk.heading and not consuming:
                current["lines"].extend(blk.lines)
                continue
            if current is not None:
                segments.append(_finish(current, index=len(segments)))
                current = None
            if consuming and not blk.heading:
                # still inside the instructional block: not report material.
                continue
            consuming = False
            current = {
                "heading": blk.heading,
                "lines": list(blk.lines[1:] if blk.heading else blk.lines),
            }
        if current is not None:
            segments.append(_finish(current, index=len(segments)))
        return segments

    def reports(self, text: str) -> list[ReportSegment]:
        """Report segments only (non-report material excluded)."""
        out: list[ReportSegment] = []
        for seg in self.segment(text):
            if seg.kind == "report" and seg.character_count >= MIN_REPORT_CHARACTERS:
                out.append(seg)
        return out


def _finish(current: dict, index: int = 0) -> ReportSegment:
    text = "\n".join(current["lines"]).strip()
    return ReportSegment(
        index=index, kind="report", heading=current["heading"].strip(),
        text=text, character_count=len(text))