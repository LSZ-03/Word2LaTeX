"""Citation / Reference model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Citation:
    """A single bibliographic reference entry."""
    key: str = ""                      # cite key, e.g. "smith2024"
    authors: str = ""                  # formatted author string
    title: str = ""
    journal: Optional[str] = None
    booktitle: Optional[str] = None    # for conference papers
    year: Optional[str] = None
    volume: Optional[str] = None
    number: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    publisher: Optional[str] = None
    entry_type: str = "article"        # "article", "inproceedings", "book", etc.

    confidence: float = 1.0
    warnings: list[str] = field(default_factory=list)
