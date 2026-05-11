"""ProfileRegistry — load, cache, and resolve journal profiles.

Architecture:
  ┌─ built-in profiles (__init__.py) ──┐
  │  TGRS, IEEE_GENERIC, ICLR          │  ← always available, fully verified
  └────────────────────────────────────┘
  ┌─ catalog profiles (YAML files) ────┐
  │  catalog/families/{slug}/           │  ← 28 family baselines
  │  catalog/journals/{family}/{slug}/  │  ← 87 journal overrides
  └────────────────────────────────────┘

Resolution order:
  1. Check built-in profiles first (name match)
  2. Check catalog/journals/{family}/{name}/
  3. Check catalog/journals/{name}/  (flat lookup)
  4. Fall back to family baseline
  5. Fall back to IEEE_GENERIC
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Dict

import yaml

from manuscript_compiler.journal_profiles.models import (
    JournalProfile,
    VerificationCheck,
    ValidationRule,
    ManualCheck,
    HouseStyle,
)

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_CATALOG_ROOT = Path(__file__).resolve().parent / "catalog"
_FAMILIES_DIR = _CATALOG_ROOT / "families"
_JOURNALS_DIR = _CATALOG_ROOT / "journals"


class ProfileRegistry:
    """Lazy-loaded registry of all journal profiles.

    Usage:
        reg = ProfileRegistry()
        profile = reg.get("tgrs")               # → built-in TGRS
        profile = reg.get("ieee-jstars")         # → catalog journal
        profile = reg.get("elsevier")            # → family baseline

        for p in reg.list_catalog():
            print(p.name, p.display_name)
    """

    def __init__(self):
        # Built-in profiles: imported late to avoid circular deps
        from manuscript_compiler.journal_profiles import (
            TGRS, IEEE_GENERIC, ICLR, _BUILTIN_PROFILES,
        )
        self._builtins: dict[str, JournalProfile] = dict(_BUILTIN_PROFILES)

        # Lazy caches
        self._family_cache: dict[str, JournalProfile] | None = None
        self._journal_cache: dict[str, JournalProfile] | None = None
        self._family_list: list[str] | None = None
        self._journal_list: list[dict] | None = None

    # ── Public API ─────────────────────────────────────────────────

    def get(self, name: str) -> JournalProfile | None:
        """Resolve a journal profile by name/slug.

        Resolution order: builtins → journals → families → IEEE_GENERIC
        """
        name = name.strip().lower()

        # 1. Check catalog families FIRST (richer data: house_style, validation_rules, etc.)
        #    If found, merge with any builtin that has the same slug
        family = self._load_family(name)
        if family:
            # Merge builtin fields if the same-named builtin exists
            if name in self._builtins:
                builtin = self._builtins[name]
                family.merge_family_defaults(builtin)
            return family

        # 2. Built-in
        if name in self._builtins:
            return self._builtins[name]

        # 2. Catalog journals
        journal = self._load_journal(name)
        if journal:
            return journal

        # 3. Catalog families
        family = self._load_family(name)
        if family:
            return family

        # 4. Fallback
        logger.warning(f"Unknown journal '{name}', falling back to IEEE_GENERIC")
        return self._builtins.get("ieee")

    def get_builtin(self, name: str) -> JournalProfile | None:
        """Get a built-in profile only."""
        return self._builtins.get(name.strip().lower())

    def list_catalog(self) -> list[dict]:
        """Return catalog summary: [{slug, display_name, family, status}, ...]"""
        if self._journal_list is not None:
            return self._journal_list

        entries = []
        # Families
        for p in self._load_all_families().values():
            entries.append({
                "slug": p.name,
                "display_name": p.display_name,
                "family": "",
                "status": p.status,
                "type": "family",
            })
        # Journals
        journals_dir = _JOURNALS_DIR
        if journals_dir.exists():
            for family_dir in sorted(journals_dir.iterdir()):
                if not family_dir.is_dir():
                    continue
                for journal_dir in sorted(family_dir.iterdir()):
                    yaml_path = journal_dir / "profile.yaml"
                    if yaml_path.exists():
                        data = _load_yaml(yaml_path)
                        if data:
                            entries.append({
                                "slug": data.get("slug", journal_dir.name),
                                "display_name": data.get("display_name", journal_dir.name),
                                "family": family_dir.name,
                                "status": data.get("status", "unknown"),
                                "type": "journal",
                            })
        self._journal_list = entries
        return entries

    def list_families(self) -> list[str]:
        """List all family slugs."""
        if self._family_list is None:
            self._load_all_families()
        return list(self._family_cache.keys()) if self._family_cache else []

    # ── Internal loaders ───────────────────────────────────────────

    def _load_family(self, slug: str) -> JournalProfile | None:
        """Load a family profile by slug."""
        if self._family_cache is None:
            self._load_all_families()
        return self._family_cache.get(slug) if self._family_cache else None

    def _load_all_families(self) -> dict[str, JournalProfile]:
        """Load all family profiles from catalog/families/."""
        if self._family_cache is not None:
            return self._family_cache

        self._family_cache = {}
        families_dir = _FAMILIES_DIR
        if not families_dir.exists():
            return self._family_cache

        for family_dir in sorted(families_dir.iterdir()):
            if not family_dir.is_dir():
                continue
            yaml_path = family_dir / "profile.yaml"
            if yaml_path.exists():
                profile = _yaml_to_profile(yaml_path)
                if profile:
                    self._family_cache[profile.name] = profile

        return self._family_cache

    def _load_journal(self, slug: str) -> JournalProfile | None:
        """Load a journal profile by slug. Search all family subdirectories."""
        journals_dir = _JOURNALS_DIR
        if not journals_dir.exists():
            return None

        for family_dir in sorted(journals_dir.iterdir()):
            if not family_dir.is_dir():
                continue
            journal_dir = family_dir / slug
            yaml_path = journal_dir / "profile.yaml"
            if yaml_path.exists():
                profile = _yaml_to_profile(yaml_path)
                if profile:
                    # Resolve family inheritance
                    family = self._load_family(profile.family)
                    if family:
                        profile.merge_family_defaults(family)
                    return profile

        # Also try flat lookup: journals/{slug}/
        flat_path = journals_dir / slug / "profile.yaml"
        if flat_path.exists():
            return _yaml_to_profile(flat_path)

        return None


# ── YAML helpers ───────────────────────────────────────────────────────

def _parse_house_style(data):
    if not data:
        return None
    from manuscript_compiler.journal_profiles.models import HouseStyle
    return HouseStyle(
        section_order=data.get("section_order", []),
        float_spacing=data.get("float_spacing", {}),
        fonts=data.get("fonts", []),
        front_matter=data.get("front_matter", []),
    )


def _parse_validation_rules(rules):
    from manuscript_compiler.journal_profiles.models import ValidationRule
    result = []
    for r in rules:
        result.append(ValidationRule(
            id=r.get("id", ""),
            description=r.get("description", ""),
            pattern=r.get("pattern", ""),
            severity=r.get("severity", "warning"),
            negate=r.get("negate", False),
        ))
    return result


def _parse_manual_checks(checks):
    from manuscript_compiler.journal_profiles.models import ManualCheck
    result = []
    for c in checks:
        result.append(ManualCheck(
            id=c.get("id", ""),
            title=c.get("title", ""),
            items=c.get("items", []),
        ))
    return result


def _parse_caption_policy(data):
    if not data:
        return None
    from manuscript_compiler.journal_profiles.models import CaptionPolicy
    return CaptionPolicy(
        figure_position=data.get("figure_position", "below"),
        table_position=data.get("table_position", "above"),
    )


def _parse_float_policy(data):
    if not data:
        return None
    from manuscript_compiler.journal_profiles.models import FloatPolicy
    return FloatPolicy(
        strategy=data.get("strategy", "near_reference"),
    )


def _load_yaml(path: Path) -> dict | None:
    """Load a YAML file, returning None on failure."""
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Failed to load {path}: {e}")
        return None


def _yaml_to_profile(yaml_path: Path) -> JournalProfile | None:
    """Parse a profile.yaml into a JournalProfile dataclass."""
    data = _load_yaml(yaml_path)
    if not data:
        return None

    try:
        # Parse verification checks
        checks = []
        for c in data.get("checks", []):
            checks.append(VerificationCheck(
                id=c.get("id", ""),
                title=c.get("title", ""),
                requirement=c.get("requirement", ""),
                status=c.get("status", "unchecked"),
            ))

        # For catalog profiles, use empty-string defaults for inheritable fields.
        # This ensures merge_family_defaults() can fill them from the family baseline.
        status = data.get("status", "checklist-required")
        is_catalog = status != "builtin"

        def _catalog_default(value, catalog_default=""):
            """Return catalog_default if this is a catalog profile and value is absent."""
            return data.get(value, catalog_default) if is_catalog else data.get(value)

        return JournalProfile(
            name=data.get("slug", yaml_path.parent.name),
            display_name=data.get("display_name", ""),
            family=data.get("family", ""),
            documentclass=_catalog_default("documentclass", ""),
            class_options=_catalog_default("class_options", []),
            packages=data.get("packages", []),
            package_options=data.get("package_options", {}),
            preamble_extra=data.get("preamble_extra", []),
            section_numbering=_catalog_default("section_numbering", ""),
            section_depth=_catalog_default("section_depth", 0),
            bibliography_style=_catalog_default("bibliography_style", ""),
            bibliography_type=_catalog_default("bibliography_type", ""),
            figure_max_width=_catalog_default("figure_max_width", ""),
            figure_allowed_formats=data.get("figure_allowed_formats",
                                           ["pdf", "eps", "png", "jpg"]),
            figure_placement=_catalog_default("figure_placement", ""),
            table_placement=_catalog_default("table_placement", ""),
            table_default_align=_catalog_default("table_default_align", ""),
            table_style=_catalog_default("table_style", ""),
            caption_style=_catalog_default("caption_style", ""),
            journal_header=data.get("journal_header", ""),
            journal_header_short=data.get("journal_header_short", ""),
            template_dir=data.get("template_dir", ""),
            status=status,
            official_source=data.get("official_source", ""),
            template_package_url=data.get("template_package_url", ""),
            template_package_path=data.get("template_package_path", ""),
            house_style=_parse_house_style(data.get("house_style")),
            caption_policy=_parse_caption_policy(data.get("caption_policy")),
            float_policy=_parse_float_policy(data.get("float_policy")),
            checks=checks,
            validation_rules=_parse_validation_rules(
                data.get("validation_rules", {}).get("automated", [])
            ),
            manual_checks=_parse_manual_checks(
                data.get("validation_rules", {}).get("manual_checks", [])
            ),
        )
    except Exception as e:
        logger.error(f"Failed to parse {yaml_path}: {e}")
        return None
