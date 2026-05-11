#!/usr/bin/env python3
"""Manuscript layout compliance validator.

Usage:
    python3 -m manuscript_compiler.scripts.validate_output \
        --tex /path/to/main.tex \
        --journal tgrs

Or integrated in pipeline:
    from manuscript_compiler.scripts.validate_output import validate
    report = validate(main_tex_path, journal_name)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Ensure project root is on path
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def validate(tex_path: str | Path, journal: str) -> dict:
    """Validate main.tex against journal profile validation rules.

    Returns:
        {
            "journal": str,
            "total": int,
            "passed": int,
            "failed": int,
            "results": [
                {
                    "id": str,
                    "description": str,
                    "severity": str,
                    "status": "passed" | "failed" | "skipped",
                    "detail": str,
                },
                ...
            ],
            "manual_checks": [...],
            "house_style": {...} | None,
        }
    """
    from manuscript_compiler.journal_profiles.registry import ProfileRegistry

    tex_path = Path(tex_path)
    if not tex_path.exists():
        return {"error": f"File not found: {tex_path}"}

    tex_content = tex_path.read_text()

    reg = ProfileRegistry()
    profile = reg.get(journal)
    if profile is None:
        return {"error": f"Unknown journal: {journal}"}

    results = []

    # ── Automated checks ──────────────────────────────────────────
    for rule in profile.validation_rules:
        try:
            pattern = rule.pattern
            if rule.negate:
                # Negate: pattern should NOT be present (assertion fails if found)
                matched = bool(re.search(pattern, tex_content, re.MULTILINE))
                passed = not matched
                detail = f"Pattern not found (expected)" if passed else f"Pattern found but should NOT: {pattern[:60]}"
            else:
                # Normal: pattern should be present (assertion fails if not found)
                matched = bool(re.search(pattern, tex_content, re.MULTILINE))
                passed = matched
                detail = f"Pattern found: {pattern[:60]}" if passed else f"Pattern NOT found: {pattern[:60]}"
        except re.error as e:
            passed = False
            detail = f"Regex error: {e}"

        results.append({
            "id": rule.id,
            "description": rule.description,
            "severity": rule.severity,
            "status": "passed" if passed else "failed",
            "detail": detail,
        })

    # ── Manual checks ─────────────────────────────────────────────
    manual_results = []
    for mc in profile.manual_checks:
        manual_results.append({
            "id": mc.id,
            "title": mc.title,
            "items": mc.items,
        })

    # ── Summary ───────────────────────────────────────────────────
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")

    # House style info
    hs = None
    if profile.house_style:
        hs = {
            "section_order": profile.house_style.section_order,
            "float_spacing": profile.house_style.float_spacing,
            "fonts": profile.house_style.fonts,
        }

    return {
        "journal": profile.display_name,
        "status": profile.status,
        "total": total,
        "passed": passed,
        "failed": failed,
        "results": results,
        "manual_checks": manual_results,
        "house_style": hs,
    }


def print_report(report: dict) -> None:
    """Print a human-readable validation report."""
    if "error" in report:
        print(f"❌ {report['error']}")
        return

    print("=" * 55)
    print(f"  📋 格式合规报告 — {report['journal']}")
    print(f"  状态: {report['status']}")
    print("=" * 55)

    # Summary
    total = report["total"]
    passed = report["passed"]
    failed = report["failed"]
    print(f"\n📊 自动校验: {total} 项检查")
    print(f"   ✅ 通过: {passed}")
    print(f"   ❌ 失败: {failed}")
    if failed > 0:
        print(f"   ⚠️  通过这些才能确保 Overleaf 编译通过")

    # Detail by severity
    by_severity = {"error": [], "warning": [], "info": []}
    for r in report["results"]:
        by_severity.setdefault(r["severity"], []).append(r)

    for severity in ["error", "warning", "info"]:
        items = by_severity.get(severity, [])
        if not items:
            continue
        failed_items = [r for r in items if r["status"] == "failed"]
        if not failed_items:
            continue
        label = {"error": "❌ 错误 (必须修复)", "warning": "⚠️  警告 (建议修复)", "info": "ℹ️  提示"}.get(severity, severity)
        print(f"\n{label}:")
        for r in failed_items:
            print(f"   [{r['id']}] {r['description']}")
            print(f"          {r['detail']}")

    # Manual checks
    if report.get("manual_checks"):
        print(f"\n📋 手动检查项（需要人工确认）:")
        for mc in report["manual_checks"]:
            print(f"   [{mc['title']}]")
            for item in mc["items"]:
                print(f"     ☐ {item}")

    # House style
    if report.get("house_style"):
        hs = report["house_style"]
        print(f"\n📖 规范参考 (House Style):")
        if hs.get("section_order"):
            print(f"   章节顺序: {' → '.join(hs['section_order'])}")
        if hs.get("fonts"):
            print(f"   字体: {', '.join(hs['fonts'])}")
        if hs.get("float_spacing"):
            print(f"   Float 间距:")
            for k, v in hs["float_spacing"].items():
                print(f"     {k}: {v}")

    print(f"\n{'=' * 55}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Validate LaTeX output against journal profile")
    parser.add_argument("--tex", required=True, help="Path to main.tex")
    parser.add_argument("--journal", "-j", required=True, help="Journal slug (e.g. tgrs, ieee)")
    args = parser.parse_args()

    report = validate(args.tex, args.journal)
    print_report(report)

    # Exit with non-zero if any errors failed
    if "error" in report:
        sys.exit(1)
    errors_failed = sum(1 for r in report.get("results", []) if r["severity"] == "error" and r["status"] == "failed")
    if errors_failed > 0:
        sys.exit(1)
