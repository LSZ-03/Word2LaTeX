"""Formula recognition using Doubao Vision API.

Batch converts formula PNGs to LaTeX via Doubao (火山引擎) Vision API.
Supports: automatic retry, incremental recognition, persistent cache.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

DOUBAO_API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
DOUBAO_MODEL = "doubao-seed-2-0-mini-260428"

SYSTEM_PROMPT = """你是一个专业的数学公式 OCR 助手。
请将图片中的数学公式转换为标准 LaTeX 代码。

要求：
1. 只输出 LaTeX 代码，不要任何解释、代码块标记或前缀
2. 行间公式不要包含 \\begin{equation} 等环境，只输出公式内容
3. 变量使用斜体，向量/矩阵使用 \\mathbf{}
4. 如果图片不是公式，输出空字符串"""


def _image_to_base64(image_path: str | Path) -> str:
    """Read an image file and return base64-encoded data URI."""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{b64}"


def recognize_formula(
    image_path: str | Path,
    api_key: str,
    max_retries: int = 3,
    timeout: int = 30,
) -> str:
    """Recognize a single formula image and return LaTeX code.

    Returns empty string on failure.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        logger.warning(f"Image not found: {image_path}")
        return ""

    data_url = _image_to_base64(image_path)
    payload = {
        "model": DOUBAO_MODEL,
        "max_tokens": 512,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT.strip()},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url},
                    },
                    {"type": "text", "text": "请识别上图中的数学公式"},
                ],
            },
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(
                    DOUBAO_API_URL, json=payload, headers=headers
                )
                resp.raise_for_status()
                result = resp.json()
                latex = (
                    result.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                # Clean up markdown code blocks if any
                latex = re.sub(r"```latex\s*", "", latex)
                latex = re.sub(r"\s*```", "", latex)
                latex = latex.strip()
                logger.info(
                    f"✅ Recognized: {image_path.name} → {latex[:50]}..."
                )
                return latex
        except Exception as e:
            wait = 2**attempt
            logger.warning(
                f"❌ Attempt {attempt+1}/{max_retries} failed: {e}. "
                f"Retrying in {wait}s..."
            )
            time.sleep(wait)

    logger.error(f"All {max_retries} attempts failed for {image_path.name}")
    return ""


def batch_recognize(
    png_dir: Path,
    output_path: Path,
    api_key: str,
) -> dict[str, str]:
    """Batch recognize all PNG formulas in a directory.

    Results are saved incrementally to output_path (supports resume).

    Returns:
        {filename: latex} mapping.
    """
    # Load existing results (support incremental/resume)
    result_map: dict[str, str] = {}
    if output_path.exists():
        try:
            result_map = json.loads(output_path.read_text())
            logger.info(f"Loaded {len(result_map)} existing results")
        except Exception:
            result_map = {}

    png_files = sorted(png_dir.glob("*.png"))
    if not png_files:
        logger.info("No PNG files found")
        return result_map

    # Filter out already-recognized files
    to_process = [f for f in png_files if f.name not in result_map]
    logger.info(
        f"Total: {len(png_files)}, "
        f"Already done: {len(png_files) - len(to_process)}, "
        f"Remaining: {len(to_process)}"
    )

    new_count = 0
    for png_path in to_process:
        latex = recognize_formula(png_path, api_key)
        result_map[png_path.name] = latex
        new_count += 1

        # Save after each formula (prevent data loss on interrupt)
        if new_count % 5 == 0:
            output_path.write_text(
                json.dumps(result_map, ensure_ascii=False, indent=2)
            )
            logger.info(f"Saved checkpoint: {new_count} new formulas")

    # Final save
    output_path.write_text(
        json.dumps(result_map, ensure_ascii=False, indent=2)
    )
    logger.info(
        f"Done! New: {new_count}, Total: {len(result_map)}/{len(png_files)}"
    )
    return result_map


def batch_recognize_from_docx(
    docx_path: str | Path,
    output_dir: str | Path,
    api_key: str,
) -> dict[str, str]:
    """Full pipeline: extract WMF → convert to PNG → recognize via API.

    This is the high-level entry point for the pipeline.
    """
    from manuscript_compiler.agents.docx_parser.equation_extractor import (
        extract_equations,
    )
    from manuscript_compiler.agents.docx_parser.wmf_converter import (
        batch_convert,
    )

    docx_path = Path(docx_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Extract formulas (get WMF paths and paragraph positions)
    equations = extract_equations(docx_path, output_dir=output_dir)

    # Step 2: Convert WMF → PNG
    wmf_dir = output_dir / "figures"
    png_dir = output_dir / "formula_png"
    png_dir.mkdir(exist_ok=True)
    batch_convert(wmf_dir, png_dir, resolution=300)

    # Step 3: Recognize PNG → LaTeX
    map_path = output_dir / "formula_image_map.json"
    result_map = batch_recognize(png_dir, map_path, api_key)

    # Step 4: Inject LaTeX into equation objects
    injected = 0
    for eq in equations:
        if eq.image_path:
            fname = Path(eq.image_path).stem  # e.g. "image1"
            if fname in result_map and result_map[fname]:
                eq.latex = result_map[fname]
                eq.confidence = 0.85
                injected += 1

    logger.info(f"Injected LaTeX: {injected}/{len(equations)}")
    return result_map
