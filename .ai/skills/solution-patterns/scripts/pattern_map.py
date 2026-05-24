#!/usr/bin/env python3
"""Generate `.ai/solution-patterns.csv` — the Code | UI | Test table.

Part of the solution-patterns skill. Zero required arguments — auto-discovers
the repo root and reads `.ai/solution-patterns.instructions.md` for per-project
overrides. Writes deterministic CSV output (sorted rows, stable column order,
UTF-8, LF line endings) safe to commit.

Columns (the contract — do not rename or reorder):
  CodePath, Role, ExpectedUiPath, ActualUiPath,
  ExpectedTestPath, ActualTestPath, Deviation, Notes

Examples:
  python pattern_map.py                       # full scan, writes .ai/solution-patterns.csv
  python pattern_map.py --dry-run             # preview rows without writing
  python pattern_map.py --affected path1,p2   # refresh only rows under given paths
  python pattern_map.py --json                # full result as JSON (stdout)
"""
import argparse, csv, io, json, os, re, sys
from pathlib import Path

import detect_stack

# Column order is a contract. Never rename/reorder without bumping skill §4.
COLUMNS = ["CodePath", "Role", "ExpectedUiPath", "ActualUiPath",
           "ExpectedTestPath", "ActualTestPath", "Deviation", "Notes"]

SKIP_DIRS = detect_stack.SKIP_DIRS

# -- File walking -------------------------------------------------------------

def walk_code(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    """List files under root matching any suffix, skipping SKIP_DIRS and test-project dirs."""
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS
                       and not d.startswith(".")
                       and not d.endswith(".Tests")]
        for f in filenames:
            if f.endswith(suffixes):
                out.append(Path(dirpath) / f)
    return out

def walk_tests(root: Path) -> list[Path]:
    """List files under any *.Tests folder."""
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        parts = Path(dirpath).relative_to(root).parts if Path(dirpath) != root else ()
        if not any(p.endswith(".Tests") for p in parts):
            continue
        for f in filenames:
            if f.endswith((".cs", ".ts", ".tsx", ".js", ".jsx")):
                out.append(Path(dirpath) / f)
    return out

def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""

def rel_posix(p: Path, root: Path) -> str:
    return str(p.relative_to(root)).replace("\\", "/")

# -- Role inference -----------------------------------------------------------

