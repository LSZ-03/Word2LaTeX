"""Table model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TableCell:
    text: str = ""
    colspan: int = 1
    rowspan: int = 1
    bold: bool = False
    alignment: str = "left"           # "left", "center", "right"
    is_header: bool = False


@dataclass
class TableRow:
    cells: List[TableCell] = field(default_factory=list)


@dataclass
class Table:
    id: str = ""
    caption: str = ""
    label: Optional[str] = None       # e.g. "Table I"
    rows: List[TableRow] = field(default_factory=list)
    num_cols: int = 0
    num_rows: int = 0
    has_header_row: bool = False

    # Traceability
    source_xml: Optional[str] = None
    confidence: float = 1.0
    warnings: List[str] = field(default_factory=list)
    # Anchor (set by constraint layer)
    first_reference_section_id: str = ""
    # Table notes (footnotes / abbreviations that follow the table)
    notes: List[str] = field(default_factory=list)
    # Layout: 1 = single-column, 2 = double-column (table*)
    column_span: int = 1
