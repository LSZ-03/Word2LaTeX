"""WMF to PNG converter using Wand (ImageMagick).

Replaces the Windows PowerShell .NET approach with native Linux WMF conversion.
Requires: libmagickwand-6.q16-6 (runtime) + Wand (Python binding).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from wand.image import Image as WandImage
from wand.color import Color

logger = logging.getLogger(__name__)


def wmf_to_png(
    wmf_path: str | Path,
    output_path: str | Path,
    resolution: int = 300,
) -> bool:
    """Convert a single WMF file to PNG using ImageMagick.

    Args:
        wmf_path: Path to input WMF file.
        output_path: Path to output PNG file.
        resolution: DPI for rendering (higher = better OCR quality).

    Returns:
        True if successful, False otherwise.
    """
    wmf_path = Path(wmf_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not wmf_path.exists():
        logger.warning(f"WMF file not found: {wmf_path}")
        return False

    try:
        with WandImage(filename=str(wmf_path), resolution=resolution) as img:
            img.format = "png"
            img.background_color = Color("white")
            img.alpha_channel = "remove"
            img.save(filename=str(output_path))
        logger.info(f"✅ WMF → PNG: {wmf_path.name} → {output_path.name}")
        return True
    except Exception as e:
        logger.warning(f"❌ WMF → PNG failed for {wmf_path.name}: {e}")
        return False


def batch_convert(
    wmf_dir: Path,
    output_dir: Path,
    resolution: int = 300,
) -> dict[str, str]:
    """Batch convert all WMF files in a directory to PNG.

    Returns:
        {wmf_filename: png_path} mapping.
    """
    mapping: dict[str, str] = {}
    wmf_files = sorted(wmf_dir.glob("*.wmf"))
    if not wmf_files:
        logger.info("No WMF files found")
        return mapping

    logger.info(f"Found {len(wmf_files)} WMF files")
    for wmf_path in wmf_files:
        png_name = wmf_path.stem + ".png"
        png_path = output_dir / png_name
        if wmf_to_png(wmf_path, png_path, resolution):
            mapping[wmf_path.name] = str(png_path)

    logger.info(f"Converted {len(mapping)}/{len(wmf_files)} files")
    return mapping
