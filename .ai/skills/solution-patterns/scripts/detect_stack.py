#!/usr/bin/env python3
"""Detect which technology stacks are present in a repo.

Part of the solution-patterns skill. Zero required arguments — auto-discovers
the repo root from the current directory and scans for stack signals defined
in the references/{stack}-patterns.md files.

Emitted stacks (stable IDs — referenced by other scripts):
  angular, nextjs, aspnet-core, wpf, winui, winforms

Examples:
  python detect_stack.py                      # human-readable summary
  python detect_stack.py --json               # JSON for AI consumption
  python detect_stack.py --root C:/repos/foo  # explicit repo root
"""
import argparse, json, os, re, sys
from pathlib import Path

# -- Repo root discovery ------------------------------------------------------

def find_repo_root(start: Path) -> Path:
    """Walk up looking for .git/ or a solution/package anchor. Fall back to start."""
    d = start.resolve()
    while True:
        if (d / ".git").exists():
            return d
        parent = d.parent
        if parent == d:
            return start.resolve()
        d = parent

# -- File helpers -------------------------------------------------------------

SKIP_DIRS = {"node_modules", "bin", "obj", ".git", ".vs", ".idea",
             "dist", "build", "out", ".next", "TestResults"}

def walk_files(root: Path, suffixes: tuple[str, ...] | None = None,
               name: str | None = None) -> list[Path]:
    """Recursively list files, skipping SKIP_DIRS. Match by suffix or exact name."""
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for f in filenames:
            if name and f == name:
                out.append(Path(dirpath) / f)
            elif suffixes and f.endswith(suffixes):
                out.append(Path(dirpath) / f)
    return out

def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""

# -- Per-stack detectors ------------------------------------------------------

def detect_angular(root: Path) -> list[dict]:
    hits = []
    for ng in walk_files(root, name="angular.json"):
        hits.append({"evidence": str(ng.relative_to(root)).replace("\\", "/"),
                     "reason": "angular.json present"})
    for pkg in walk_files(root, name="package.json"):
        txt = read_text(pkg)
        if '"@angular/core"' in txt:
            hits.append({"evidence": str(pkg.relative_to(root)).replace("\\", "/"),
                         "reason": "@angular/core in dependencies"})
    return hits

def detect_nextjs(root: Path) -> list[dict]:
    hits = []
    for name in ("next.config.js", "next.config.ts", "next.config.mjs", "next.config.cjs"):
        for p in walk_files(root, name=name):
            hits.append({"evidence": str(p.relative_to(root)).replace("\\", "/"),
                         "reason": f"{name} present"})
    for pkg in walk_files(root, name="package.json"):
        txt = read_text(pkg)
        if re.search(r'"next"\s*:\s*"', txt):
            hits.append({"evidence": str(pkg.relative_to(root)).replace("\\", "/"),
                         "reason": "next in dependencies"})
    return hits

def detect_aspnet_core(root: Path) -> list[dict]:
    hits = []
    for csproj in walk_files(root, suffixes=(".csproj",)):
        txt = read_text(csproj)
        if 'Sdk="Microsoft.NET.Sdk.Web"' in txt or "Microsoft.NET.Sdk.Web" in txt:
            sub_modes = []
            proj_dir = csproj.parent
            if (proj_dir / "Pages").is_dir():
                sub_modes.append("razor-pages")
            if (proj_dir / "Controllers").is_dir():
                sub_modes.append("mvc")
            prog = proj_dir / "Program.cs"
            if prog.exists() and re.search(r"app\.Map(Get|Post|Put|Delete|Patch)\b",
                                           read_text(prog)):
                sub_modes.append("minimal-api")
            if not sub_modes:
                sub_modes.append("minimal-flat")
            hits.append({
                "evidence": str(csproj.relative_to(root)).replace("\\", "/"),
                "reason": "Microsoft.NET.Sdk.Web",
                "subModes": sub_modes,
            })
    return hits

def detect_wpf(root: Path) -> list[dict]:
    hits = []
    for csproj in walk_files(root, suffixes=(".csproj",)):
        txt = read_text(csproj)
        if re.search(r"<UseWPF>\s*true\s*</UseWPF>", txt, re.IGNORECASE):
            hits.append({"evidence": str(csproj.relative_to(root)).replace("\\", "/"),
                         "reason": "<UseWPF>true</UseWPF>"})
    return hits

def detect_winui(root: Path) -> list[dict]:
    hits = []
    for csproj in walk_files(root, suffixes=(".csproj",)):
        txt = read_text(csproj)
        if re.search(r"<UseWinUI>\s*true\s*</UseWinUI>", txt, re.IGNORECASE):
            hits.append({"evidence": str(csproj.relative_to(root)).replace("\\", "/"),
                         "reason": "<UseWinUI>true</UseWinUI>"})
        elif "Microsoft.WindowsAppSDK" in txt:
            hits.append({"evidence": str(csproj.relative_to(root)).replace("\\", "/"),
                         "reason": "Microsoft.WindowsAppSDK package reference"})
    return hits

def detect_winforms(root: Path) -> list[dict]:
    hits = []
    for csproj in walk_files(root, suffixes=(".csproj",)):
        txt = read_text(csproj)
        if re.search(r"<UseWindowsForms>\s*true\s*</UseWindowsForms>", txt, re.IGNORECASE):
            hits.append({"evidence": str(csproj.relative_to(root)).replace("\\", "/"),
                         "reason": "<UseWindowsForms>true</UseWindowsForms>"})
    return hits

DETECTORS = {
    "angular": detect_angular,
    "nextjs": detect_nextjs,
    "aspnet-core": detect_aspnet_core,
    "wpf": detect_wpf,
    "winui": detect_winui,
    "winforms": detect_winforms,
}

# -- Main ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Detect technology stacks present in a repo (solution-patterns skill).")
    parser.add_argument("--root", help="Repo root (auto-discovered if omitted)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else find_repo_root(Path.cwd())

    result = {"root": str(root).replace("\\", "/"), "stacks": {}}
    for stack, detector in DETECTORS.items():
        hits = detector(root)
        if hits:
            result["stacks"][stack] = hits

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"\nStack detection: {root}")
    print("-" * 60)
    if not result["stacks"]:
        print("  No recognised stacks found.")
        print("  (Supported: angular, nextjs, aspnet-core, wpf, winui, winforms)")
        sys.exit(0)

    for stack, hits in result["stacks"].items():
        print(f"  \033[32m{stack}\033[0m ({len(hits)} match{'es' if len(hits) != 1 else ''})")
        for h in hits[:5]:
            extra = ""
            if "subModes" in h:
                extra = f"  [{', '.join(h['subModes'])}]"
            print(f"    - {h['evidence']}  ({h['reason']}){extra}")
        if len(hits) > 5:
            print(f"    ... and {len(hits) - 5} more")
    print()

if __name__ == "__main__":
    main()
