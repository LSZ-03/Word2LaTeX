"""Equation model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Equation:
    id: str = ""
    latex: str = ""                   # LaTeX representation
    omml_xml: Optional[str] = None    # original OMML XML (for debugging)
    inline: bool = False              # True = $...$, False = \begin{equation}
    label: Optional[str] = None       # equation number / label
    image_path: Optional[str] = None  # path to formula image (WMF/PNG for MathType)
    paragraph_index: Optional[int] = None  # index in docx paragraphs for inline placement
    confidence: float = 1.0
    warnings: list[str] = field(default_factory=list)

    # 精确插入：公式在段落内是第几个（0-based），用于占位符展开
    offset_in_paragraph: int = 0

    # 语义分类：是 (1)(2)(3) 编号公式吗？
    is_equation_number: bool = False

    # 跳过渲染：编号已绑定到前一个 display eq，不独立输出
    skip_render: bool = False

    # 绑定的编号文本，如 "(1)"，渲染时附加到 display eq 的 caption 中
    number: str = ""