def infer_role(rel: str, stacks: set[str]) -> str | None:
    """Map a repo-relative file path to a Role. Returns None for files we skip."""
    name = Path(rel).name
    stem = Path(rel).stem
    suffix = Path(rel).suffix.lower()
    parts = [p.lower() for p in Path(rel).parts]

    # WPF / WinUI / WinForms (C# + XAML)
    if "wpf" in stacks or "winui" in stacks or "winforms" in stacks:
        if suffix == ".xaml":
            if name == "App.xaml":
                return "bootstrap"
            if name == "MainWindow.xaml" or stem.endswith(("Shell",)):
                return "shell"
            # ResourceDictionary / themes / resources — not a UI view.
            if "themes" in parts or "resources" in parts:
                return "resource"
            return "ui-view"
        if suffix == ".cs":
            if name.endswith(".xaml.cs"):
                return "code-behind"
            if name == "App.xaml.cs" or name == "Program.cs":
                return "bootstrap"
            if stem.endswith("ViewModel"):
                return "view-model"
            if stem.endswith("Converter"):
                return "converter"
            if stem.endswith("Behavior"):
                return "behavior"

    # ASP.NET Core
    if "aspnet-core" in stacks and suffix == ".cs":
        if stem.endswith("Controller"):
            return "controller"
        if "/pages/" in "/" + "/".join(parts) and name.endswith(".cshtml.cs"):
            return "page-model"
        if name == "Program.cs":
            return "bootstrap"
    if "aspnet-core" in stacks and suffix == ".cshtml":
        if stem.startswith("_"):
            return "layout"
        return "page"

    # Common C# service-layer heuristics (apply when any .NET stack is present)
    dotnet_stacks = {"wpf", "winui", "winforms", "aspnet-core"}
    if dotnet_stacks & stacks and suffix == ".cs":
        if stem.endswith("Service"):
            return "service"
        if stem.endswith("Repository"):
            return "repository"
        if stem.endswith("Middleware"):
            return "middleware"

    # Angular
    if "angular" in stacks:
        if rel.endswith(".component.ts"):
            return "ui-view"
        if rel.endswith(".component.html"):
            return "template"
        if rel.endswith((".component.scss", ".component.css")):
            return "style"
        if rel.endswith(".service.ts"):
            return "service"
        if rel.endswith(".module.ts"):
            return "module"
        if rel.endswith(".pipe.ts"):
            return "pipe"
        if rel.endswith(".directive.ts"):
            return "directive"
        if re.search(r"[./-]guard\.ts$", rel):
            return "guard"
        if re.search(r"[./-]resolver\.ts$", rel):
            return "resolver"
        if re.search(r"[./-]interceptor\.ts$", rel):
            return "interceptor"
        if rel.endswith(".spec.ts"):
            return "test"

    # Next.js (App Router + Pages Router)
    if "nextjs" in stacks:
        base = Path(rel).name
        if base in ("page.tsx", "page.jsx", "page.js"):
            return "ui-view"
        if base in ("layout.tsx", "layout.jsx"):
            return "layout"
        if base in ("route.ts", "route.js"):
            return "endpoint"
        if base in ("loading.tsx", "loading.jsx"):
            return "loading-ui"
        if base in ("error.tsx", "global-error.tsx"):
            return "error-boundary"
        if "/pages/" in "/" + "/".join(parts) and suffix in (".tsx", ".jsx", ".js", ".ts"):
            if base.startswith("_"):
                return None
            if "/pages/api/" in "/" + "/".join(parts):
                return "endpoint"
            return "ui-view"
        if rel.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx")):
            return "test"

    return None

# -- Expected UI path ---------------------------------------------------------

def expected_ui_path(rel: str, role: str, stacks: set[str]) -> str:
    """Derive the expected UI path (URL for web, 'Shell > Breadcrumb' for desktop)."""
    parts = Path(rel).parts
    stem = Path(rel).stem
    lower_parts = [p.lower() for p in parts]

    # Next.js: folder = route by framework contract
    if "nextjs" in stacks and role in ("ui-view", "layout", "endpoint", "loading-ui", "error-boundary"):
        # Find the app/ or pages/ anchor.
        anchor = None
        for i, p in enumerate(lower_parts):
            if p in ("app", "pages"):
                anchor = i
                break
        if anchor is None:
            return ""
        segments = []
        for p in parts[anchor + 1:-1]:  # skip the file itself
            if p.startswith("(") and p.endswith(")"):
                continue  # route group
            if p.startswith("@"):
                continue  # parallel slot
            p2 = p
            if p2.startswith("[[...") and p2.endswith("]]"):
                p2 = ":" + p2[5:-2] + "?"
            elif p2.startswith("[...") and p2.endswith("]"):
                p2 = ":" + p2[4:-1] + "*"
            elif p2.startswith("[") and p2.endswith("]"):
                p2 = ":" + p2[1:-1]
            segments.append(p2)
        # Pages Router: the file stem itself is the last segment (unless index).
        if "pages" in lower_parts and role == "ui-view":
            if stem.lower() not in ("index",):
                s = stem
                if s.startswith("[[...") and s.endswith("]]"):
                    s = ":" + s[5:-2] + "?"
                elif s.startswith("[...") and s.endswith("]"):
                    s = ":" + s[4:-1] + "*"
                elif s.startswith("[") and s.endswith("]"):
                    s = ":" + s[1:-1]
                segments.append(s)
        return "/" + "/".join(segments) if segments else "/"

    # ASP.NET Core Razor Pages: Pages/{Area}/{Name}.cshtml -> /{Area}/{Name}
    if "aspnet-core" in stacks and role == "page":
        if "Pages" not in parts:
            return ""
        idx = parts.index("Pages")
        segments = list(parts[idx + 1:-1]) + ([stem] if stem.lower() != "index" else [])
        # Areas handling: Areas/{Area}/Pages/... -> /{Area}/...
        if "Areas" in parts:
            ai = parts.index("Areas")
            if ai + 1 < len(parts):
                segments = [parts[ai + 1]] + segments
        return "/" + "/".join(segments) if segments else "/"

    # WPF / WinUI / WinForms: breadcrumb default = Shell > StemWithoutSuffix
    if role in ("ui-view",) and ({"wpf", "winui", "winforms"} & stacks):
        s = stem
        for suf in ("View", "Page", "Window", "Form", "Control", "Panel"):
            if s.endswith(suf) and len(s) > len(suf):
                s = s[:-len(suf)]
                break
        # If under Views/{Feature}/, include Feature in the breadcrumb.
        feature = ""
        if "Views" in parts:
            vi = parts.index("Views")
            if vi + 1 < len(parts) - 1:
                feature = parts[vi + 1]
        shell = "MainWindow"
        crumbs = [shell]
        if feature and feature.lower() != s.lower():
            crumbs.append(feature)
        crumbs.append(s)
        return " > ".join(crumbs)

    # Angular: folder-based guess (only a hint; actual path from routes file)
    if "angular" in stacks and role == "ui-view":
        # src/app/{feature}/{name}-page/{name}-page.component.ts
        app_idx = None
        for i, p in enumerate(lower_parts):
            if p == "app" and i > 0 and lower_parts[i - 1] == "src":
                app_idx = i
                break
        if app_idx is None:
            return ""
        rest = parts[app_idx + 1:-1]
        # Drop "features", "pages" wrappers if present.
        rest = [r for r in rest if r.lower() not in ("features", "pages")]
        if not rest:
            return "/"
        last = rest[-1]
        name = re.sub(r"-(page|component|view)$", "", last)
        rest = list(rest[:-1]) + [name]
        return "/" + "/".join(rest)

    return ""

