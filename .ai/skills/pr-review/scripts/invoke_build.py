#!/usr/bin/env python3
"""Cross-platform build wrapper for .NET solutions and projects.

Locates and invokes MSBuild or dotnet build to compile solutions/projects.

Build strategy:
  1. On Windows with Visual Studio installed: uses full MSBuild via vswhere
     (better for mixed SDK + .NET Framework multi-targeting solutions).
  2. Everywhere else (or if VS not found): uses 'dotnet msbuild' which ships
     with the .NET SDK and works on Windows, macOS, and Linux.
  3. Fallback: 'dotnet build' if 'dotnet msbuild' is unavailable.

Usage:
    python invoke_build.py <solution_or_project> [msbuild_args...]
    python invoke_build.py MyApp.sln /v:minimal /clp:Summary
    python invoke_build.py MyProject.csproj /p:Configuration=Release /t:Rebuild
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repo_case import normalize_solution


def find_msbuild_via_vswhere():
    """Locate MSBuild on Windows using vswhere.exe.

    Returns:
        Path to MSBuild.exe or None if not found.
    """
    if os.name != "nt":
        return None

    vswhere = Path(os.environ.get("ProgramFiles(x86)", "")) / \
        "Microsoft Visual Studio" / "Installer" / "vswhere.exe"

    if not vswhere.is_file():
        return None

    try:
        result = subprocess.run(
            [str(vswhere), "-latest", "-requires", "Microsoft.Component.MSBuild",
             "-find", "MSBuild\\**\\Bin\\MSBuild.exe"],
            capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            msbuild = result.stdout.strip().splitlines()[0]
            if Path(msbuild).is_file():
                return msbuild
    except OSError:
        pass

    return None


def find_dotnet():
    """Check if 'dotnet' CLI is available on PATH.

    Returns:
        Path to dotnet or None.
    """
    return shutil.which("dotnet")


def main():
    if len(sys.argv) < 2:
        print("Usage: python invoke_build.py <solution_or_project> [msbuild_args...]")
        print()
        print("Examples:")
        print("  python invoke_build.py MyApp.sln /v:minimal /clp:Summary")
        print("  python invoke_build.py MyProject.csproj /p:Configuration=Release /t:Rebuild")
        sys.exit(1)

    build_args = sys.argv[1:]

    project_or_solution = Path(build_args[0]).resolve()
    if not project_or_solution.exists():
        print(f"ERROR: Project or solution file does not exist: {project_or_solution}", file=sys.stderr)
        sys.exit(1)

    # Prefer the modern XML solution format (.slnx) over the legacy INI format
    # (.sln) when both exist side-by-side with the same stem. Repos in the
    # middle of migrating typically commit both and keep the .slnx as the
    # source of truth; building the .sln in that state risks picking up a
    # stale project list. The AI agent doesn't always know which file is
    # authoritative — picking automatically here makes its choice robust.
    if project_or_solution.suffix.lower() == ".sln":
        sibling_slnx = project_or_solution.with_suffix(".slnx")
        if sibling_slnx.is_file():
            print(f"Preferring {sibling_slnx.name} over {project_or_solution.name} "
                  "(both formats present; .slnx is the modern source of truth).")
            project_or_solution = sibling_slnx

    build_args[0] = str(project_or_solution)

    # Linux build of a Windows-authored solution frequently fails because the
    # .sln/.slnx records project paths in the Windows-author's casing while
    # the on-disk files end up in different casing on case-sensitive
    # filesystems. _repo_case.normalize_solution walks the project graph and
    # REWRITES recorded paths in the clone so they match the on-disk casing
    # exactly. (s04_fetch_repository.py runs the same pass after clone for
    # other build entry points; this here is a safety net.) The clone is
    # disposable — `.tmp/pr-review/branch/...` for PR review — so rewrites
    # never travel back to origin.
    if os.name != "nt" and project_or_solution.suffix.lower() in (".sln", ".slnx", ".csproj", ".vbproj", ".fsproj"):
        try:
            rewrites = normalize_solution(project_or_solution, verbose=True)
            if rewrites:
                files_changed = sorted({r[0] for r in rewrites})
                print(
                    f"Case-normalised {len(rewrites)} reference(s) across "
                    f"{len(files_changed)} file(s) in the clone."
                )
        except Exception as exc:
            print(f"WARNING: case-normalization preflight failed: {exc}", file=sys.stderr)

    # Strategy 1: Full MSBuild via vswhere (Windows only)
    msbuild_path = find_msbuild_via_vswhere()
    if msbuild_path:
        print(f"Using MSBuild: {msbuild_path}")
        result = subprocess.run([msbuild_path] + build_args)
        sys.exit(result.returncode)

    # Strategy 2: dotnet msbuild (cross-platform)
    dotnet_path = find_dotnet()
    if dotnet_path:
        print(f"Using dotnet msbuild: {dotnet_path}")
        result = subprocess.run([dotnet_path, "msbuild"] + build_args)
        if result.returncode == 0:
            sys.exit(0)

        # Strategy 3: Fallback to dotnet build
        print("dotnet msbuild failed; falling back to dotnet build...")
        result = subprocess.run([dotnet_path, "build"] + build_args)
        sys.exit(result.returncode)

    print("ERROR: No build tool found. Install either:", file=sys.stderr)
    print("  - .NET SDK (provides 'dotnet msbuild' and 'dotnet build')", file=sys.stderr)
    print("  - Visual Studio with MSBuild component (Windows)", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
