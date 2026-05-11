"""Renders Table AST nodes to LaTeX \\table environments.

PURE RENDERER — no formatting logic or citation conversion.
Caption position determined by profile.caption_policy.table_position.
"""
from __future__ import annotations

from typing import List

from manuscript_compiler.ast.table import Table
from manuscript_compiler.journal_profiles import JournalProfile


def _tab_caption_position(profile: JournalProfile) -> str:
    """Get table caption position from profile, defaulting to 'above'."""
    if profile.caption_policy:
        return profile.caption_policy.table_position
    return "above"


def render_tables(tables: List[Table], profile: JournalProfile) -> List[str]:
    """Render all Table AST nodes to LaTeX."""
    lines: List[str] = []
    for tbl in tables:
        rendered = render_single_table(tbl, profile)
        if rendered:
            lines.extend(rendered)
            lines.append("")
    return lines


def render_single_table(tbl: Table, profile: JournalProfile) -> List[str]:
    """Render a single Table to LaTeX tabular environment.

    Reads pre-computed fields set by constraint layer:
      - tbl.caption    (already cleaned — no "Table" prefix)
      - tbl.label      (already canonical — "tab:N" format)
      - cell.text      (citations + refs already converted)

    Caption position determined by profile.caption_policy.table_position.
    """
    if tbl.num_rows == 0 or tbl.num_cols == 0:
        return []

    lines: List[str] = []
    env = "table*" if tbl.column_span == 2 else "table"
    lines.append(r"\begin{" + env + "}[" + profile.table_placement + "]")
    lines.append(r"\centering")

    # Build caption + label block
    cap = tbl.caption or ""
    cap = _escape_table_text(cap)
    caption_line = r"\caption{" + cap + "}" if cap else r"\caption{}"
    label = tbl.label or f"tab:{tbl.id}"
    label_line = r"\label{" + label + "}"

    # Build tabular block
    col_spec = " ".join([profile.table_default_align] * tbl.num_cols)
    tabular_lines: List[str] = []
    tabular_lines.append(r"\begin{tabular}{" + col_spec + "}")
    tabular_lines.append(r"\toprule")

    for row_idx, row in enumerate(tbl.rows):
        cell_texts = []
        for cell in row.cells:
            text = _escape_table_text(cell.text)
            if cell.is_header:
                text = r"\textbf{" + text + "}"
            cell_texts.append(text)
        tabular_lines.append(" & ".join(cell_texts) + r" \\")
        if row_idx == 0 and tbl.has_header_row:
            tabular_lines.append(r"\midrule")

    tabular_lines.append(r"\bottomrule")
    tabular_lines.append(r"\end{tabular}")

    # Place caption according to journal policy
    cap_pos = _tab_caption_position(profile)
    if cap_pos == "below":
        lines.extend(tabular_lines)
        lines.append(caption_line)
        lines.append(label_line)
    else:
        # Caption above table (IEEE/Springer style — default)
        lines.append(caption_line)
        lines.append(label_line)
        lines.extend(tabular_lines)

    # Attached notes (footnotes / abbreviations following the table)
    if tbl.notes:
        lines.append(r"\vspace{2pt}")
        for note in tbl.notes:
            note_text = _escape_table_text(note)
            lines.append(r"\footnotesize{" + note_text + "}")

    lines.append(r"\end{" + env + "}")
    return lines


def _escape_table_text(text: str) -> str:
    """Escape LaTeX special chars inside table cells.

    Constraints (citations, fig/table refs) are already applied by
    the constraint layer. We still need to protect any \\cite/\\ref
    commands that may be present from escaping.
    """
    import re as _re
    placeholders = {}
    def _save(m):
        k = f"\x00CT{len(placeholders)}\x00"
        placeholders[k] = m.group(0)
        return k
    text = _re.sub(r"\\cite\{[^}]*\}", _save, text)
    text = _re.sub(r"~?\s*\\ref\{[^}]*\}", _save, text)

    result = (text.replace("&", r"\&")
                  .replace("%", r"\%")
                  .replace("$", r"\$")
                  .replace("#", r"\#")
                  .replace("_", r"\_")
                  .replace("{", r"\{")
                  .replace("}", r"\}")
                  .replace("~", r"\textasciitilde{}")
                  .replace("^", r"\textasciicircum{}"))

    for k, v in placeholders.items():
        result = result.replace(k, v)
    return result
