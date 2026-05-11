"""Image extraction from .docx files.

The .docx format is a ZIP archive. Images are stored under word/media/.
This module extracts them to a designated output directory and returns
Figure AST nodes with paths.
"""

from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path
from typing import List, Optional
from xml.etree import ElementTree

from manuscript_compiler.ast.figure import Figure

# XML namespaces used in docx
NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
NS_PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"

_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_DRAWING_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
_PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"

# Global cache for figure captions (lazy, scanned once from docx)
_fig_caption_cache: List[str] = []
_fig_caption_idx: int = 0


def _reset_caption_cache():
    """Reset the global caption cache (for testing / multiple calls)."""
    global _fig_caption_cache, _fig_caption_idx
    _fig_caption_cache = []
    _fig_caption_idx = 0


def extract_images(
    docx_path: str | Path,
    output_dir: str | Path,
) -> List[Figure]:
    """Extract all embedded images from the .docx file.

    Returns:
        List of Figure AST nodes with image_path and caption set.
    """
    docx_path = Path(docx_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Reset caption cache for fresh extraction
    _reset_caption_cache()

    # Step 1: Build the relationship map from word/_rels/document.xml.rels
    rels = _build_relationship_map(docx_path)

    # Step 2: Parse document.xml to find drawing elements and map to rels
    figures: List[Figure] = []
    figure_counter = 0

    with zipfile.ZipFile(docx_path, "r") as z:
        doc_xml = z.read("word/document.xml")
        root = ElementTree.fromstring(doc_xml)

        # Pre-scan figure captions before extracting images
        figure_captions = _scan_figure_captions(root)

        # Find all <w:drawing> elements
        for drawing in root.iter(f"{{{NS_W}}}drawing"):
            # Find the blip (image reference)
            blip = drawing.find(f".//{{{NS_A}}}blip")
            if blip is None:
                continue

            embed_id = blip.get(f"{{{NS_R}}}embed") or blip.get(f"{{{NS_R}}}link")
            if embed_id is None or embed_id not in rels:
                continue

            image_target = rels[embed_id]  # e.g. "media/image1.png"
            image_path_in_zip = f"word/{image_target}"

            try:
                image_data = z.read(image_path_in_zip)
            except KeyError:
                continue

            # Determine extension
            ext = Path(image_target).suffix.lower()
            figure_counter += 1
            figure_id = f"fig_{figure_counter}"
            out_name = f"{figure_id}{ext}"
            out_path = output_dir / out_name

            out_path.write_bytes(image_data)

            # Get caption from pre-scanned list, matched by order
            caption = figure_captions[figure_counter - 1] if figure_counter - 1 < len(figure_captions) else ""

            figures.append(Figure(
                id=figure_id,
                caption=caption,
                label=f"Fig. {figure_counter}",
                image_path=str(out_path),
                image_bytes_size=len(image_data),
                image_format=ext.lstrip("."),
            ))

    return figures


def _build_relationship_map(docx_path: Path) -> dict[str, str]:
    """Parse word/_rels/document.xml.rels to get a {rId: target} map."""
    rels: dict[str, str] = {}
    try:
        with zipfile.ZipFile(docx_path, "r") as z:
            rels_xml = z.read("word/_rels/document.xml.rels")
            root = ElementTree.fromstring(rels_xml)
            for rel_elem in root:
                r_id = rel_elem.get("Id", "")
                target = rel_elem.get("Target", "")
                rels[r_id] = target
    except (KeyError, ElementTree.ParseError):
        pass
    return rels


def _scan_figure_captions(root: ElementTree.Element) -> List[str]:
    """Scan all paragraphs for figure caption patterns.

    Matches paragraphs starting with "Fig. N" or "Figure N"
    and returns them in document order.
    """
    captions: List[str] = []
    for para in root.iter(f"{{{NS_W}}}p"):
        texts = []
        for t in para.iter(f"{{{NS_W}}}t"):
            if t.text:
                texts.append(t.text)
        text = "".join(texts).strip()
        if re.match(r"^(Fig(ure)?\.?\s*\d)", text):
            captions.append(text)
    return captions