# -- Expected test path (qa-tester §5.2) --------------------------------------

def expected_test_path(rel: str, role: str, projects: list[str]) -> str:
    """Mirror the code path into a sibling {Project}.Tests project or collocated spec.

    `projects` is the list of detected project-root prefixes (the folders that contain a
    .csproj or package.json). The function finds the *deepest* project prefix owning the
    file, so WorkspaceManager/Core/Services/Foo.cs mirrors to WorkspaceManager/Core.Tests/
    Services/FooTests.cs, not WorkspaceManager.Tests/... .
    """
    p = Path(rel)
    stem = p.stem
    suffix = p.suffix
    parts = list(p.parts)

    # Skip: tests themselves, layouts, non-logic artifacts.
    if role in (None, "test", "style", "template", "resource",
                "layout", "designer-generated"):
        return ""

    # C#/XAML: find the deepest detected project prefix that owns this file.
    if suffix in (".cs", ".xaml", ".cshtml") and len(parts) >= 2:
        project = find_project_for(rel, projects)
        if not project:
            project = parts[0]  # fallback
        project_parts = Path(project).parts
        tests_project = str(Path(*project_parts[:-1]) / f"{project_parts[-1]}.Tests").replace("\\", "/") \
            if len(project_parts) > 1 else f"{project}.Tests"
        # For .xaml.cs, the test maps the xaml-level stem.
        base_stem = stem
        if rel.endswith(".xaml.cs"):
            base_stem = Path(rel[:-len(".xaml.cs")]).name
        test_name = f"{base_stem}Tests.cs"
        rest = parts[len(project_parts):-1]
        return "/".join([tests_project] + list(rest) + [test_name])

    # TypeScript/JavaScript: collocated .spec.{ext} sibling.
    if suffix in (".ts", ".tsx", ".js", ".jsx") and role != "test":
        sibling_stem = stem
        return "/".join(list(parts[:-1]) + [f"{sibling_stem}.spec{suffix}"])

    return ""

def find_project_for(rel: str, all_projects: list[str]) -> str | None:
    """Given a file path, return the project (top-level folder containing .csproj)
    the file belongs to. Uses the list of detected project-rooted paths."""
    for proj in sorted(all_projects, key=len, reverse=True):
        if rel.startswith(proj + "/"):
            return proj
    return None

