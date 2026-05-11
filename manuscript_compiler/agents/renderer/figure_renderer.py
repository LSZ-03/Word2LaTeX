"""Renders Figure AST nodes to LaTeX \\figure environments.

PURE RENDERER — no formatting logic.
Caption position determined by profile.caption_policy.figure_position.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from manuscript_compiler.ast.figure import Figure
from manuscript_compiler.journal_profiles import JournalProfile


def _fig_caption_position(profile: JournalProfile) -> str:
    """Get figure caption position from profile, defaulting to 'below'."""
    if profile.caption_policy:
        return profile.caption_policy.figure_position
    return "below"


def render_figures(
    figures: List[Figure],
    profile: JournalProfile,
    image_base_dir: Optional[str] = None,
) -> List[str]:
    """Render all Figure AST nodes to LaTeX figure environments."""
    lines: List[str] = []
    for fig in figures:
        rendered = render_single_figure(fig, profile, image_base_dir)
        if rendered:
            lines.extend(rendered)
            lines.append("")
    return lines


def render_single_figure(
    fig: Figure,
    profile: JournalProfile,
    image_base_dir: Optional[str] = None,
) -> List[str]:
    """Render a single Figure to LaTeX.

    Reads pre-computed fields set by constraint layer:
      - fig.caption    (already cleaned — no "Fig." prefix)
      - fig.label      (already canonical — "fig:N" format)

    Caption position determined by profile.caption_policy.figure_position.
    """
    if not fig.image_path:
        return []

    lines: List[str] = []
    env = "figure*" if fig.column_span == 2 else "figure"
    lines.append(r"\begin{" + env + "}[" + profile.figure_placement + "]")
    lines.append(r"\centering")

    # Build caption + label block
    cap_text = fig.caption or ""
    cap_text = _escape_fig_text(cap_text)
    caption_line = r"\caption{" + cap_text + "}" if cap_text else r"\caption{}"
    label = fig.label or f"fig:{fig.id}"
    label_line = r"\label{" + label + "}"

    # Image path — make relative if possible
    img_path = fig.image_path
    if image_base_dir:
        try:
            img_path = Path(img_path).relative_to(image_base_dir).as_posix()
        except ValueError:
            img_path = Path(img_path).name
    else:
        img_path = Path(img_path).name

    image_line = r"\includegraphics[width=" + profile.figure_max_width + "]{" + img_path + "}"

    # Place caption according to journal policy
    cap_pos = _fig_caption_position(profile)
    if cap_pos == "above":
        # Caption above figure (rare)
        lines.append(caption_line)
        lines.append(label_line)
        lines.append(image_line)
    else:
        # Caption below figure (IEEE/Elsevier default)
        lines.append(image_line)
        lines.append(caption_line)
        lines.append(label_line)

    lines.append(r"\end{" + env + "}")
    return lines


def _escape_fig_text(text: str) -> str:
    """Minimal LaTeX escaping for figure captions."""
    return text.replace("&", r"\&").replace("%", r"\#").replace("_", r"\_")
