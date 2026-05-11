"""Manuscript Compiler — pipeline orchestrator.

Coordinates the full Word → AST → LaTeX pipeline.
"""

from __future__ import annotations
import shutil
import json as _json
from pathlib import Path
from typing import Optional
from PIL import Image

from manuscript_compiler.ast.manuscript import Manuscript
from manuscript_compiler.agents.docx_parser.agent import run as run_parser
from manuscript_compiler.agents.renderer.agent import run as run_renderer
from manuscript_compiler.constraints.engine import apply as apply_constraints


def run_pipeline(
    docx_path: str | Path,
    output_dir: Optional[str | Path] = None,
    journal: Optional[str] = None,
) -> Manuscript:
    """Execute the full Word → AST → LaTeX pipeline.

    Args:
        docx_path: Path to the input .docx file.
        output_dir: Optional output directory. Defaults to docx filename + "_output".
        journal: Optional target journal name (e.g. "ieee", "tgrs").

    Returns:
        The final Manuscript AST (non-None fields indicate what was produced).
    """
    docx_path = Path(docx_path)
    if output_dir is None:
        output_dir = docx_path.parent / f"{docx_path.stem}_output"
    output_dir = Path(output_dir)

    print(f"📄 Input:  {docx_path}")
    print(f"📁 Output: {output_dir}")

    # ── Stage 1: Parse docx → AST ─────────────────────────────────────
    print("\n🔍 Stage 1/2: Parsing .docx → AST ...")
    manuscript = run_parser(
        docx_path=docx_path,
        output_dir=output_dir / "figures",
        journal_target=journal,
    )
    _print_summary(manuscript)

    # ── Stage 2: Inject formula LaTeX + convert TIFF to PNG ────────────
    _inject_formula_latex(manuscript)
    _convert_tiff_to_png(output_dir / "figures", manuscript)

    # ── Stage 2b: Apply journal constraints ───────────────────────────
    from manuscript_compiler.journal_profiles.registry import ProfileRegistry
    _profile = ProfileRegistry().get(journal or "tgrs")
    if _profile:
        print(f"  📐 Applying journal constraints: {_profile.display_name} ({_profile.status})")
        apply_constraints(manuscript, _profile)
    else:
        print(f"  ⚠️  No profile found for '{journal}', skipping constraint layer")

    # ── Stage 3: Render AST → LaTeX ──────────────────────────────────
    print(f"\n🎨 Stage 3/3: Rendering AST → LaTeX ...")

    manuscript = run_renderer(
        manuscript=manuscript,
        output_dir=output_dir,
        journal=journal,
    )

    print(f"\n✅ Pipeline complete. Run ID: {manuscript.run_id}")
    return manuscript


def _inject_formula_latex(manuscript: Manuscript) -> None:
    """Inject Doubao-recognized LaTeX into equation AST nodes.

    Matches by image filename stored in equation_extractor.
    """
    import json as _json
    image_map_path = Path("/tmp/formula_image_map.json")
    if not image_map_path.exists():
        return
    try:
        image_map = _json.loads(image_map_path.read_text())
    except Exception:
        return
    imported = 0
    for eq in manuscript.equations:
        if eq.image_path:
            fname = Path(eq.image_path).stem  # e.g. "image1"
            if fname in image_map and image_map[fname]:
                eq.latex = image_map[fname]
                eq.confidence = 0.85
                imported += 1
    if imported > 0:
        print(f"  ➗ Formula LaTeX injected: {imported}/{len(manuscript.equations)}")


def _convert_tiff_to_png(fig_dir: Path, manuscript: Optional[Manuscript] = None) -> None:
    """Convert TIFF figures to PNG for pdflatex compatibility."""
    if not fig_dir.exists():
        return
    converted = 0
    seen_pngs = set()
    for tiff_path in list(fig_dir.glob("*.tif*")):
        try:
            img = Image.open(tiff_path)
            png_path = tiff_path.with_suffix(".png")
            if not png_path.exists() or tiff_path.stat().st_mtime > png_path.stat().st_mtime:
                img.save(png_path, "PNG")
            seen_pngs.add(png_path.name)
            converted += 1
            tiff_path.unlink(missing_ok=True)
        except Exception as e:
            print(f"  ⚠️  TIFF→PNG failed for {tiff_path.name}: {e}")
    if converted > 0:
        print(f"  🖼️  TIFF→PNG converted: {converted} images")
    # Update figure paths in manuscript AST
    if manuscript:
        for fig in manuscript.figures:
            if fig.image_path:
                p = Path(fig.image_path)
                if p.suffix.lower() in (".tif", ".tiff"):
                    png_path = p.with_suffix(".png")
                    if png_path.name in seen_pngs:
                        fig.image_path = str(png_path)


def _print_summary(m: Manuscript) -> None:
    """Print a human-readable summary of the parsed manuscript."""
    print(f"\n📊 Summary:")
    print(f"   Title:    {m.metadata.title or '(not detected)'}")
    print(f"   Sections: {_count_sections(m.sections)} ({len(m.sections)} top-level)")
    print(f"   Figures:  {len(m.figures)}")
    print(f"   Tables:   {len(m.tables)}")
    print(f"   Equations: {len(m.equations)}")
    print(f"   References: {len(m.bibliography)}")
    if m.warnings:
        print(f"   ⚠️  Warnings: {len(m.warnings)}")
        for w in m.warnings[:3]:
            print(f"      - [{w.severity}] {w.message[:80]}")


def _count_sections(sections) -> int:
    count = len(sections)
    for s in sections:
        count += _count_sections(s.subsections)
    return count
