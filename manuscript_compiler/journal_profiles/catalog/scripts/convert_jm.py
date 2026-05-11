#!/usr/bin/env python3
"""Convert JournalManuscript markdown profiles → structured YAML.

Extracts structured metadata from JournalManuscript's profile.md,
verification.yaml, and layout-checklist.md files, then writes clean
profile.yaml files into our catalog directory.

Usage:
    python3 -m manuscript_compiler.journal_profiles.catalog.scripts.convert_jm \
        --source /path/to/JournalManuscript/journal-manuscript

Output:
    catalog/families/{slug}/profile.yaml     ← 28 family baselines
    catalog/journals/{family}/{slug}/profile.yaml  ← 87 journal profiles
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
from pathlib import Path

import yaml

# Adjust path for running as script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("convert_jm")

# ── Output directories ────────────────────────────────────────────────
CATALOG_FAMILIES = Path(__file__).resolve().parent.parent / "families"
CATALOG_JOURNALS = Path(__file__).resolve().parent.parent / "journals"


# ═══════════════════════════════════════════════════════════════════════
#  Parsers
# ═══════════════════════════════════════════════════════════════════════

def parse_family_profile(md_path: Path) -> dict:
    """Parse a family-level profile.md into structured data."""
    text = md_path.read_text()
    slug = md_path.parent.name

    data = {
        "slug": slug,
        "display_name": _extract_title(text) or f"{slug.title()} Family",
        "family": "",
        "status": "checklist-required",
        "documentclass": _extract_documentclass(text) or "article",
        "class_options": [],
        "packages": [],
        "package_options": {},
        "preamble_extra": [],
        "section_numbering": "arabic",
        "section_depth": 3,
        "bibliography_style": _extract_bibstyle(text) or "ieeetr",
        "bibliography_type": "thebibliography",
        "figure_placement": "tbp",
        "figure_max_width": r"0.9\columnwidth",
        "table_placement": "tbp",
        "table_default_align": "c",
        "table_style": "booktabs",
        "caption_style": "bf",
        "journal_header": "",
        "journal_header_short": "",
        "template_dir": slug,
        "official_source": _extract_source_url(text),
        "template_package_url": _extract_package_url(text),
        "template_package_path": "",
        "checks": [],
    }

    # Extract packages
    packages = _extract_packages(text)
    if packages:
        data["packages"] = packages

    # Extract class options
    class_opt = _extract_class_options(text)
    if class_opt:
        data["class_options"] = class_opt

    # Extract figure placement
    placement = _extract_figure_placement(text)
    if placement:
        data["figure_placement"] = placement

    # Extract verification status
    vfy_path = md_path.parent / "verification.yaml"
    if vfy_path.exists():
        vfy_data = _load_yaml(vfy_path)
        if vfy_data:
            data["status"] = vfy_data.get("status", "checklist-required")
            # Parse verification checks
            for vc in vfy_data.get("verification_checks", []):
                data["checks"].append({
                    "id": vc.get("id", ""),
                    "title": vc.get("title", ""),
                    "requirement": vc.get("requirement", ""),
                    "status": "verified" if data["status"] == "verified" else "checklist-required",
                })
            data["official_source"] = vfy_data.get("official_source", data["official_source"])
            data["template_package_url"] = vfy_data.get("official_template_import", {}).get(
                "package_url", data["template_package_url"]
            )

    return data


def parse_journal_profile(md_path: Path, family_slug: str) -> dict:
    """Parse a journal-level profile.md into structured data.

    Journals inherit from their family. We only capture overrides here.
    """
    text = md_path.read_text()
    slug = md_path.parent.name

    data = {
        "slug": slug,
        "display_name": _extract_title(text) or slug.replace("-", " ").title(),
        "family": family_slug,
        "status": "checklist-required",
        # Fields with empty values will inherit from family at runtime
        "documentclass": "",
        "class_options": [],
        "packages": [],
        "package_options": {},
        "preamble_extra": [],
        "section_numbering": "",
        "section_depth": 0,
        "bibliography_style": "",
        "bibliography_type": "",
        "figure_placement": "",
        "figure_max_width": "",
        "table_placement": "",
        "table_default_align": "",
        "table_style": "",
        "caption_style": "",
        "journal_header": _extract_journal_header(text),
        "journal_header_short": _extract_journal_header_short(text),
        "template_dir": "",
        "official_source": _extract_source_url(text),
        "template_package_url": "",
        "template_package_path": "",
        "checks": [],
    }

    # Verification
    vfy_path = md_path.parent / "verification.yaml"
    if vfy_path.exists():
        vfy_data = _load_yaml(vfy_path)
        if vfy_data:
            data["status"] = vfy_data.get("status", "checklist-required")
            for vc in vfy_data.get("verification_checks", []):
                data["checks"].append({
                    "id": vc.get("id", ""),
                    "title": vc.get("title", ""),
                    "requirement": vc.get("requirement", ""),
                    "status": vc.get("status", "checklist-required"),
                })
            data["official_source"] = vfy_data.get("official_source", data["official_source"])
            data["template_package_url"] = vfy_data.get("official_template_import", {}).get(
                "package_url", ""
            )

    return data


# ═══════════════════════════════════════════════════════════════════════
#  Extraction helpers
# ═══════════════════════════════════════════════════════════════════════

def _extract_title(text: str) -> str:
    """Extract the first H1 heading as display name."""
    m = re.search(r"^#\s+(.+)", text, re.MULTILINE)
    if m:
        title = m.group(1).strip()
        # Remove " Profile" suffix
        title = re.sub(r"\s+Profile$", "", title)
        return title
    return ""


def _extract_documentclass(text: str) -> str:
    """Extract the primary LaTeX class from the profile."""
    # Look for patterns like "Base class: `IEEEtran`" or "Primary LaTeX anchor: `IEEEtran`"
    m = re.search(r"(?:Base class|Primary LaTeX anchor|documentclass)[:\s]+`(\w+)`", text)
    if m:
        return m.group(1)
    # Or just `\documentclass[journal]{IEEEtran}`
    m = re.search(r"\\documentclass(?:\[[^\]]*\])?\{(\w+)\}", text)
    if m:
        return m.group(1)
    return ""


def _extract_class_options(text: str) -> list[str]:
    """Extract class options like [journal] from examples."""
    m = re.search(r"\\documentclass\[([^\]]+)\]\{(\w+)\}", text)
    if m:
        return [opt.strip() for opt in m.group(1).split(",")]
    return []


def _extract_packages(text: str) -> list[str]:
    """Extract packages mentioned in the profile."""
    # Look for code blocks with \usepackage patterns
    packages = set()
    for m in re.finditer(r"\\usepackage(?:\[[^\]]*\])?\{(\w+)\}", text):
        packages.add(m.group(1))
    # Also look for bullet lists of packages
    in_list = False
    for line in text.split("\n"):
        if re.match(r"^\s*-\s+`?\w+`?", line) and any(pkg in line for pkg in
                ["amsmath", "graphicx", "booktabs", "cite", "hyperref", "natbib"]):
            m = re.search(r"`(\w+)`", line)
            if m:
                packages.add(m.group(1))
    return sorted(packages)


def _extract_bibstyle(text: str) -> str:
    """Extract bibliography style."""
    m = re.search(r"(?:bibliography style|bibliography|reference style|citation style)[:\s]+`?(\w+)`?",
                  text, re.IGNORECASE)
    if m:
        style = m.group(1).lower()
        if "ieee" in style:
            return "IEEEtran"
        if "nature" in style:
            return "naturemag"
        return style
    # Check for patterns like "numeric IEEE references"
    if re.search(r"numeric\s+IEEE", text, re.IGNORECASE):
        return "IEEEtran"
    return ""


def _extract_source_url(text: str) -> str:
    """Extract official source URL."""
    m = re.search(r"(?:official guide page|official source):\s*(https?://\S+)", text, re.IGNORECASE)
    return m.group(1).strip().rstrip(".") if m else ""


def _extract_package_url(text: str) -> str:
    """Extract template download URL."""
    m = re.search(r"(?:official template download|package_url):\s*(https?://\S+)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip().rstrip(".")
    m = re.search(r"https?://mirrors\.ctan\.org\S+", text)
    return m.group(0).strip() if m else ""


def _extract_figure_placement(text: str) -> str:
    """Extract figure float placement specifier."""
    m = re.search(r"`\[!?([a-z]+)\]`", text)
    if m:
        return "!" + m.group(1)
    return ""


def _extract_journal_header(text: str) -> str:
    """Extract journal full name."""
    title = _extract_title(text)
    if title:
        return title
    return ""


def _extract_journal_header_short(text: str) -> str:
    """Extract journal abbreviation."""
    slug = Path(text).parent.name if hasattr(text, "parent") else ""
    if slug:
        parts = slug.replace("ieee-", "").replace("-", " ").upper().split()
        return "".join(p[0] for p in parts if p) if len(parts) <= 4 else slug
    return slug


def _load_yaml(path: Path) -> dict | None:
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════
#  Main converter
# ═══════════════════════════════════════════════════════════════════════

def convert(source_dir: str | Path):
    """Convert all JournalManuscript profiles to structured YAML."""
    source = Path(source_dir)
    journals_root = source / "references" / "journals"

    if not journals_root.exists():
        logger.error(f"Source not found: {journals_root}")
        return

    # ── Convert families ─────────────────────────────────────────────
    families_dir = CATALOG_FAMILIES
    families_dir.mkdir(parents=True, exist_ok=True)

    family_count = 0
    for item in sorted(journals_root.iterdir()):
        if not item.is_dir():
            continue
        slug = item.name
        md_path = item / "profile.md"
        if not md_path.exists():
            continue

        # Check if it's a family (has no parent slug in path)
        if item.parent == journals_root:
            data = parse_family_profile(md_path)

            # Write YAML
            out = families_dir / slug
            out.mkdir(parents=True, exist_ok=True)
            _write_yaml(data, out / "profile.yaml")
            family_count += 1
            logger.info(f"  ✅ [family]   {slug:30s} → {data.get('display_name', '')[:50]}")

    # ── Convert journals ─────────────────────────────────────────────
    journals_out = CATALOG_JOURNALS
    journals_out.mkdir(parents=True, exist_ok=True)

    journal_count = 0
    for family_dir in sorted(journals_root.iterdir()):
        if not family_dir.is_dir():
            continue
        family_slug = family_dir.name

        for journal_dir in sorted(family_dir.iterdir()):
            if not journal_dir.is_dir():
                continue
            md_path = journal_dir / "profile.md"
            if not md_path.exists():
                continue

            data = parse_journal_profile(md_path, family_slug)

            # Write YAML
            out = journals_out / family_slug / data["slug"]
            out.mkdir(parents=True, exist_ok=True)
            _write_yaml(data, out / "profile.yaml")
            journal_count += 1
            logger.info(f"  ✅ [journal]  {family_slug}/{data['slug']} → {data.get('display_name', '')[:50]}")

    logger.info(f"\n📊 Complete: {family_count} families, {journal_count} journals")


def _write_yaml(data: dict, path: Path):
    """Write structured, well-formatted YAML."""
    # Clean up empty values for readability
    cleaned = _clean_empty(data)
    with open(path, "w") as f:
        yaml.dump(cleaned, f, default_flow_style=False, allow_unicode=True,
                  sort_keys=False, width=120)
        f.write("\n")  # trailing newline


def _clean_empty(d: dict) -> dict:
    """Remove empty lists and empty strings for cleaner YAML output."""
    result = {}
    for k, v in d.items():
        if isinstance(v, list) and not v:
            continue
        if isinstance(v, str) and not v:
            continue
        if isinstance(v, dict) and not v:
            continue
        if isinstance(v, dict):
            v = _clean_empty(v)
        result[k] = v
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert JournalManuscript profiles to YAML")
    parser.add_argument("--source", required=True,
                        help="Path to JournalManuscript/journal-manuscript/ directory")
    args = parser.parse_args()
    convert(args.source)
