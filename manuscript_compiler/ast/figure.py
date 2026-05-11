"""Figure model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Figure:
    id: str = ""                     # unique ID for cross-ref
    caption: str = ""
    label: Optional[str] = None      # e.g. "Fig. 1"
    image_path: Optional[str] = None  # extracted image file path
    image_bytes_size: int = 0
    image_format: Optional[str] = None  # "png", "jpg", "emf", "wmf", etc.
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    subfigures: list = field(default_factory=list)

    # Traceability
    source_rel_id: Optional[str] = None  # OOXML relationship ID
    confidence: float = 1.0
    warnings: list[str] = field(default_factory=list)
    # Anchor (set by constraint layer)
    first_reference_section_id: str = ""
    # Layout: 1 = single-column, 2 = double-column (figure*)
    column_span: int = 1
