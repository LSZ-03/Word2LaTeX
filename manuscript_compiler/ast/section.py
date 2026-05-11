"""Section / Paragraph / List models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class SemanticRole(Enum):
    INTRODUCTION = "introduction"
    RELATED_WORK = "related_work"
    METHOD = "method"
    EXPERIMENTS = "experiments"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    ACKNOWLEDGMENT = "acknowledgment"
    APPENDIX = "appendix"
    ABSTRACT = "abstract"
    UNKNOWN = "unknown"


@dataclass
class TextRun:
    """A contiguous styled text fragment within a paragraph."""
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    superscript: bool = False
    subscript: bool = False
    font_size: Optional[float] = None  # pt
    font_name: Optional[str] = None
    color_hex: Optional[str] = None


@dataclass
class ListItem:
    """A single item in a bulleted or numbered list."""
    text: str
    level: int = 0          # nesting depth (0 = top-level)
    number: Optional[str] = None  # "1.", "2.", "a)", bullet char, etc.
    children: List[ListItem] = field(default_factory=list)


@dataclass
class ListBlock:
    """A contiguous list (ordered or unordered)."""
    items: List[ListItem] = field(default_factory=list)
    ordered: bool = False   # True = numbered, False = bullet


@dataclass
class Paragraph:
    """A single paragraph of text with optional inline styling."""
    runs: List[TextRun] = field(default_factory=list)
    plain_text: str = ""            # plain text fallback (no style)
    style_name: Optional[str] = None  # Word style name (e.g. "Normal", "Body Text")
    alignment: Optional[str] = None   # "left", "center", "right", "justify"
    first_line_indent: Optional[float] = None
    # TOC / heading info
    is_heading: bool = False
    heading_level: int = 0         # 1-9 for Word Heading 1-9; 0 = not heading
    # Original position in docx (for inline element injection)
    paragraph_index: Optional[int] = None  # index in docx.paragraphs
    # Inline elements to inject after this paragraph
    inline_equation_ids: List[str] = field(default_factory=list)
    inline_figure_ids: List[str] = field(default_factory=list)
    inline_table_ids: List[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return self.plain_text or "".join(r.text for r in self.runs)


@dataclass
class Section:
    """A section (or subsection) of the manuscript."""

    id: str = ""
    title: str = ""
    level: int = 1                   # 1=section, 2=subsection, 3=subsubsection
    paragraphs: List[Paragraph] = field(default_factory=list)
    subsections: List[Section] = field(default_factory=list)
    lists: List[ListBlock] = field(default_factory=list)

    # Cross-references (IDs only, resolved at render time)
    figure_ids: List[str] = field(default_factory=list)
    table_ids: List[str] = field(default_factory=list)
    equation_ids: List[str] = field(default_factory=list)
    citation_keys: List[str] = field(default_factory=list)

    # Semantic role (for journal adaptation)
    semantic_role: SemanticRole = SemanticRole.UNKNOWN

    # Traceability
    source_page_range: Optional[str] = None
    confidence: float = 1.0
    warnings: List[str] = field(default_factory=list)
