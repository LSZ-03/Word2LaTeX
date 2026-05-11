"""Patch registry.py — add house_style, validation_rules, manual_checks parsing."""
from pathlib import Path

path = Path("/home/zls/workspace/Word2PaperAI/manuscript_compiler/journal_profiles/registry.py")
content = path.read_text()

# 1. Fix the return statement in _yaml_to_profile
old = """            checks=checks,
        )"""

new = """            house_style=_parse_house_style(data.get("house_style")),
            checks=checks,
            validation_rules=_parse_validation_rules(
                data.get("validation_rules", {}).get("automated", [])
            ),
            manual_checks=_parse_manual_checks(
                data.get("validation_rules", {}).get("manual_checks", [])
            ),
        )"""

assert old in content, "old return not found!"
content = content.replace(old, new)

# 2. Add parser functions before _load_yaml
old_fn = """def _load_yaml(path: Path) -> dict | None:"""

new_fn = """def _parse_house_style(data):
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


def _load_yaml(path: Path) -> dict | None:"""

assert old_fn in content, "old _load_yaml not found!"
content = content.replace(old_fn, new_fn)

path.write_text(content)
print("✅ registry.py patched successfully")
print(f"  File size: {path.stat().st_size} bytes")
