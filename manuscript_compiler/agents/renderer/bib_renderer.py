"""Renders bibliography to LaTeX thebibliography environment."""

from __future__ import annotations

import re
from typing import List

from manuscript_compiler.ast.citation import Citation
from manuscript_compiler.journal_profiles import JournalProfile


def render_bibliography(
    bibliography: List[Citation],
    profile: JournalProfile,
) -> List[str]:
    """Render bibliography to LaTeX.

    For MVP: use thebibliography environment (no BibTeX dependency).
    """
    if not bibliography:
        return []

    lines: List[str] = []
    lines.append(r"\begin{thebibliography}{99}")
    lines.append("")

    for i, ref in enumerate(bibliography):
        lines.extend(render_single_citation(ref, i + 1, profile))

    lines.append(r"\end{thebibliography}")
    return lines


def render_single_citation(ref: Citation, index: int, profile: JournalProfile) -> List[str]:
    """Render a single citation entry to \\bibitem format."""
    lines: List[str] = []
    cite_key = ref.key or f"ref_{index}"
    lines.append(f"\\bibitem{{{cite_key}}}")

    # Build the reference text from available fields
    parts = []
    if ref.authors:
        parts.append(ref.authors)
    if ref.title:
        # Strip leading number like "1.\t" or "1. "
        clean_title = re.sub(r"^\d+\.\s*", "", ref.title).strip()
        clean_title = re.sub(r"^\t+", "", clean_title).strip()
        parts.append(f"\\textit{{{clean_title}}}")
    if ref.journal:
        parts.append(ref.journal)
    if ref.booktitle:
        parts.append(f"\\textit{{{ref.booktitle}}}")
    if ref.volume:
        vol = ref.volume
        if ref.number:
            vol += f"({ref.number})"
        parts.append(vol)
    if ref.pages:
        parts.append(f"pp.~{ref.pages}")
    if ref.publisher:
        parts.append(ref.publisher)
    if ref.year:
        parts.append(ref.year)
    if ref.doi:
        parts.append(f"DOI: {ref.doi}")
    if ref.url:
        parts.append(ref.url)

    if parts:
        lines.append(". ".join(parts) + ".")
    else:
        # Fallback: use plain text from title field, strip leading number
        text = ref.title or ""
        text = re.sub(r"^\d+\.\s*", "", text).strip()  # Strip "1. "
        text = re.sub(r"^\t+", "", text).strip()        # Strip tabs
        lines.append(text)

    lines.append("")
    return lines
