#!/usr/bin/env python3
"""Coverage mirror checker and impact-scoped test selector for the qa-tester skill.

Uses the qa-tester skill's deterministic §5.2 file mapping
({Project}/{Sub}/{Name}.cs -> {Project}.Tests/{Sub}/{Name}Tests.cs)
and §5.3 @under-test headers to produce:

  Default (no flags):  coverage gap report — MISSING / ORPHAN / OK per product file.
  --affected <range>:  git-diff impact analysis — which tests to run for changed files.

All arguments are optional. Auto-discovers {Project} + {Project}.Tests pair
from the current directory or the nearest ancestor that contains both.

Examples:
  python test_map.py                       # coverage check from repo root
  python test_map.py --affected HEAD~1     # impact analysis for last commit
  python test_map.py --affected main..HEAD --json   # JSON for AI consumption
  python test_map.py --product CoreProjector --tests CoreProjector.Tests
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

# -- Auto-discover ------------------------------------------------------------

def find_project_pair(start: Path) -> tuple[Path, Path] | None:
    """Walk up from start looking for sibling {Name} + {Name}.Tests folders."""
    d = start.resolve()
    while True:
        for child in sorted(d.iterdir()) if d.is_dir() else []:
            if child.is_dir() and (d / f"{child.name}.Tests").is_dir():
                return child, d / f"{child.name}.Tests"
        parent = d.parent
        if parent == d:
            break
        d = parent
    return None

# -- Helpers ------------------------------------------------------------------

def cs_files(root: Path) -> list[str]:
    """All .cs files under root, relative, excluding bin/obj."""
    out = []
    for p in root.rglob("*.cs"):
        rel = str(p.relative_to(root))
        if "bin" + os.sep in rel or "obj" + os.sep in rel:
            continue
        out.append(rel)
    return sorted(out)

def expected_test_path(product_rel: str) -> str:
    """§5.2 transform: {Sub}/{Name}.cs -> {Sub}/{Name}Tests.cs"""
    stem = Path(product_rel).stem
    parent = str(Path(product_rel).parent)
    ext = Path(product_rel).suffix
    name = f"{stem}Tests{ext}"
    return str(Path(parent) / name) if parent != "." else name

def read_under_test(filepath: Path) -> list[str]:
    """Read @under-test header from the first 5 lines of a test file."""
    try:
        with open(filepath, encoding="utf-8-sig", errors="replace") as f:
            for _, line in zip(range(5), f):
                m = re.search(r"@under-test:\s*(.+)", line)
                if m:
                    return [s.strip() for s in m.group(1).split(",")]
    except OSError:
        pass
    return []

def extract_type_names(filepath: Path) -> list[str]:
    """Extract class/interface/record/struct/enum names from a .cs file."""
    try:
        text = filepath.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return []
    return sorted(set(m.group(1) for m in re.finditer(
        r"(?:class|interface|record|struct|enum)\s+(\w+)", text)))

def grep_type_in_project(type_name: str, project_root: Path, exclude: set[str]) -> list[str]:
    """Find .cs files under project_root that contain type_name as a whole word."""
    hits = []
    pattern = re.compile(rf"\b{re.escape(type_name)}\b")
    for p in project_root.rglob("*.cs"):
        rel = str(p.relative_to(project_root))
        if "bin" + os.sep in rel or "obj" + os.sep in rel:
            continue
        if rel in exclude:
            continue
        try:
            text = p.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        if pattern.search(text):
            hits.append(rel)
    return hits

# -- Coverage Check -----------------------------------------------------------

def coverage_check(product: Path, tests: Path, as_json: bool):
    product_files = cs_files(product)
    test_files_set = {f.lower() for f in cs_files(tests)}
    rows = []

    for pf in product_files:
        expected = expected_test_path(pf)
        exists = expected.lower() in test_files_set
        header_ok = False
        status = "MISSING"
        if exists:
            headers = read_under_test(tests / expected)
            pf_name = Path(pf).name
            header_ok = any(pf_name in h for h in headers)
            status = "OK" if header_ok else "WRONG_HEADER"
        rows.append({"productFile": pf, "expectedTestFile": expected,
                      "testExists": exists, "headerCorrect": header_ok, "status": status})

    # Orphan detection
    for tf in cs_files(tests):
        headers = read_under_test(tests / tf)
        if any("(infrastructure" in h for h in headers):
            continue
        stem = Path(tf).stem
        if not stem.endswith("Tests"):
            continue
        orig_stem = stem[:-5]  # strip "Tests"
        orig_name = f"{orig_stem}{Path(tf).suffix}"
        parent = str(Path(tf).parent)
        expected_product = str(Path(parent) / orig_name) if parent != "." else orig_name
        if expected_product.lower() not in {pf.lower() for pf in product_files}:
            product_name = product.name
            refs_product = any(product_name in h for h in headers)
            if not refs_product and not headers:
                rows.append({"productFile": "(none)", "expectedTestFile": tf,
                              "testExists": True, "headerCorrect": False, "status": "ORPHAN"})

    total = sum(1 for r in rows if r["status"] != "ORPHAN")
    ok = sum(1 for r in rows if r["status"] == "OK")
    missing = sum(1 for r in rows if r["status"] == "MISSING")
    wrong = sum(1 for r in rows if r["status"] == "WRONG_HEADER")
    orphan = sum(1 for r in rows if r["status"] == "ORPHAN")
    coverage = round((ok / max(total, 1)) * 100, 1)

    if as_json:
        print(json.dumps({"product": product.name, "tests": tests.name,
                           "summary": {"total": total, "ok": ok, "missing": missing,
                                       "wrongHeader": wrong, "orphan": orphan},
                           "coverage": coverage, "rows": rows}, indent=2))
    else:
        print(f"\nCoverage: {product.name} -> {tests.name}")
        print("-" * 55)
        colors = {"OK": "\033[32m", "MISSING": "\033[31m",
                  "WRONG_HEADER": "\033[33m", "ORPHAN": "\033[33m"}
        reset = "\033[0m"
        for r in sorted(rows, key=lambda x: (x["status"], x["productFile"])):
            c = colors.get(r["status"], "")
            f = r["expectedTestFile"] if r["status"] == "ORPHAN" else r["productFile"]
            print(f"  {c}{r['status']:13s} {f}{reset}")
        print(f"\n  OK: {ok}/{total}   Missing: {missing}   Wrong header: {wrong}   Orphan: {orphan}")
        pct_color = "\033[32m" if coverage >= 80 else "\033[33m" if coverage >= 50 else "\033[31m"
        print(f"  {pct_color}Coverage: {coverage}%{reset}\n")

# -- Impact Analysis ----------------------------------------------------------

def impact_analysis(product: Path, tests: Path, git_range: str, depth: int, as_json: bool):
    # Step 1: git diff -> directly changed product files
    repo_root = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True, stderr=subprocess.DEVNULL).strip()
    product_rel = str(product.resolve().relative_to(Path(repo_root).resolve())).replace("\\", "/")

    diff_output = subprocess.check_output(
        ["git", "diff", "--name-only", git_range], text=True, stderr=subprocess.DEVNULL)
    diff_files = [
        line[len(product_rel) + 1:].replace("/", os.sep)
        for line in diff_output.strip().splitlines()
        if line.startswith(product_rel + "/")
    ]
    if not diff_files:
        print(f"No product files changed in '{git_range}' range.")
        return

    # Step 2: transitive dependents via type-name grep
    affected = set(diff_files)
    frontier = list(diff_files)
    for level in range(depth):
        next_frontier = []
        for f in frontier:
            full = product / f
            if not full.exists():
                continue
            for type_name in extract_type_names(full):
                for hit in grep_type_in_project(type_name, product, affected):
                    affected.add(hit)
                    next_frontier.append(hit)
        frontier = next_frontier

    # Step 3: map affected -> test files via §5.2 + @under-test grep
    affected_tests: set[str] = set()
    for af in affected:
        expected = expected_test_path(af)
        if (tests / expected).exists():
            affected_tests.add(expected)

    # Crosscutting tests via @under-test header
    for af in affected:
        af_name = Path(af).name
        for tf_path in tests.rglob("*.cs"):
            rel = str(tf_path.relative_to(tests))
            if "bin" + os.sep in rel or "obj" + os.sep in rel:
                continue
            headers = read_under_test(tf_path)
            if any(af_name in h for h in headers):
                affected_tests.add(rel)

    # Step 4: build filter string
    class_names = sorted({Path(t).stem for t in affected_tests})
    filter_parts = [f"FullyQualifiedName~{c}" for c in class_names] + ["TestCategory=critical"]
    filter_string = "|".join(filter_parts)

    if as_json:
        print(json.dumps({
            "gitRange": git_range,
            "directChanges": diff_files,
            "transitiveDepth": depth,
            "allAffectedFiles": sorted(affected),
            "affectedTests": sorted(affected_tests),
            "filterString": filter_string,
            "note": "AI should review allAffectedFiles and use find_references for shared types to catch dependents string-grep missed."
        }, indent=2))
    else:
        print(f"\nImpact analysis: {git_range} -> {product.name}")
        print("-" * 55)
        print("  Direct changes:")
        for f in diff_files:
            print(f"    \033[33m{f}\033[0m")
        transitive = sorted(affected - set(diff_files))
        if transitive:
            print(f"  Transitive dependents (depth {depth}):")
            for f in transitive:
                print(f"    \033[33m{f}\033[0m")
        print(f"\n  Tests to run ({len(affected_tests)}):")
        for t in sorted(affected_tests):
            print(f"    \033[32m{t}\033[0m")
        print(f"\n  Filter:\n    \033[36mdotnet test --filter \"{filter_string}\"\033[0m\n")

# -- Main ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Coverage mirror checker and impact-scoped test selector (qa-tester §5.5).")
    parser.add_argument("--product", help="Product project folder (auto-discovered if omitted)")
    parser.add_argument("--tests", help="Test project folder (auto-discovered if omitted)")
    parser.add_argument("--affected", metavar="GIT_RANGE",
                        help="Git diff range (e.g. HEAD~1, main..HEAD). Switches to impact analysis mode.")
    parser.add_argument("--depth", type=int, default=2,
                        help="Levels of transitive dependent chasing (default: 2)")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of human-readable table")
    args = parser.parse_args()

    product = Path(args.product) if args.product else None
    tests = Path(args.tests) if args.tests else None

    if not product or not tests:
        pair = find_project_pair(Path.cwd())
        if not pair:
            print("Error: could not auto-discover {Project} + {Project}.Tests pair.", file=sys.stderr)
            print("Use --product and --tests explicitly.", file=sys.stderr)
            sys.exit(1)
        if not product:
            product = pair[0]
        if not tests:
            tests = pair[1]

    product = product.resolve()
    tests = tests.resolve()

    if args.affected:
        impact_analysis(product, tests, args.affected, args.depth, args.json)
    else:
        coverage_check(product, tests, args.json)

if __name__ == "__main__":
    main()
