"""Renderer Agent — converts Manuscript AST to LaTeX.

Coordinates:
  1. Journal profile selection + official template file copying
  2. Preamble generation (documentclass, packages)
  3. Section/paragraph rendering
  4. Figure/table/equation rendering
  5. Bibliography rendering
  6. Output file writing

Key design rule:
  - Template files (.cls/.bst/.sty) come from templates/{profile.name}/
    (downloaded from official journal websites).
  - Renderer generates the .tex content ONLY; it does NOT contain
    template-style definitions.
  - Copies all template files to output dir so compilation works
    without system-wide LaTeX package installation.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from manuscript_compiler.ast.manuscript import Manuscript
from manuscript_compiler.journal_profiles import get_profile, JournalProfile
from manuscript_compiler.agents.renderer.section_renderer import (
    render_sections,
)
from manuscript_compiler.agents.renderer.figure_renderer import render_figures
from manuscript_compiler.agents.renderer.table_renderer import render_tables
from manuscript_compiler.agents.renderer.equation_renderer import render_equations
from manuscript_compiler.agents.renderer.bib_renderer import render_bibliography


def run(
    manuscript: Manuscript,
    output_dir: str | Path,
    journal: Optional[str] = None,
    copy_figures: bool = True,
) -> Manuscript:
    """Render the Manuscript AST to a complete LaTeX project.

    Args:
        manuscript: The parsed Manuscript AST.
        output_dir: Where to write the LaTeX output.
        journal: Target journal name (e.g. "tgrs", "ieee", "iclr").
        copy_figures: Whether to copy extracted figures into the output dir.

    Returns:
        The Manuscript AST (updated with pipeline_stage).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Resolve journal profile ──
    journal_name = journal or manuscript.metadata.journal_target or "ieee"
    profile = get_profile(journal_name)
    print(f"  📖 Journal: {profile.display_name}")

    # ── 2. Copy official template files (.cls, .bst, .sty) ──
    _copy_template_files(profile, output_dir)

    # ── 3. Render components → LaTeX lines ──
    tex_lines: list[str] = []

    # Preamble
    tex_lines.extend(_render_preamble(profile))
    tex_lines.append("")

    # Title block (includes abstract + keywords)
    tex_lines.extend(_render_ieee_title_block(manuscript, profile))
    tex_lines.append("")

    # Sections + bibliography + figures/tables (all in order)
    tex_lines.extend(render_sections(
        manuscript.sections,
        profile,
        manuscript.equations,
        manuscript.figures,
        manuscript.tables,
        manuscript.bibliography,
        image_base_dir=str(output_dir / "figures") if copy_figures else None,
    ))
    tex_lines.append("")

    # End
    tex_lines.append(r"\end{document}")
    tex_lines.append("")

    # ── 4. Write main.tex ──
    tex_path = output_dir / "main.tex"
    tex_path.write_text("\n".join(tex_lines), encoding="utf-8")
    print(f"  ✅ main.tex: {tex_path}")

    # ── 5. Copy figures (skip if already in output dir) ──
    if copy_figures and manuscript.figures:
        fig_output_dir = output_dir / "figures"
        fig_output_dir.mkdir(exist_ok=True)
        copied = 0
        for fig in manuscript.figures:
            if fig.image_path:
                src = Path(fig.image_path)
                if src.exists():
                    dst = fig_output_dir / src.name
                    if src.resolve() != dst.resolve():
                        shutil.copy2(str(src), str(dst))
                    copied += 1
        print(f"  🖼️  Figures: {copied}/{len(manuscript.figures)} ready")

    # ── Print summary ──
    _print_tex_summary(tex_path, manuscript, profile)
    _list_template_files(profile, output_dir)

    manuscript.pipeline_stage = "rendered"
    return manuscript


# ── Template file management ──────────────────────────────────────────


_TEMPLATE_EXTENSIONS = {".cls", ".bst", ".sty", ".bib", ".def", ".cfg"}


def _copy_template_files(profile: JournalProfile, output_dir: Path) -> None:
    """Copy official template files from templates/{name}/ to output dir.

    This ensures the LaTeX project is self-contained — no dependency on
    system-wide LaTeX package installations.
    """
    template_path = profile.template_path
    if not template_path.exists() or not template_path.is_dir():
        print(f"  ⚠️  No official template directory: {template_path}")
        print(f"     Using generic LaTeX — download the {profile.name} template")
        print(f"     and place it in: {template_path}")
        return

    copied = 0
    for f in template_path.iterdir():
        if f.is_file() and f.suffix in _TEMPLATE_EXTENSIONS:
            dst = output_dir / f.name
            shutil.copy2(str(f), str(dst))
            copied += 1

    if copied > 0:
        print(f"  📦 Template files copied: {copied}")