# -- Actual test path lookup --------------------------------------------------

def read_under_test_header(p: Path) -> list[str]:
    """Read @under-test header (first 5 lines)."""
    try:
        with open(p, encoding="utf-8-sig", errors="replace") as f:
            for _, line in zip(range(5), f):
                m = re.search(r"@under-test:\s*(.+)", line)
                if m:
                    return [s.strip() for s in m.group(1).split(",")]
    except OSError:
        pass
    return []

def build_test_index(test_files: list[Path], root: Path) -> dict[str, list[str]]:
    """Map product-file basename or relpath -> list of test relpaths that claim it."""
    idx: dict[str, list[str]] = {}
    for tf in test_files:
        rel = rel_posix(tf, root)
        for header in read_under_test_header(tf):
            idx.setdefault(header, []).append(rel)
            idx.setdefault(Path(header).name, []).append(rel)
    return idx

# -- Overrides ----------------------------------------------------------------

def load_overrides(root: Path) -> dict:
    """Read .ai/solution-patterns.instructions.md — light parse of the Overrides section.
    v1: only collects a set of recognised override keys per stack; the AI agent is expected
    to read the human-written rationale. Empty dict if file absent."""
    p = root / ".ai" / "solution-patterns.instructions.md"
    if not p.exists():
        return {}
    txt = read_text(p)
    overrides: dict[str, list[str]] = {}
    current = None
    for line in txt.splitlines():
        if line.startswith("### "):
            current = line[4:].strip().lower()
            overrides.setdefault(current, [])
        elif current and line.strip().startswith("- `"):
            m = re.match(r"- `([^`]+)`", line.strip())
            if m:
                overrides[current].append(m.group(1))
    return overrides

# -- Row building -------------------------------------------------------------

def build_rows(root: Path, stacks: set[str], projects: list[str],
               overrides: dict) -> list[dict]:
    rows: list[dict] = []

    # Determine which suffixes we care about based on stacks.
    suffixes: list[str] = []
    if {"wpf", "winui", "winforms", "aspnet-core"} & stacks:
        suffixes += [".cs", ".xaml", ".cshtml"]
    if {"angular", "nextjs"} & stacks:
        suffixes += [".ts", ".tsx", ".js", ".jsx", ".html", ".scss", ".css"]
    suffixes_tuple = tuple(sorted(set(suffixes)))
    if not suffixes_tuple:
        return rows

    code_files = walk_code(root, suffixes_tuple)
    test_files = walk_tests(root)
    test_index = build_test_index(test_files, root)

    for p in code_files:
        rel = rel_posix(p, root)
        role = infer_role(rel, stacks)
        if role is None:
            continue

        expected_ui = expected_ui_path(rel, role, stacks)
        expected_test = expected_test_path(rel, role, projects)

        # ActualTestPath: start with the expected location if it exists,
        # then broaden via @under-test headers.
        actual_test_candidates: list[str] = []
        if expected_test and (root / expected_test).exists():
            actual_test_candidates.append(expected_test)
        for candidate in test_index.get(rel, []) + test_index.get(Path(rel).name, []):
            if candidate not in actual_test_candidates:
                actual_test_candidates.append(candidate)
        actual_test = ";".join(actual_test_candidates) if actual_test_candidates else ""

        # ActualUiPath: v1 only fills it for Next.js (folder = route by construction).
        actual_ui = expected_ui if "nextjs" in stacks and role in ("ui-view", "layout", "endpoint") else ""

        # Deviation:
        deviation = "none"
        if expected_test and not actual_test:
            deviation = "test-missing"
        elif actual_test and expected_test and expected_test not in actual_test.split(";"):
            deviation = "test-relocated"
        if expected_ui and actual_ui and expected_ui != actual_ui:
            deviation = "ui-mismatch"
        elif expected_ui and not actual_ui and role in ("ui-view", "page") and "nextjs" not in stacks:
            # For stacks where actual UI discovery is deferred to v2, leave deviation='none'
            # unless the code path itself looks suspect. Don't spam the report.
            pass

        # Notes seed
        notes = []
        if role == "ui-view" and ({"wpf", "winui", "winforms"} & stacks):
            stem = Path(rel).stem
            for suf in ("View", "Page", "Window", "Form", "Control", "Panel"):
                if stem.endswith(suf) and len(stem) > len(suf):
                    stem = stem[:-len(suf)]
                    break
            notes.append(f"AutomationId prefix = {stem}.")

        rows.append({
            "CodePath": rel,
            "Role": role,
            "ExpectedUiPath": expected_ui,
            "ActualUiPath": actual_ui,
            "ExpectedTestPath": expected_test,
            "ActualTestPath": actual_test,
            "Deviation": deviation,
            "Notes": "; ".join(notes),
        })

    rows.sort(key=lambda r: (r["CodePath"], r["Role"]))
    return rows

