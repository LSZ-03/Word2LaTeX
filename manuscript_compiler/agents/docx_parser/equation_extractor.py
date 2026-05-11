"""Equation extraction — handles MathType/WMF formulas from VML imagedata.

MathType equations in .docx are stored as:
  1. OLE objects (.bin) in word/embeddings/ — raw MathType data
  2. WMF preview images in word/media/ — rendered formula images
  3. VML <v:imagedata> tags in document.xml — position references

Core fix — Precise inline placement:
  Old: formulas extracted separately, stacked at paragraph end
  New: walk runs in order, embed \\x00EQ\\x00 placeholders in paragraph text
       Renderer expands placeholders at correct positions

Returns: (equations, para_texts)
  equations:  List[Equation] — formula AST nodes
  para_texts: {paragraph_index: str} — paragraph text with \\x00EQ\\x00 markers
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

from lxml import etree

from manuscript_compiler.ast.equation import Equation

# ── Namespaces ──────────────────────────────────────────────────
NS_W   = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_V   = "urn:schemas-microsoft-com:vml"
NS_R   = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

EQ_PLACEHOLDER = "\x00EQ\x00"

# lxml full tag names
TAG_W_P         = f"{{{NS_W}}}p"
TAG_W_R         = f"{{{NS_W}}}r"
TAG_W_T         = f"{{{NS_W}}}t"
TAG_W_TAB       = f"{{{NS_W}}}tab"
TAG_W_HYPERLINK = f"{{{NS_W}}}hyperlink"
TAG_V_IMAGEDATA = f"{{{NS_V}}}imagedata"


def extract_equations(
    docx_path: str | Path,
    output_dir: Optional[str | Path] = None,
) -> Tuple[List[Equation], dict]:
    """Extract MathType formulas and build placeholder-embedded paragraph text.

    Returns:
        equations:  List of Equation AST nodes with image_path set.
        para_texts: dict {paragraph_index: str}
                    e.g. {5: "we apply \\x00EQ\\x00 to the feature map"}
    """
    docx_path = Path(docx_path)
    output_dir = Path(output_dir) if output_dir else docx_path.parent
    figures_dir = output_dir / "figures"

    equations: List[Equation] = []
    para_texts: dict = {}

    with zipfile.ZipFile(docx_path, "r") as zf:
        rel_map = _load_rel_map(zf)

        xml_bytes = zf.read("word/document.xml")
        root = etree.fromstring(xml_bytes)
        body = root.find(f"{{{NS_W}}}body")
        if body is None:
            return equations, para_texts

        paragraphs = body.findall(f".//{TAG_W_P}")
        eq_counter = 1

        for para_idx, para_elem in enumerate(paragraphs):
            text_parts: list[str] = []
            offset_in_para = 0

            for child in para_elem.iterchildren():
                tag = child.tag

                # <w:r> — text run
                if tag == TAG_W_R:
                    text_elems = child.findall(f".//{TAG_W_T}")
                    for t in text_elems:
                        if t.text:
                            text_parts.append(t.text)

                # <w:tab> — tab character
                elif tag == TAG_W_TAB:
                    text_parts.append("\t")

                # <w:hyperlink> — might contain imagedata inside
                elif tag == TAG_W_HYPERLINK:
                    # Text inside hyperlink
                    for t in child.iter(TAG_W_T):
                        if t.text:
                            text_parts.append(t.text)
                    # Also check for VML imagedata inside hyperlink
                    for imagedata in child.iter(TAG_V_IMAGEDATA):
                        rid = imagedata.get(f"{{{NS_R}}}id", "")
                        if rid and rid in rel_map:
                            target = rel_map[rid]
                            if target.lower().endswith(".wmf"):
                                png_name = Path(target).name.replace(".wmf", ".png")
                                eq = Equation(
                                    id=f"eq_{eq_counter}",
                                    latex="",
                                    inline=False,
                                    label=f"({eq_counter})",
                                    image_path=str(figures_dir / png_name) if output_dir else None,
                                    paragraph_index=para_idx,
                                    offset_in_paragraph=offset_in_para,
                                    confidence=0.3,
                                )
                                equations.append(eq)
                                eq_counter += 1
                                offset_in_para += 1
                                text_parts.append(EQ_PLACEHOLDER)

                # VML imagedata (MathType formula) in paragraph directly
                if tag != TAG_W_HYPERLINK:
                    for imagedata in child.iter(TAG_V_IMAGEDATA):
                        rid = imagedata.get(f"{{{NS_R}}}id", "")
                        if rid and rid in rel_map:
                            target = rel_map[rid]
                            if target.lower().endswith(".wmf"):
                                png_name = Path(target).name.replace(".wmf", ".png")
                                eq = Equation(
                                    id=f"eq_{eq_counter}",
                                    latex="",
                                    inline=False,
                                    label=f"({eq_counter})",
                                    image_path=str(figures_dir / png_name) if output_dir else None,
                                    paragraph_index=para_idx,
                                    offset_in_paragraph=offset_in_para,
                                    confidence=0.3,
                                )
                                equations.append(eq)
                                eq_counter += 1
                                offset_in_para += 1
                                text_parts.append(EQ_PLACEHOLDER)

            para_text = "".join(text_parts)
            if para_text.strip():
                para_texts[para_idx] = para_text

    return equations, para_texts


def _load_rel_map(zf: zipfile.ZipFile) -> dict[str, str]:
    """Load relationship map: rId -> target path."""
    rel_map: dict[str, str] = {}
    try:
        rels_xml = zf.read("word/_rels/document.xml.rels")
        rels_root = etree.fromstring(rels_xml)
        ns_rel = f"{{{NS_REL}}}"
        for child in rels_root:
            rid = child.get("Id", "")
            target = child.get("Target", "")
            rel_map[rid] = target
    except (KeyError, etree.ParseError):
        pass
    return rel_map
