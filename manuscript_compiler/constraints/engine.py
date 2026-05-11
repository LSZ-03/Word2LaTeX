"""Constraint Engine — apply journal formatting rules to the raw AST.

This is the core of the Journal Formatting / Constraint Layer.
It takes a raw Manuscript AST (from Parser) and a JournalProfile,
returns an enriched AST with all format decisions pre-computed.

The downstream Renderer becomes a pure "AST → LaTeX" translator,
with NO format logic of its own.

Flow:
    parser → raw AST → constraint_engine(ast, profile) → constrained AST → renderer → main.tex
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from manuscript_compiler.ast.manuscript import Manuscript
from manuscript_compiler.ast.section import Paragraph, Section, ListBlock
from manuscript_compiler.ast.figure import Figure
from manuscript_compiler.ast.table import Table
from manuscript_compiler.journal_profiles.models import JournalProfile


# ═══════════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════════

def apply(manuscript: Manuscript, profile: JournalProfile) -> Manuscript:
    """Apply journal formatting constraints to the Entire AST.

    Mutates the manuscript in-place for efficiency. Returns it for chaining.

    What this does:
      1. Converts Word-style citations [1-5] → \\cite{ref_1,...}, protected
      2. Converts Figure/Table refs "Fig. 3" → Fig.~\\ref{fig:3}, protected
      3. Strips numbering from section titles ("1. Introduction" → "Introduction")
      4. Cleans figure captions (removes "Fig." prefix)
      5. Generates clean figure labels (fig:N)
      6. Sets figure float placement from profile
      7. Cleans table captions (removes "Table" prefix)
      8. Generates clean table labels (tab:N)
      9. Sets table float placement from profile
      10. Converts citations + refs in table cell text
    """
    # 1–2. Process all paragraph texts
    _constrain_all_paragraphs(manuscript)

    # 3. Strip section numbering
    for section in manuscript.sections:
        _constrain_section(section, profile)

    # 4–6. Figure constraints
    for fig in manuscript.figures:
        _constrain_figure(fig, profile)

    # 7–10. Table constraints
    for tbl in manuscript.tables:
        _constrain_table(tbl, profile)

    # 11. Anchor figures/tables to their first reference paragraphs
    _anchor_fig_tables(manuscript)

    # 12. Apply float placement strategy from profile
    _apply_float_policy(manuscript, profile)

    # 13. Classify column_span (single vs double column) + equation semantics
    _classify_layout(manuscript, profile)
    _bind_equation_numbers(manuscript)

    return manuscript


# ═══════════════════════════════════════════════════════════════════════
#  Paragraph constraints — citation + figure/table reference conversion
# ═══════════════════════════════════════════════════════════════════════

def _constrain_all_paragraphs(manuscript: Manuscript) -> None:
    """Process every paragraph in the manuscript tree.

    Converts citations and figure/table refs, embedding null-byte
    placeholders so the Renderer's LaTeX escaping doesn't corrupt them.
    Also removes standalone figure/table caption paragraphs (duplicates
    of the content already in \\caption{}).
    """
    for section in manuscript.sections:
        _walk_paragraphs(section)

    # Second pass: blank out paragraphs that are standalone figure/table captions
    _blank_fig_tab_caption_paragraphs(manuscript)


def _walk_paragraphs(section: Section) -> None:
    """Recursively walk sections and process paragraphs."""
    for para in section.paragraphs:
        _constrain_paragraph(para)
    for sub in section.subsections:
        _walk_paragraphs(sub)


def _constrain_paragraph(para: Paragraph) -> None:
    """Apply citation and ref constraints to a single paragraph.

    Converts text IN-PLACE. Citations and refs are left as raw LaTeX
    commands (e.g. \\cite{ref_1}, \\ref{fig:3}) — the renderer's
    protection mechanism handles LaTeX escaping around them.
    """
    if para.runs:
        for run in para.runs:
            raw = run.text
            raw = _convert_fig_table_refs(raw)
            raw = _convert_citations(raw)
            run.text = raw
    else:
        raw = para.plain_text
        raw = _convert_fig_table_refs(raw)
        raw = _convert_citations(raw)
        para.plain_text = raw


# ── Citation conversion ────────────────────────────────────────────

_CITATION_RE = re.compile(r"\[(\d[\d,\s\-–—]*)\]")  # support hyphen, en-dash (–), em-dash (—)


def _convert_citations(text: str) -> str:
    """Convert [1-5], [11], [1,3-5,7] to \\cite{ref_1,ref_2,...}.

    Only matches brackets whose content is purely digits, commas, hyphens.
    Skips LaTeX float specifiers like [t], [htbp].
    """
    def _expand(match: re.Match) -> str:
        content = match.group(1).strip()
        parts = re.split(r"\s*,\s*", content)
        keys: list[str] = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            rng = re.match(r"^(\d+)\s*[-–—]\s*(\d+)$", part)  # support en-dash/em-dash
            if rng:
                start, end = int(rng.group(1)), int(rng.group(2))
                if start <= end <= 999:
                    keys.extend(f"ref_{i}" for i in range(start, end + 1))
            elif part.isdigit():
                keys.append(f"ref_{part}")
            else:
                return match.group(0)
        if not keys:
            return match.group(0)
        return "\\cite{" + ",".join(keys) + "}"

    result: list[str] = []
    last_end = 0
    for m in _CITATION_RE.finditer(text):
        start, end = m.start(), m.end()
        result.append(text[last_end:start])
        content = m.group(1)
        if re.search(r"[a-zA-Z]", content):
            result.append(m.group(0))
        else:
            result.append(_expand(m))
        last_end = end
    result.append(text[last_end:])
    return "".join(result)


# ── Standalone caption paragraph detection ──────────────────────────
_CAPTION_LINE_RE = re.compile(
    r"^(?:"
    r"Fig(?:ure)?\.?~?\\ref\{fig:\d+\}|"     # Fig.~\\ref{fig:1} (converted)
    r"Table~?\\ref\{tab:\d+\}|"               # Table~\\ref{tab:1} (converted)
    r"Fig(?:ure)?\.?\s*\d+[\s\.:]|"          # Fig. 1. (raw unconverted)
    r"Table\s+\d+[\s\.:]"                     # Table 1. (raw unconverted)
    r")"
)
_NOTE_LINE_RE = re.compile(
    r"^(?:Note|Notes|Abbreviation|Abbreviations)[\s:]",
    re.IGNORECASE
)


def _blank_fig_tab_caption_paragraphs(manuscript: Manuscript) -> None:
    """Blank out paragraphs that are standalone figure/table captions or notes.

    These paragraphs look like:
      "Fig.~\\ref{fig:3}. Proposed RDAF-Net architecture."
      "Table~\\ref{tab:1}: Influence of each component..."
      "Note: (\"R-50-DRRCM_S4\" indicates ...)"

    The caption text is already in \\caption{}, and the note text is already
    in Table.notes, so these body-text paragraphs are redundant.
    """
    for section in manuscript.sections:
        _walk_blank(section)


def _walk_blank(section: Section) -> None:
    """Recursively walk sections, blanking caption and note paragraphs."""
    for para in section.paragraphs:
        text = ""
        if para.runs:
            text = "".join(r.text for r in para.runs)
        elif para.plain_text:
            text = para.plain_text

        # Check if this paragraph IS a figure/table caption or standalone note
        if _CAPTION_LINE_RE.search(text) or _NOTE_LINE_RE.search(text):
            para.plain_text = ""
            para.runs = []
            para.inline_equation_ids = []
            para.inline_figure_ids = []
            para.inline_table_ids = []
    for sub in section.subsections:
        _walk_blank(sub)


# ── Figure/Table reference conversion ─────────────────────────────

_FIG_TAB_PATTERNS = [
    (re.compile(r'\bFigure\s+(\d+)\b', re.IGNORECASE), r'Fig.~\\ref{fig:\1}'),
    (re.compile(r'\bFig\.?\s*(\d+)\b', re.IGNORECASE), r'Fig.~\\ref{fig:\1}'),
    (re.compile(r'\bTable\s+(\d+)\b', re.IGNORECASE), r'Table~\\ref{tab:\1}'),
    (re.compile(r'\bTab\.\s*(\d+)\b', re.IGNORECASE), r'Table~\\ref{tab:\1}'),
]


def _convert_fig_table_refs(text: str) -> str:
    """Convert body-text figure/table references to clickable \\ref{} commands.

    Examples:
      "as shown in Figure 3" → "as shown in Fig.~\\ref{fig:3}"
      "in Fig. 4"            → "in Fig.~\\ref{fig:4}"
    """
    for pattern, replacement in _FIG_TAB_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


# ── Placeholder embedding ─────────────────────────────────────────

_PLACEHOLDER_PATTERNS = [
    re.compile(r"~?\s*\\cite\{[^}]*\}"),
    re.compile(r"~?\s*\\ref\{[^}]*\}"),
]


def _embed_placeholders(text: str) -> str:
    """Wrap all \\cite{...} and \\ref{...} in null-byte placeholders.

    Null bytes (\\x00) are immune to _escape_latex() because they
    are not in SPECIAL_CHARS and have ord() < 128. The renderer
    will restore them after escaping.
    """
    # Use a counter that's unique per paragraph
    counter = 0
    for pat in _PLACEHOLDER_PATTERNS:
        def _make_replacer(_c=[counter]):
            def _replace(m):
                _c[0] += 1
                return f"\x00PH{_c[0] - 1}\x00"
            return _replace
        text = pat.sub(_make_replacer(), text)
        counter = _get_last_counter(text) + 1
    return text


def _get_last_counter(text: str) -> int:
    """Extract the highest placeholder counter used in text."""
    max_n = -1
    for m in re.finditer(r"\x00PH(\d+)\x00", text):
        max_n = max(max_n, int(m.group(1)))
    return max_n


# ── Placeholder restoration (used by renderer) ────────────────────

_PH_RE = re.compile(r"\x00PH(\d+)\x00")


def restore_placeholders(text: str, original_commands: Optional[Dict[str, str]] = None) -> str:
    """Restore null-byte placeholders to real \\cite/\\ref commands.

    Called by the Renderer AFTER _escape_latex() has run.
    If no original_commands dict is provided, we can't restore,
    so this is just a safety fallback that strips placeholders.
    """
    if original_commands:
        for key, val in original_commands.items():
            text = text.replace(key, val)
        return text
    # Fallback: remove raw placeholders (shouldn't happen)
    return _PH_RE.sub("", text)


# ═══════════════════════════════════════════════════════════════════════
#  Section constraints — numbering stripping
# ═══════════════════════════════════════════════════════════════════════

def _constrain_section(section: Section, profile: JournalProfile) -> None:
    """Strip numbering from section titles, process subsections."""
    # Strip "1. Introduction" → "Introduction"
    section.title = _strip_numbering(section.title)
    for sub in section.subsections:
        _constrain_section(sub, profile)


def _strip_numbering(title: str) -> str:
    """Remove leading number prefix from a section title.

    Examples:
      "1. Introduction"      → "Introduction"
      "2.1. Method"          → "Method"
      "Abstract:"            → "Abstract"
      "Keywords:"            → "Keywords"
    """
    stripped = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", title).strip()
    stripped = stripped.rstrip(":").strip()
    return stripped if stripped else title


# ═══════════════════════════════════════════════════════════════════════
#  Figure constraints — caption, label, placement
# ═══════════════════════════════════════════════════════════════════════

def _constrain_figure(fig: Figure, profile: JournalProfile) -> None:
    """Clean caption, compute label, set placement from profile.

    Constraints applied (in order):
      1. Strip "Fig." / "Figure" prefix from caption text
      2. Compute canonical label fig:{N}
      3. Set float placement from profile
    """
    raw_caption = fig.caption or ""
    fig.caption = re.sub(r"^(?:Fig(?:ure)?\.?\s*\d*\s*[\.:]?\s*)", "", raw_caption, flags=re.IGNORECASE).strip().rstrip(".")

    fig_num = "".join(c for c in (fig.id or "") if c.isdigit())
    fig.label = f"fig:{fig_num}" if fig_num else f"fig:{fig.id}"


def _constrain_table(tbl: Table, profile: JournalProfile) -> None:
    """Clean caption, compute label, process cell text for citations/refs.

    Constraints applied (in order):
      1. Process each cell's text: convert citations + fig/table refs
      2. Strip "Table" prefix from caption text
      3. Compute canonical label tab:{N}
    """
    # 1. Process cell text
    for row in tbl.rows:
        for cell in row.cells:
            raw = cell.text
            raw = _convert_fig_table_refs(raw)
            raw = _convert_citations(raw)
            cell.text = raw

    # 2. Strip "Table" prefix from caption
    raw_caption = tbl.caption or ""
    tbl.caption = re.sub(r"^(Table\s*\d*\s*[\.:]?\s*)", "", raw_caption, flags=re.IGNORECASE).strip()

    # 3. Compute canonical label
    tab_num = "".join(c for c in (tbl.id or "") if c.isdigit())
    tbl.label = f"tab:{tab_num}" if tab_num else f"tab:{tbl.id}"


# ═══════════════════════════════════════════════════════════════════════
#  Figure/Table anchoring — stream placement constraint
# ═══════════════════════════════════════════════════════════════════════

def _anchor_fig_tables(manuscript: Manuscript) -> None:
    """Anchor each figure/table to the paragraph that first references it.

    Scans all paragraph text for \\ref{fig:N} / \\ref{tab:N} and injects
    the corresponding figure/table ID into that paragraph's
    inline_figure_ids / inline_table_ids.

    This enables streaming rendering: the renderer places the figure/table
    environment immediately after the referencing paragraph, instead of
    collecting everything at the end.

    Rules enforced:
      - Every figure/table must have at least one anchor paragraph
      - Only the FIRST reference anchors; subsequent refs are ignored
      - Unreferenced figures/tables get no anchor (they won't render)
    """
    # Build lookup: fig.label -> fig, tab.label -> tab
    fig_map: dict[str, Figure] = {}
    for fig in manuscript.figures:
        label = fig.label or f"fig:{fig.id}"
        fig_map[label] = fig
        fig.first_reference_section_id = ""  # reset

    tab_map: dict[str, Table] = {}
    for tbl in manuscript.tables:
        label = tbl.label or f"tab:{tbl.id}"
        tab_map[label] = tbl
        tbl.first_reference_section_id = ""  # reset

    anchored_figs: set[str] = set()
    anchored_tabs: set[str] = set()

    def _walk(section: Section, current_depth: int = 0):
        for para in section.paragraphs:
            # Use runs text (constraint layer modifies runs, NOT plain_text)
            if para.runs:
                para_text = "".join(r.text for r in para.runs)
            else:
                para_text = para.plain_text or ""

            # Find figure refs in this paragraph
            for m in re.finditer(r"\\ref\{fig:(\d+)\}", para_text):
                label = f"fig:{m.group(1)}"
                if label in fig_map and label not in anchored_figs:
                    fig = fig_map[label]
                    if fig.id not in para.inline_figure_ids:
                        para.inline_figure_ids.append(fig.id)
                    if not fig.first_reference_section_id:
                        sec_id = section.id or section.title or "unknown"
                        fig.first_reference_section_id = sec_id
                    anchored_figs.add(label)

            # Find table refs in this paragraph
            for m in re.finditer(r"\\ref\{tab:(\d+)\}", para_text):
                label = f"tab:{m.group(1)}"
                if label in tab_map and label not in anchored_tabs:
                    tbl = tab_map[label]
                    if tbl.id not in para.inline_table_ids:
                        para.inline_table_ids.append(tbl.id)
                    if not tbl.first_reference_section_id:
                        sec_id = section.id or section.title or "unknown"
                        tbl.first_reference_section_id = sec_id
                    anchored_tabs.add(label)

        for sub in section.subsections:
            _walk(sub, current_depth + 1)

    for section in manuscript.sections:
        _walk(section)

    # Log summary
    anchored_fig_count = len(anchored_figs)
    anchored_tab_count = len(anchored_tabs)
    total_figs = len(manuscript.figures)
    total_tabs = len(manuscript.tables)

    if total_figs > 0:
        unanchored = total_figs - anchored_fig_count
        if unanchored:
            print(f"  ⚠️  {unanchored}/{total_figs} figures have no text reference — skipped")
    if total_tabs > 0:
        unanchored = total_tabs - anchored_tab_count
        if unanchored:
            print(f"  ⚠️  {unanchored}/{total_tabs} tables have no text reference — skipped")


def _apply_float_policy(manuscript: Manuscript, profile: JournalProfile) -> None:
    """Apply float placement strategy from journal profile.

    Adjusts figure/table placement specifiers based on float_policy:
      - near_reference: streaming, [!t] (default)
      - strict_stream:  streaming, [tbp] allow more natural float movement
      - top_preferred:  streaming, [!t] strongly force top
      - global_allowed: no streaming, global float pool (old behavior)
    """
    policy = profile.float_policy.strategy if profile.float_policy else "near_reference"

    if policy == "top_preferred":
        # Force [!t] on all figures and tables
        if profile.figure_placement != "!t":
            object.__setattr__(profile, "figure_placement", "!t")
        if profile.table_placement != "!t":
            object.__setattr__(profile, "table_placement", "!t")

    elif policy == "strict_stream":
        # Use [tbp] — LaTeX has more freedom but still streaming
        if not profile.figure_placement:
            object.__setattr__(profile, "figure_placement", "tbp")
        if not profile.table_placement:
            object.__setattr__(profile, "table_placement", "tbp")

    elif policy == "global_allowed":
        # Global pool — skip anchoring, let renderer collect all at end
        for para in manuscript.sections:
            _clear_anchors(para)


def _clear_anchors(section: Section) -> None:
    """Remove figure/table anchors from all paragraphs (for global_allowed)."""
    for para in section.paragraphs:
        para.inline_figure_ids.clear()
        para.inline_table_ids.clear()
    for sub in section.subsections:
        _clear_anchors(sub)


# ═══════════════════════════════════════════════════════════════════════
#  Layout classification — single vs double column
# ═══════════════════════════════════════════════════════════════════════

_WIDE_TABLE_MIN_COLS = 7         # >= 7 columns → table*
_WIDE_EQ_MIN_CHARS = 15          # <= 15 chars → inline $...$ instead of \begin{equation}

_ARCHITECTURE_KEYWORDS = [
    "architecture", "pipeline", "framework", "overview", "network structure",
    "system overview", "schematic", "block diagram",
]


def _classify_layout(manuscript: Manuscript, profile: JournalProfile) -> None:
    """Classify each figure and table as single or double-column.

    Heuristics:
      Tables: num_cols >= 7 → double-column (table*)
      Figures: caption contains architecture/pipeline keywords → double-column (figure*)
      Equations: latex length <= 15 chars → inline ($...$) (marked in Equation model)
    """
    # Classify tables
    for tbl in manuscript.tables:
        if tbl.num_cols >= _WIDE_TABLE_MIN_COLS:
            tbl.column_span = 2
            print(f"  📐 Table {tbl.id}: {tbl.num_cols} columns → double-column")

    # Classify figures
    for fig in manuscript.figures:
        caption_lower = (fig.caption or "").lower()
        label_lower = (fig.label or "").lower()
        text_to_check = caption_lower + " " + label_lower
        if any(kw in text_to_check for kw in _ARCHITECTURE_KEYWORDS):
            fig.column_span = 2
            kw_found = [kw for kw in _ARCHITECTURE_KEYWORDS if kw in text_to_check][0]
            print(f"  📐 Figure {fig.id}: '{kw_found}' in caption → double-column")

    # ── Equation classification: semantic rules ──────────────────
    # Rules (in order, first match wins):
    #   1. Pure number (1)(2) → is_equation_number=True
    #   2. Inline pattern match → inline=True
    #   3. Display keyword match → inline=False
    #   4. Has assignment = → inline=False
    #   5. Fallback: length <= 20 chars → inline
    #                  otherwise → display

    _INLINE_PATTERNS = [
        re.compile(r"^\\[a-zA-Z]+(_\{[^}]{1,6}\})?'?$"),          # \\theta_i  \\mu  \\sigma_i
        re.compile(r"^\\[a-zA-Z]+'?$"),                             # \\mu  \\omega  \\lambda
        re.compile(r"^[A-Za-z]\\{?[\^_][^}]{0,6}\}?'?$"),        # Y_i  S^2  W_i'
        re.compile(r"^[A-Za-z]'$"),                                   # S'  R'
        re.compile(r"^\\d+(\\.\\d+)?$"),                          # 0  1  3.14
        re.compile(r"^[A-Za-z]$"),                                    # N  k  p
        re.compile(r"^\\[a-zA-Z]+\\{[^}]{1,8}\}$"),                # \\hat{S}  \\bar{x}
    ]

    _DISPLAY_KEYWORDS = [
        r"\\frac", r"\\sum", r"\\int", r"\\prod",
        r"\\begin", r"\\matrix",
        r"\\left", r"\\right",
        r"\\sqrt\\.{4,}",
        r"\\over", r"\\underbrace", r"\\overbrace",
        r"\\lim", r"\\inf", r"\\sup",
    ]

    for eq in manuscript.equations:
        if not eq.latex:
            eq.inline = True
            continue

        latex = eq.latex.strip().strip("$").strip()

        # Rule 1: Pure number (1) (2) (12) → equation_number
        if re.fullmatch(r"\(\d+\)", latex):
            eq.is_equation_number = True
            eq.inline = True
            print(f"  📐 Equation {eq.id}: '{latex}' → equation_number")
            continue

        # Rule 2: Inline pattern match
        if any(p.fullmatch(latex) for p in _INLINE_PATTERNS):
            eq.inline = True
            continue

        # Rule 3: Display keyword match
        if any(re.search(kw, latex) for kw in _DISPLAY_KEYWORDS):
            eq.inline = False
            continue

        # Rule 4: Has assignment =
        if re.search(r"[A-Za-z_}\\]\\s*=\\s*\\S", latex):
            eq.inline = False
            continue

        # Rule 5: Fallback by length
        FALLBACK_INLINE_MAX_CHARS = 20
        eq.inline = len(latex) <= FALLBACK_INLINE_MAX_CHARS


# ═══════════════════════════════════════════════════════════════════════
#  Equation number binding — attach (1)(2)(3) to parent display equation
# ═══════════════════════════════════════════════════════════════════════

def _bind_equation_numbers(manuscript) -> None:
    """Bind (1)(2)(3) numbered formulas to their preceding display equation.

    In Word documents, equation numbers like "(1)" are often individual
    MathType objects. This function finds such formulas and:
      1. Attaches the number text to the nearest preceding display equation
      2. Marks the number formula as skip_render=True (don't output separately)

    The display equation's number field is used by the renderer to output
    \\label{eq:N} with the correct number reference.
    """
    last_display_eq = None

    for eq in manuscript.equations:
        if eq.is_equation_number:
            if last_display_eq is not None:
                last_display_eq.number = eq.latex.strip().strip("$").strip()
                eq.skip_render = True
                print(f"  📐 Bound {eq.id} '{eq.latex}' → {last_display_eq.id}")
            else:
                # No preceding display eq — keep as inline
                eq.inline = True
                print(f"  ⚠️  Equation number {eq.id} '{eq.latex}' has no parent display eq")
        elif not eq.inline:
            last_display_eq = eq