# -- CSV writing --------------------------------------------------------------

def write_csv(rows: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n",
                             quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in COLUMNS})
    out_path.write_text(buf.getvalue(), encoding="utf-8", newline="")

# -- Main ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate .ai/solution-patterns.csv (solution-patterns skill).")
    parser.add_argument("--root", help="Repo root (auto-discovered if omitted)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print summary without writing the CSV")
    parser.add_argument("--json", action="store_true",
                        help="Print full rows as JSON (implies --dry-run)")
    parser.add_argument("--affected", help="Comma-separated path prefixes; only refresh rows whose CodePath starts with one of these")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else detect_stack.find_repo_root(Path.cwd())

    stacks = {s: detect_stack.DETECTORS[s](root) for s in detect_stack.DETECTORS}
    active_stacks = {s for s, hits in stacks.items() if hits}

    if not active_stacks:
        print("No stacks detected. Nothing to do.", file=sys.stderr)
        sys.exit(0)

    projects: list[str] = []
    for hits in stacks.values():
        for h in hits:
            # .csproj / angular.json / package.json evidence lives in the project dir.
            ev = h.get("evidence", "")
            proj = str(Path(ev).parent).replace("\\", "/")
            if proj and proj != "." and proj not in projects:
                projects.append(proj)

    overrides = load_overrides(root)
    rows = build_rows(root, active_stacks, projects, overrides)

    if args.affected:
        prefixes = [p.strip().replace("\\", "/") for p in args.affected.split(",") if p.strip()]
        rows = [r for r in rows if any(r["CodePath"].startswith(pref) for pref in prefixes)]

    out_path = root / ".ai" / "solution-patterns.csv"

    if args.json:
        print(json.dumps({"root": str(root).replace("\\", "/"),
                          "stacks": sorted(active_stacks),
                          "rowCount": len(rows),
                          "outputPath": str(out_path.relative_to(root)).replace("\\", "/"),
                          "rows": rows}, indent=2))
        return

    if args.dry_run:
        print(f"\nsolution-patterns dry-run: {len(rows)} rows (stacks: {', '.join(sorted(active_stacks))})")
        by_role: dict[str, int] = {}
        by_dev: dict[str, int] = {}
        for r in rows:
            by_role[r["Role"]] = by_role.get(r["Role"], 0) + 1
            by_dev[r["Deviation"]] = by_dev.get(r["Deviation"], 0) + 1
        print("\n  Roles:", ", ".join(f"{k}={v}" for k, v in sorted(by_role.items())))
        print("  Deviations:", ", ".join(f"{k}={v}" for k, v in sorted(by_dev.items())))
        print()
        return

    write_csv(rows, out_path)
    print(f"\nWrote {len(rows)} rows to {out_path.relative_to(root)}")
    print(f"  Stacks: {', '.join(sorted(active_stacks))}")
    by_dev: dict[str, int] = {}
    for r in rows:
        by_dev[r["Deviation"]] = by_dev.get(r["Deviation"], 0) + 1
    print(f"  Deviations: {', '.join(f'{k}={v}' for k, v in sorted(by_dev.items()))}")
    print()

if __name__ == "__main__":
    main()
