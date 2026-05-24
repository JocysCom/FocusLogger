#!/usr/bin/env python3
"""Restore the Playwright demo scaffold into the repo's Tests/UI.Playwright folder.

Usage:
  python restore_playwright_demo.py                        # default destination
  python restore_playwright_demo.py --dest Tests/E2E       # custom destination
  python restore_playwright_demo.py --force                # overwrite existing files
"""
import argparse, os, shutil, sys
from pathlib import Path

def section(title: str):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")

def copy_tree(src: Path, dest: Path, force: bool):
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dest / item.name
        if item.is_dir():
            copy_tree(item, target, force)
        else:
            if target.exists() and not force:
                print(f"SKIP (exists): {target}")
            else:
                shutil.copy2(item, target)
                print(f"WROTE: {target}")

def main():
    parser = argparse.ArgumentParser(description="Restore the Playwright demo scaffold.")
    parser.add_argument("--dest", default="Tests/UI.Playwright",
                        help="Destination folder relative to the repo root (default: Tests/UI.Playwright)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    template_root = script_dir.parent / "references" / "playwright-demo-scaffold"
    if not template_root.is_dir():
        print(f"Error: template folder not found at {template_root}", file=sys.stderr)
        sys.exit(1)

    repo_root = Path.cwd()
    dest_path = repo_root / args.dest

    section("Restore Playwright demo scaffold")
    print(f"  Repo root:   {repo_root}")
    print(f"  Template:    {template_root}")
    print(f"  Destination: {dest_path}")

    copy_tree(template_root, dest_path, args.force)

    section("Next steps")
    print(f"  cd {args.dest}")
    print("  npm install")
    print("  npx playwright install")
    print("  npx playwright test --ui --project=chromium")
    print("")
    print("  To run only the demo test:")
    print("  npx playwright test --grep @demo")

if __name__ == "__main__":
    main()
