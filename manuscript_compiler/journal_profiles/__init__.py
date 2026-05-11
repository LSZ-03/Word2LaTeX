"""Journal profile registry — built-in profiles and catalog integration.

Architecture:
  built-in profiles  │  catalog profiles (YAML)
  ──────────────────│─────────────────────────────────────
  TGRS, IEEE, ICLR   │  28 families + 87 journals
  always available   │  loaded on demand via ProfileRegistry

Usage:
    from manuscript_compiler.journal_profiles import get_profile, list_profiles
    from manuscript_compiler.journal_profiles.models import JournalProfile
    from manuscript_compiler.journal_profiles.registry import ProfileRegistry

    # Quick lookup (built-ins + fallback)
    profile = get_profile("tgrs")

    # Full catalog-aware lookup
    reg = ProfileRegistry()
    profile = reg.get("ieee-tro")
    for entry in reg.list_catalog():
        print(entry["slug"], entry["display_name"])
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from manuscript_compiler.journal_profiles.models import (
    JournalProfile,
    VerificationCheck,
)

# ═══════════════════════════════════════════════════════════════════════
#  Built-in profiles — always available, fully verified
#  Templates must be manually downloaded and placed under templates/{name}/.
# ═══════════════════════════════════════════════════════════════════════

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

TGRS = JournalProfile(
    name="tgrs",
    display_name="IEEE Transactions on Geoscience and Remote Sensing",
    template_dir="tgrs",

    documentclass="IEEEtran",
    class_options=["journal"],

    packages=[
        "cite", "graphicx", "amsmath", "amssymb",
        "url", "hyperref", "booktabs", "caption",
        "subcaption", "array", "algorithmic",
    ],
    package_options={
        "cite": "numbers,sort&compress",
        "hyperref": "colorlinks=true,linkcolor=black,citecolor=black,urlcolor=black",
    },
    preamble_extra=[
        r"\ifCLASSINFOpdf",
        r"  \DeclareGraphicsExtensions{.pdf,.png,.jpg}",
        r"\else",
        r"  \DeclareGraphicsExtensions{.eps}",
        r"\fi",
    ],

    bibliography_style="IEEEtran",
    bibliography_type="thebibliography",

    figure_max_width=r"0.45\textwidth",
    figure_placement="!t",
    table_placement="!t",

    journal_header="IEEE Transactions on Geoscience and Remote Sensing",
    journal_header_short="TGRS",
    status="verified",
)

IEEE_GENERIC = JournalProfile(
    name="ieee",
    display_name="IEEE Transactions (Generic)",
    template_dir="ieee",

    documentclass="IEEEtran",
    class_options=["journal"],

    packages=["cite", "graphicx", "amsmath", "amssymb", "hyperref", "booktabs"],
    package_options={
        "cite": "numbers,sort&compress",
        "hyperref": "colorlinks=true,linkcolor=black,citecolor=black,urlcolor=black",
    },

    bibliography_style="IEEEtran",
    figure_max_width=r"0.45\textwidth",
    status="verified",
)

ICLR = JournalProfile(
    name="iclr",
    display_name="International Conference on Learning Representations",
    template_dir="",

    documentclass="article",
    class_options=["10pt", "final"],

    packages=["amsmath", "amssymb", "graphicx", "hyperref", "booktabs", "natbib"],
    package_options={"natbib": "numbers,sort&compress"},

    bibliography_style="plainnat",
    figure_max_width=r"0.9\columnwidth",
    status="verified",
)

# ── Registry ─────────────────────────────────────────────────────────

_BUILTIN_PROFILES: dict[str, JournalProfile] = {
    "tgrs": TGRS,
    "ieee": IEEE_GENERIC,
    "iclr": ICLR,
}


def get_profile(name: str) -> JournalProfile:
    """Get a journal profile by name with catalog-aware lookup.

    Resolution: built-ins → catalog journals → catalog families → IEEE_GENERIC
    """
    from manuscript_compiler.journal_profiles.registry import ProfileRegistry

    name = name.strip().lower()
    reg = ProfileRegistry()
    return reg.get(name) or IEEE_GENERIC


def list_profiles() -> list[dict]:
    """List all available profiles (built-in + catalog)."""
    from manuscript_compiler.journal_profiles.registry import ProfileRegistry

    builtin_list = [
        {"slug": p.name, "display_name": p.display_name, "family": "", "status": p.status, "type": "builtin"}
        for p in _BUILTIN_PROFILES.values()
    ]
    reg = ProfileRegistry()
    return builtin_list + reg.list_catalog()