def _list_template_files(profile: JournalProfile, output_dir: Path) -> None:
    """Show which official template files are in the output dir."""
    found = [f.name for f in output_dir.iterdir()
             if f.is_file() and f.suffix in _TEMPLATE_EXTENSIONS]
    if found:
        print(f"  📁 Output template files: {', '.join(found)}")


# ── IEEEtran Preamble ─────────────────────────────────────────────────


def _render_preamble(profile: JournalProfile) -> list[str]:
    """Render the LaTeX preamble for IEEEtran class."""
    lines: list[str] = []

    # Document class
    opts = ",".join(profile.class_options) if profile.class_options else ""
    if opts:
        lines.append(f"\\documentclass[{opts}]{{{profile.documentclass}}}")
    else:
        lines.append(f"\\documentclass{{{profile.documentclass}}}")
    lines.append("")

    # Packages
    for pkg in profile.packages:
        opt = profile.package_options.get(pkg, "")
        if opt:
            lines.append(f"\\usepackage[{opt}]{{{pkg}}}")
        else:
            lines.append(f"\\usepackage{{{pkg}}}")
    lines.append("")

    # Graphics path
    lines.append(r"\graphicspath{{./figures/}}")
    lines.append("")

    # Extra preamble commands
    for cmd in profile.preamble_extra:
        lines.append(cmd)
    if profile.preamble_extra:
        lines.append("")

    # Begin document
    lines.append(r"\begin{document}")
    lines.append("")

    return lines


def _render_ieee_title_block(manuscript: Manuscript, profile: JournalProfile) -> list[str]:
    """Render IEEEtran-format title, abstract, keywords, and journal header."""
    lines: list[str] = []

    # ── \title ──
    title = manuscript.metadata.title or "Untitled"
    lines.append(r"\title{" + _escape_latex(title) + "}")
    lines.append("")

    # ── \author (placeholder — manuscript_compiler doesn't parse authors yet) ──
    lines.append(r"\author{\IEEEauthorblockN{Author Names}}")
    lines.append(r"\IEEEauthorblockA{Affiliation, City, Country}")
    lines.append("")

    # ── \markboth (journal header for running heads) ──
    header = profile.journal_header or profile.display_name
    short_title = title[:50] + ("..." if len(title) > 50 else "")
    lines.append(r"\markboth{" + _escape_latex(header) + "}%" + "{")
    lines.append(r"\MakeLowercase{\textit{" + _escape_latex(short_title) + "}}}")
    lines.append("")

    # ── \maketitle ──
    lines.append(r"\maketitle")
    lines.append("")

    # ── Abstract ──
    abstract_text = manuscript.metadata.abstract
    if abstract_text:
        lines.append(r"\begin{abstract}")
        lines.append(_escape_latex(abstract_text))
        lines.append(r"\end{abstract}")
        lines.append("")

    # ── Keywords (IEEEtran uses \begin{IEEEkeywords}) ──
    if manuscript.metadata.keywords:
        kw_text = ", ".join(manuscript.metadata.keywords)
        lines.append(r"\begin{IEEEkeywords}")
        lines.append(_escape_latex(kw_text))
        lines.append(r"\end{IEEEkeywords}")
        lines.append("")

    # ── Peer review title (for peer review drafts) ──
    lines.append(r"\IEEEpeerreviewmaketitle")
    lines.append("")

    return lines


# ── Utilities ─────────────────────────────────────────────────────────


def _escape_latex(text: str) -> str:
    """Escape special LaTeX characters."""
    replacements = {
        "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
        "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
    }
    result = []
    for ch in text:
        if ch in replacements:
            result.append(replacements[ch])
        elif ord(ch) < 128:
            result.append(ch)
        else:
            result.append(ch)
    return "".join(result)


def _print_tex_summary(tex_path: Path, manuscript: Manuscript, profile: JournalProfile) -> None:
    """Print a summary of the rendered LaTeX output."""
    tex_size_kb = tex_path.stat().st_size / 1024
    line_count = tex_path.read_text(encoding="utf-8").count("\n")
    print(f"\n  📄 LaTeX stats: {line_count} lines, {tex_size_kb:.1f} KB")
    print(f"     Class: {profile.documentclass}")
    print(f"     {len(manuscript.sections)} sections, {len(manuscript.figures)} figures")
    print(f"     {len(manuscript.tables)} tables, {len(manuscript.bibliography)} refs")
