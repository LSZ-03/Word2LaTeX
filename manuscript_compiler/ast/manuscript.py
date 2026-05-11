"""Top-level Manuscript node."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from .section import Section
from .figure import Figure
from .table import Table
from .equation import Equation
from .citation import Citation


@dataclass
class Author:
    full_name: str
    email: Optional[str] = None
    affiliation: Optional[str] = None
    orcid: Optional[str] = None


@dataclass
class ManuscriptMetadata:
    title: str = ""
    authors: List[Author] = field(default_factory=list)
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    journal_target: Optional[str] = None


@dataclass
class ManuscriptWarning:
    source: str          # e.g. "docx_parser", "equation_repair"
    message: str
    severity: str        # "info" | "warning" | "error"


@dataclass
class Manuscript:
    """Top-level AST node — the entire converted manuscript."""

    metadata: ManuscriptMetadata = field(default_factory=ManuscriptMetadata)
    sections: List[Section] = field(default_factory=list)
    figures: List[Figure] = field(default_factory=list)
    tables: List[Table] = field(default_factory=list)
    equations: List[Equation] = field(default_factory=list)
    bibliography: List[Citation] = field(default_factory=list)
    appendices: List[Section] = field(default_factory=list)

    # Pipeline traceability
    source_file: str = ""
    run_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    pipeline_stage: str = ""
    overall_confidence: float = 1.0
    warnings: List[ManuscriptWarning] = field(default_factory=list)

    def all_paragraphs(self) -> List:
        """Recursively collect all paragraphs from all sections."""
        result = []
        def _walk(section):
            result.extend(section.paragraphs)
            for sub in section.subsections:
                _walk(sub)
        for sec in self.sections:
            _walk(sec)
        for sec in self.appendices:
            _walk(sec)
        return result
