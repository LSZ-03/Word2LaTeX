"""Journal profile data model — extended with verification and catalog support.

This module defines the canonical profile format used throughout the system.
Built-in profiles (TGRS, IEEE, ICLR) live in __init__.py.
External profiles (from journal-manuscript catalog) are loaded from YAML files
via registry.py and parsed into the same JournalProfile dataclass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class VerificationCheck:
    """A single verification item tracked for a journal profile."""
    id: str
    title: str = ""
    requirement: str = ""
    status: str = "unchecked"  # verified | checklist-required | blocked | unchecked


@dataclass
class ValidationRule:
    """An automated LaTeX pattern check against the rendered main.tex.

    Use with the pipeline validation script to verify output compliance.
    """
    id: str
    description: str = ""
    pattern: str = ""            # regex pattern to search in main.tex
    severity: str = "warning"    # error | warning | info
    negate: bool = False         # True means "must NOT match"


@dataclass
class ManualCheck:
    """A manual verification item that requires human inspection."""
    id: str
    title: str = ""
    items: List[str] = field(default_factory=list)


@dataclass
class HouseStyle:
    """House style baseline — the typographic and structural rules."""
    section_order: List[str] = field(default_factory=list)
    float_spacing: Dict[str, str] = field(default_factory=dict)
    fonts: List[str] = field(default_factory=list)
    front_matter: List[str] = field(default_factory=list)


@dataclass
class CaptionPolicy:
    """Caption placement policy — where caption goes relative to float.

    Each position is either "above" or "below".
    """
    figure_position: str = "below"   # above | below
    table_position: str = "above"    # above | below


@dataclass
class FloatPolicy:
    """Float placement strategy for figures and tables.

    Strategies:
      near_reference   — place within ±2 paragraphs of first reference (IEEE/TGRS)
      top_preferred    — [!t] top-of-page, traditional two-column journals
      strict_stream    — strictly follow AST order, no rearrangement (Elsevier/Nature)
      global_allowed   — allow LaTeX global float pool (rare, discouraged)
    """
    strategy: str = "near_reference"


@dataclass
class JournalProfile:
    """Defines the LaTeX rendering rules for a specific journal.

    Attributes marked with [catalog] are loaded from the extended profile catalog
    (catalog/families/*/profile.yaml or catalog/journals/*/*/profile.yaml).
    Attributes without [catalog] are the core built-in fields.
    """

    # ── Core identity ──────────────────────────────────────────────
    name: str                                 # short slug, e.g. "tgrs"
    display_name: str = ""                    # human-readable, e.g. "IEEE TGRS"
    family: str = ""                          # [catalog] parent family slug

    # ── Document class ─────────────────────────────────────────────
    documentclass: str = "article"
    class_options: List[str] = field(default_factory=list)

    # ── Packages ───────────────────────────────────────────────────
    packages: List[str] = field(default_factory=list)
    package_options: dict = field(default_factory=dict)

    # ── Preamble ───────────────────────────────────────────────────
    preamble_extra: List[str] = field(default_factory=list)

    # ── Section numbering ──────────────────────────────────────────
    section_numbering: str = "arabic"          # arabic | roman | none
    section_depth: int = 3

    # ── Bibliography ───────────────────────────────────────────────
    bibliography_style: str = "ieeetr"
    bibliography_type: str = "thebibliography" # thebibliography | bibtex

    # ── Figures ────────────────────────────────────────────────────
    figure_max_width: str = r"0.9\columnwidth"
    figure_allowed_formats: List[str] = field(
        default_factory=lambda: ["pdf", "eps", "png", "jpg"]
    )
    figure_placement: str = "tbp"

    # ── Tables ─────────────────────────────────────────────────────
    table_placement: str = "tbp"
    table_default_align: str = "c"
    table_style: str = "booktabs"              # booktabs | standard

    # ── Caption style ──────────────────────────────────────────────
    caption_style: str = "bf"

    # ── Journal header ─────────────────────────────────────────────
    journal_header: str = ""
    journal_header_short: str = ""

    # ── Template source ────────────────────────────────────────────
    template_dir: str = ""                     # relative to templates/{name}/

    # ── [catalog] Verification & metadata ──────────────────────────
    status: str = "builtin"                    # builtin | verified | checklist-required | blocked
    official_source: str = ""                  # URL to official template/author guide
    template_package_url: str = ""             # URL to download official template
    template_package_path: str = ""            # local path to cached template
    house_style: Optional[HouseStyle] = None
    checks: List[VerificationCheck] = field(default_factory=list)
    validation_rules: List[ValidationRule] = field(default_factory=list)
    manual_checks: List[ManualCheck] = field(default_factory=list)

    # ── Caption & float policy (journal-aware) ─────────────────────
    caption_policy: Optional[CaptionPolicy] = None
    float_policy: Optional[FloatPolicy] = None

    def __post_init__(self):
        self._validate()

    def _validate(self):
        assert self.section_numbering in ("", "arabic", "roman", "none"), \
            f"Invalid section_numbering: {self.section_numbering}"
        assert self.bibliography_type in ("", "thebibliography", "bibtex"), \
            f"Invalid bibliography_type: {self.bibliography_type}"
        assert self.status in ("builtin", "verified", "checklist-required", "blocked"), \
            f"Invalid status: {self.status}"

    @property
    def template_path(self) -> Path:
        """Absolute path to the template directory."""
        return PROJECT_ROOT / "templates" / (self.template_dir or self.name)

    def merge_family_defaults(self, family: JournalProfile) -> None:
        """Inherit family-level defaults for fields that are falsy (empty/unset).

        A journal profile only needs to specify what differs from its family.
        Fields like bibliography_style, figure_placement, packages etc.
        inherit from the family baseline when left empty in the journal YAML.
        """
        inherit_fields = [
            "documentclass", "class_options", "packages", "package_options",
            "preamble_extra", "section_numbering", "section_depth",
            "bibliography_style", "bibliography_type",
            "figure_max_width", "figure_allowed_formats", "figure_placement",
            "table_placement", "table_default_align", "table_style", "caption_style",
        ]
        for field_name in inherit_fields:
            my_val = getattr(self, field_name)
            parent_val = getattr(family, field_name)
            # Empty string → inherit; empty list/dict → inherit
            if (isinstance(my_val, str) and not my_val) or \
               (isinstance(my_val, (list, dict)) and not my_val):
                setattr(self, field_name, parent_val)

        # Inherit caption_policy and float_policy if not set
        if self.caption_policy is None and family.caption_policy is not None:
            self.caption_policy = family.caption_policy
        if self.float_policy is None and family.float_policy is not None:
            self.float_policy = family.float_policy
