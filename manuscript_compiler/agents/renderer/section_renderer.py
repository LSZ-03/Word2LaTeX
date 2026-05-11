"""Renders sections, paragraphs, and text formatting to LaTeX."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional

from manuscript_compiler.ast.section import (
    Section,
    Paragraph,
    TextRun,
    ListBlock,
    ListItem,
    SemanticRole,
)
from manuscript_compiler.ast.equation import Equation
from manuscript_compiler.ast.figure import Figure
from manuscript_compiler.ast.table import Table
from manuscript_compiler.journal_profiles import JournalProfile
from manuscript_compiler.agents.renderer.equation_renderer import render_single_equation
from manuscript_compiler.agents.renderer.figure_renderer import render_figures
from manuscript_compiler.agents.renderer.table_renderer import render_tables

# ── Equation placeholder ──────────────────────────────────────────
EQ_PLACEHOLDER = "\x00EQ\x00"


def render_sections(
    sections: List[Section],
    profile: JournalProfile,
    equations: Optional[List[Equation]] = None,
    figures: Optional[List[Figure]] = None,
    tables: Optional[List[Table]] = None,
    bibliography: Optional[List] = None,
    image_base_dir: Optional[str] = None,
) -> List[str]:
    """Render sections with streaming figure/table placement.

    Figures and tables are NOT collected at the end. Instead, the constraint
    layer anchors them to their first reference paragraph. The renderer
    injects them immediately after that paragraph (streaming).
    """
    lines: List[str] = []

    # Build lookup maps by ID
    eq_map: dict[str, Equation] = {}
    if equations:
        for eq in equations:
            eq_map[eq.id] = eq

    fig_map: dict[str, Figure] = {}
    if figures:
        for fig in figures:
            fig_map[fig.id] = fig

    tab_map: dict[str, Table] = {}
    if tables:
        for tbl in tables:
            tab_map[tbl.id] = tbl

    # Track which sections are already covered by render_title_block
    already_rendered_titles: set[str] = set()

    # First pass: scan for Abstract/Keywords under __preamble__
    for section in sections:
        if section.title == "__preamble__":
            for sub in section.subsections:
                tl = sub.title.strip().lower()
                if tl in ("abstract", "keywords") or tl.startswith("abstract:") or tl.startswith("keywords:"):
                    already_rendered_titles.add(sub.title.strip())
                if tl.startswith("abstract"):
                    already_rendered_titles.add(sub.title.strip())

    # Second pass: render everything (streaming — figs/tabs injected inline)
    for section in sections:
        lines.extend(_render_section_inner(section, profile, 0, already_rendered_titles,
                                           eq_map, fig_map, tab_map, image_base_dir))

    # Append bibliography
    if bibliography:
        from manuscript_compiler.agents.renderer.bib_renderer import render_bibliography as _render_bib
        lines.append("")
        lines.extend(_render_bib(bibliography, profile))
        lines.append("")

    return lines


def _render_section_inner(
    section: Section,
    profile: JournalProfile,
    depth: int,
    skip_titles: set[str],
    eq_map: dict[str, Equation],
    fig_map: dict[str, Figure],
    tab_map: dict[str, Table],
    image_base_dir: Optional[str] = None,
) -> List[str]:
    """Render a section with streaming figure/table/equation injection.

    Figures and tables are placed immediately after the paragraph that
    first references them (determined by constraint layer anchoring),
    NOT collected at the end.
    """
    from manuscript_compiler.agents.renderer.figure_renderer import render_single_figure
    from manuscript_compiler.agents.renderer.table_renderer import render_single_table

    lines: List[str] = []
    raw_title = section.title
    title = _escape_latex(raw_title)

    # Skip preamble section
    if raw_title == "__preamble__":
        for sub in section.subsections:
            sub_title = sub.title.strip()
            if sub_title in skip_titles:
                continue
            lines.extend(_render_section_inner(sub, profile, 0, skip_titles, eq_map,
                                               fig_map, tab_map, image_base_dir))
        return lines

    # Skip if already rendered by title block
    if raw_title in skip_titles:
        for sub in section.subsections:
            lines.extend(_render_section_inner(sub, profile, depth + 1, skip_titles, eq_map,
                                               fig_map, tab_map, image_base_dir))
        return lines

    # Render section heading
    if title:
        section_cmd = _section_command(section.level, profile)
        lines.append(f"\\{section_cmd}{{ {title} }}")
        lines.append("")

    # Render paragraphs with inline figures/tables/equation expansion
    for para in section.paragraphs:
        rendered = render_paragraph(para, eq_map, profile)
        if rendered:
            # Split on newlines so display equations get proper separate lines
            for line in rendered.split("\n"):
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
            lines.append("")

        # Streaming figures
        for fig_id in para.inline_figure_ids:
            if fig_id in fig_map:
                fig_lines = render_single_figure(fig_map[fig_id], profile, image_base_dir)
                if fig_lines:
                    lines.extend(fig_lines)
                    lines.append("")

        # Streaming tables
        for tab_id in para.inline_table_ids:
            if tab_id in tab_map:
                tab_lines = render_single_table(tab_map[tab_id], profile)
                if tab_lines:
                    lines.extend(tab_lines)
                    lines.append("")

    # Render lists
    for lst in section.lists:
        lines.extend(render_list(lst))
        lines.append("")

    # Render subsections recursively
    for sub in section.subsections:
        sub_title = sub.title.strip()
        if sub_title in skip_titles:
            continue
        lines.extend(_render_section_inner(sub, profile, section.level, skip_titles, eq_map,
                                           fig_map, tab_map, image_base_dir))

    return lines


def render_section(section: Section, profile: JournalProfile, level: int = 0) -> List[str]:
    """[DEPRECATED] Use render_sections() instead."""
    return _render_section_inner(section, profile, level, set(), {}, {}, {}, None)


def _section_command(level: int, profile: JournalProfile) -> str:
    """Map heading level to LaTeX sectioning command."""
    if profile.section_numbering == "none":
        cmds = {1: "section*", 2: "subsection*", 3: "subsubsection*"}
    else:
        cmds = {1: "section", 2: "subsection", 3: "subsubsection"}
    return cmds.get(level, "paragraph")






def render_paragraph(para: Paragraph, eq_map: dict = None, profile: JournalProfile = None) -> str:
    """Render a single Paragraph AST node to LaTeX text.

    If the paragraph has EQ placeholders (\\x00EQ\\x00), they are expanded
    into actual LaTeX equations using eq_map and render_single_equation.
    Display equations are placed on their own line.
    """
    if not para.plain_text and not para.runs:
        return ""

    eq_map = eq_map or {}
    from manuscript_compiler.agents.renderer.equation_renderer import render_single_equation as _render_eq

    def _escape_with_cite_protect(text: str) -> str:
        """Escape LaTeX chars but protect \\cite{} and \\ref{} commands from escaping."""
        placeholders = {}
        def _save(m):
            key = f"\x00PH{len(placeholders)}\x00"
            placeholders[key] = m.group(0)
            return key
        text = re.sub(r"\\cite\{[^}]*\}", _save, text)
        text = re.sub(r"~?\s*\\ref\{[^}]*\}", _save, text)
        text = _escape_latex(text)
        for key, val in placeholders.items():
            text = text.replace(key, val)
        return text

    # Get the raw LaTeX text
    if para.runs:
        parts = []
        for run in para.runs:
            text = _escape_with_cite_protect(run.text)
            if run.bold:
                text = f"\\textbf{{{text}}}"
            if run.italic:
                text = f"\\textit{{{text}}}"
            if run.underline:
                text = f"\\underline{{{text}}}"
            if run.superscript:
                text = f"\\textsuperscript{{{text}}}"
            if run.subscript:
                text = f"\\textsubscript{{{text}}}"
            parts.append(text)
        text = "".join(parts)
        # If plain_text has EQ placeholders (from _write_para_texts),
        # append them to runs text too since runs don't have them
        if EQ_PLACEHOLDER in (para.plain_text or ""):
            n_eq = para.plain_text.count(EQ_PLACEHOLDER)
            text += " " + " ".join([EQ_PLACEHOLDER] * n_eq)
    else:
        text = _escape_with_cite_protect(para.plain_text)

    # Expand EQ placeholders into actual equation LaTeX
    if EQ_PLACEHOLDER in text and para.inline_equation_ids:
        parts = text.split(EQ_PLACEHOLDER)
        segments: list[str] = []
        for i, part in enumerate(parts):
            segments.append(part)
            if i < len(para.inline_equation_ids):
                eq_id = para.inline_equation_ids[i]
                eq = eq_map.get(eq_id)
                if eq and not eq.skip_render:
                    eq_lines = _render_eq(eq, profile)
                    if eq_lines:
                        # Inline: merge into same text line
                        if len(eq_lines) == 1 and eq_lines[0].startswith("$") and eq_lines[0].endswith("$"):
                            segments[-1] += f" {eq_lines[0]}"
                        else:
                            # Display: place on its own line
                            segments.append("\n")
                            segments.extend(eq_lines)
                            segments.append("\n")
        text = "".join(segments)

    return text


def render_list(lst: ListBlock) -> List[str]:
    """Render a ListBlock (ordered or unordered) to LaTeX."""
    lines: List[str] = []
    env = "enumerate" if lst.ordered else "itemize"
    lines.append(f"\\begin{{{env}}}")
    for item in lst.items:
        lines.extend(_render_list_item(item, 0))
    lines.append(f"\\end{{{env}}}")
    return lines


def _render_list_item(item: ListItem, depth: int) -> List[str]:
    """Render a single list item, handling nesting."""
    lines: List[str] = []
    indent = "  " * depth
    lines.append(f"{indent}\\item {_escape_latex(item.text)}")
    if item.children:
        for child in item.children:
            lines.extend(_render_list_item(child, depth + 1))
    return lines


def render_abstract(text: str) -> List[str]:
    """Render abstract section."""
    if not text:
        return []
    return [
        r"\begin{abstract}",
        _escape_latex(text),
        r"\end{abstract}",
        "",
    ]


def render_keywords(keywords: List[str]) -> List[str]:
    """Render keywords as \\IEEEkeywords or inline."""
    if not keywords:
        return []
    kw_text = ", ".join(keywords)
    return [
        r"\begin{IEEEkeywords}",
        _escape_latex(kw_text),
        r"\end{IEEEkeywords}",
        "",
    ]


def render_title_block(title: str, abstract: str, keywords: List[str]) -> List[str]:
    """Render title, abstract, and keywords as LaTeX preamble."""
    lines: List[str] = []
    if title:
        lines.append(r"\title{" + _escape_latex(title) + "}")
        lines.append(r"\author{}")  # placeholder, could extract from AST
        lines.append(r"\maketitle")
        lines.append("")
    lines.extend(render_abstract(abstract))
    lines.extend(render_keywords(keywords))
    return lines


# ── LaTeX escaping ─────────────────────────────────────────────────────

_SPECIAL_CHARS = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def _escape_latex(text: str) -> str:
    """Escape special LaTeX characters in text."""
    result = []
    for ch in text:
        if ch in _SPECIAL_CHARS:
            result.append(_SPECIAL_CHARS[ch])
        elif ord(ch) < 128:
            result.append(ch)
        else:
            # Unicode character — keep as-is (xelatex/lualatex can handle)
            result.append(ch)
    return "".join(result)
