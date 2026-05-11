"""Word2LaTeX — Command-line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from manuscript_compiler.pipelines.full_pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Word2LaTeX — Convert Word manuscripts to LaTeX",
    )
    parser.add_argument("input", help="Path to input .docx file")
    parser.add_argument("-o", "--output-dir", help="Output directory (default: auto)")
    parser.add_argument("-j", "--journal", help="Target journal (e.g. ieee, tgrs)")
    parser.add_argument("--save-ast", action="store_true", help="Save intermediate AST as JSON")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ File not found: {args.input}")
        sys.exit(1)
    if input_path.suffix.lower() not in (".docx",):
        print(f"❌ Expected a .docx file, got: {input_path.suffix}")
        sys.exit(1)

    manuscript = run_pipeline(
        docx_path=args.input,
        output_dir=args.output_dir,
        journal=args.journal,
    )

    if args.save_ast:
        import json
        from dataclasses import asdict
        ast_path = Path(args.output_dir or input_path.parent / f"{input_path.stem}_output") / "ast.json"
        ast_path.parent.mkdir(parents=True, exist_ok=True)
        ast_path.write_text(json.dumps(asdict(manuscript), indent=2, default=str), encoding="utf-8")
        print(f"\n💾 AST saved to: {ast_path}")


if __name__ == "__main__":
    main()
