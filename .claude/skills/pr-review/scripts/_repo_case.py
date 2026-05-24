"""Rewrite case-mismatched project paths in .sln/.slnx/.csproj checkouts.

Windows is case-insensitive; Linux is not. Repos authored on Windows
frequently end up with a `.sln` that says `Web.Core/Web.Core.csproj` but
an on-disk file at `Web.Core/web.core.csproj` (or even
`web.core/web.core.csproj`). On Linux, MSBuild refuses to load such a
solution.

The previous version of this module tried to fix that with symlinks
(`web.core/web.core.csproj` -> `Web.Core/web.core.csproj`). That
approach kept failing in real reviews, because path resolution inside
MSBuild / NuGet doesn't behave consistently when a project is loaded
through a symlinked path. This version takes the boring, reliable
approach: walk the solution/project graph, find every recorded path
whose casing doesn't match disk, and rewrite the file in place so the
recorded path matches disk exactly.

Important properties:

  * The clone is disposable — `.tmp/pr-review/branch/...` for PR review,
    likewise for code-work-item runs. Rewrites never travel back to
    origin and are wiped on the next `s01_reset_workspace.py --keep-repo`
    when the branch folder is excluded, or by re-clone when it isn't.
  * Rewrites are line-based string substitution against the regex match
    span. No XML/INI re-serialisation, so we don't reflow whitespace,
    BOMs, line endings, comments, or attribute order. The diff is the
    minimum needed for the build to succeed.
  * Resolution is segment-by-segment with case-insensitive fallback,
    matching how an operator would manually fix this in VS Code.

Two entry points:

  normalize_solution(path)
      Walk one .sln / .slnx / .csproj (and transitively the projects it
      references). Used by invoke_build.py as the safety net for the
      specific solution about to be built.

  normalize_repo(repo_root)
      Find every top-level .sln/.slnx under repo_root and call
      normalize_solution on each. Used by s04_fetch_repository.py so
      that downstream commands (dotnet restore, dotnet build, etc.)
      see a self-consistent checkout.

Both are no-ops on Windows.

Run as a script (`python3 _repo_case.py /path/to/repo`) for ad-hoc
verification — it prints every rewrite it makes plus a final tally.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# .sln (INI-style): Project("{GUID}") = "Name", "rel/Path.csproj", "{GUID}"
# Capture group 1 = path; capture-group span lets us rewrite in place.
_SLN_PROJECT_RE = re.compile(
    r'(?<=^Project\("\{)(?P<guid>[^}]+)(?=\}"\))(?P<between1>"\)\s*=\s*"[^"]*"\s*,\s*")(?P<path>[^"]+)',
    re.MULTILINE,
)
# Simpler: locate the third quoted field. Anchored on `Project(...) = "...",`
_SLN_PROJECT_REWRITE_RE = re.compile(
    r'(^Project\("\{[^}]+\}"\)\s*=\s*"[^"]*"\s*,\s*")([^"]+)(")',
    re.MULTILINE,
)
# .slnx (XML): <Project Path="rel/Path.csproj" /> — captures the path attr.
_SLNX_PROJECT_REWRITE_RE = re.compile(
    r'(<Project\s+[^>]*?Path\s*=\s*")([^"]+)(")',
    re.IGNORECASE,
)
# .csproj/.vbproj/.fsproj: <ProjectReference Include="..\rel\Path.csproj" />
_PROJREF_REWRITE_RE = re.compile(
    r'(<ProjectReference\s+[^>]*?Include\s*=\s*")([^"]+)(")',
    re.IGNORECASE,
)

_PROJECT_FILE_SUFFIXES = (".csproj", ".vbproj", ".fsproj")
_SOLUTION_FILE_SUFFIXES = (".sln", ".slnx")
_REWRITABLE_SUFFIXES = _SOLUTION_FILE_SUFFIXES + _PROJECT_FILE_SUFFIXES


def _rewrite_regex_for(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".sln":
        return _SLN_PROJECT_REWRITE_RE
    if suffix == ".slnx":
        return _SLNX_PROJECT_REWRITE_RE
    if suffix in _PROJECT_FILE_SUFFIXES:
        return _PROJREF_REWRITE_RE
    return None


def _split_recorded(rel: str) -> list[str]:
    """Split a recorded path into segments, handling both separators."""
    # Pathlib mishandles `..\..\foo` on POSIX; normalise to '/' first.
    normalised = rel.replace("\\", "/")
    return [seg for seg in normalised.split("/") if seg != ""]


def _find_on_disk(owner_dir: Path, rel: str) -> Path | None:
    """Walk the recorded `rel` from `owner_dir` segment-by-segment.

    At each segment, prefer an exact-case child; fall back to a unique
    case-insensitive sibling. Returns the real on-disk Path, or None
    when any segment has no case-insensitive match (genuinely missing
    project, not a case bug).
    """
    current = owner_dir.resolve()
    if not current.is_dir():
        return None
    for segment in _split_recorded(rel):
        if segment == "..":
            current = current.parent
            continue
        if segment == ".":
            continue
        exact = current / segment
        if exact.exists():
            current = exact
            continue
        try:
            siblings = list(current.iterdir())
        except OSError:
            return None
        matched = None
        for entry in siblings:
            if entry.name.lower() == segment.lower():
                matched = entry
                break
        if matched is None:
            return None
        current = matched
    return current


def _disk_relative(owner_dir: Path, target: Path) -> str:
    """Format `target` relative to `owner_dir` using `..` segments, with
    OS-appropriate separators. .sln files use `\\`; .slnx and project
    files use either, but `\\` is the dominant convention from Windows
    authors so we preserve that for `.sln`. For `.slnx` and project
    files we keep `/` since those are XML and authors usually use `/`.
    """
    # Walk up from owner_dir until we share a common parent with target.
    owner_parts = owner_dir.resolve().parts
    target_parts = target.resolve().parts
    common = 0
    for o, t in zip(owner_parts, target_parts):
        if o != t:
            break
        common += 1
    ups = [".."] * (len(owner_parts) - common)
    downs = list(target_parts[common:])
    return "/".join(ups + downs)


def _format_for_owner(owner: Path, rel_disk: str, original_separator_hint: str) -> str:
    """Re-apply backslashes if the original recorded path used them.

    Mixing slashes inside the same file would look like a churn diff on
    review. We preserve whichever separator the original entry used.
    """
    if "\\" in original_separator_hint and owner.suffix.lower() == ".sln":
        return rel_disk.replace("/", "\\")
    if "\\" in original_separator_hint:
        # .slnx / .csproj — keep author's chosen separator.
        return rel_disk.replace("/", "\\")
    return rel_disk


def _iter_recorded(text: str, regex: re.Pattern) -> list[tuple[int, int, str, str, str]]:
    """Yield (path_start, path_end, prefix, recorded_path, suffix) for each match."""
    out: list[tuple[int, int, str, str, str]] = []
    for m in regex.finditer(text):
        # All three regexes use three capture groups: (prefix, path, suffix).
        prefix, recorded, suffix = m.group(1), m.group(2), m.group(3)
        path_start = m.start(2)
        path_end = m.end(2)
        out.append((path_start, path_end, prefix, recorded, suffix))
    return out


def _process_file(
    owner: Path,
    visited: set[Path],
    queue: list[Path],
    rewrites: list[tuple[str, str, str]],
    verbose: bool,
) -> None:
    """Rewrite `owner` in place so every recorded reference matches disk.

    Walks each reference to find its on-disk counterpart. When the
    recorded path differs (case or layout), rewrites just that path in
    the file. Always queues the on-disk target for further processing
    so the walk reaches every transitive .csproj.
    """
    regex = _rewrite_regex_for(owner)
    if regex is None:
        return

    try:
        text = owner.read_text(encoding="utf-8-sig", errors="replace")
    except OSError as exc:
        if verbose:
            print(f"  WARNING: could not read {owner}: {exc}", file=sys.stderr)
        return

    owner_dir = owner.parent
    new_text_parts: list[str] = []
    cursor = 0
    file_rewrites: list[tuple[str, str]] = []

    for path_start, path_end, _prefix, recorded, _suffix in _iter_recorded(text, regex):
        target = _find_on_disk(owner_dir, recorded)
        if target is None:
            if verbose:
                print(
                    f"  {owner.name}: '{recorded}' -> NOT FOUND (genuinely missing, not a case bug)",
                    file=sys.stderr,
                )
            continue
        disk_rel = _disk_relative(owner_dir, target)
        recorded_for_compare = recorded.replace("\\", "/")
        disk_for_compare = disk_rel  # already '/'-separated
        if recorded_for_compare == disk_for_compare:
            # Already correct casing — nothing to rewrite.
            if target.is_file():
                queue.append(target)
            if verbose:
                print(f"  {owner.name}: '{recorded}' OK")
            continue

        replacement = _format_for_owner(owner, disk_rel, recorded)
        new_text_parts.append(text[cursor:path_start])
        new_text_parts.append(replacement)
        cursor = path_end
        file_rewrites.append((recorded, replacement))
        if verbose:
            print(f"  {owner.name}: '{recorded}' -> '{replacement}'")
        if target.is_file():
            queue.append(target)

    if not file_rewrites:
        return

    new_text_parts.append(text[cursor:])
    new_text = "".join(new_text_parts)

    if new_text == text:
        # Belt-and-braces: shouldn't happen if file_rewrites was populated.
        return

    try:
        owner.write_text(new_text, encoding="utf-8")
    except OSError as exc:
        print(f"  WARNING: failed to rewrite {owner}: {exc}", file=sys.stderr)
        return

    for old, new in file_rewrites:
        rewrites.append((str(owner), old, new))

    visited.add(owner.resolve())


def normalize_solution(path, *, verbose: bool = True) -> list[tuple[str, str, str]]:
    """Rewrite case-mismatched references reachable from `path`.

    Walks the .sln/.slnx and transitively into each .csproj's
    ProjectReferences. Returns list of (file, old_path, new_path) tuples
    for every rewrite applied. No-op on Windows.
    """
    if os.name == "nt":
        return []
    start = Path(path).resolve()
    if not start.is_file() or start.suffix.lower() not in _REWRITABLE_SUFFIXES:
        return []

    visited: set[Path] = {start.resolve()}
    queue: list[Path] = [start]
    rewrites: list[tuple[str, str, str]] = []

    if verbose:
        print(f"Case-normalising {start.name} (and transitively-referenced projects)…", file=sys.stderr)

    while queue:
        owner = queue.pop()
        resolved = owner.resolve()
        if resolved != owner.resolve():  # paranoia: shouldn't ever differ
            owner = resolved
        if owner != start and owner.resolve() in visited:
            continue
        visited.add(owner.resolve())
        _process_file(owner, visited, queue, rewrites, verbose)

    if verbose:
        if rewrites:
            print(
                f"Rewrote {len(rewrites)} case-mismatched reference(s) across "
                f"{len({r[0] for r in rewrites})} file(s) in the clone.",
                file=sys.stderr,
            )
        else:
            print("No case-mismatched references found.", file=sys.stderr)

    return rewrites


def normalize_repo(repo_root, *, verbose: bool = True) -> list[tuple[str, str, str]]:
    """Find every top-level .sln/.slnx under repo_root and normalise each.

    "Top-level" means at most 4 directory levels deep — enough for
    typical layouts without scanning node_modules, obj/, bin/, etc.
    """
    if os.name == "nt":
        return []
    repo_root = Path(repo_root).resolve()
    if not repo_root.is_dir():
        return []

    skip_dirs = {".git", "node_modules", "bin", "obj", ".vs", ".idea", ".tmp"}
    all_rewrites: list[tuple[str, str, str]] = []
    seen: set[Path] = set()

    def walk(dir_path: Path, depth: int):
        if depth > 4:
            return
        try:
            entries = list(dir_path.iterdir())
        except OSError:
            return
        for entry in entries:
            if entry.is_dir():
                if entry.name in skip_dirs or entry.name.startswith("."):
                    continue
                walk(entry, depth + 1)
            elif entry.is_file() and entry.suffix.lower() in _SOLUTION_FILE_SUFFIXES:
                resolved = entry.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                all_rewrites.extend(normalize_solution(resolved, verbose=verbose))

    walk(repo_root, 0)
    return all_rewrites


# Backwards-compat aliases — earlier code in this skill used these names.
def normalize_solution_case(path):
    return normalize_solution(path, verbose=True)


def normalize_repo_case(repo_root):
    return normalize_repo(repo_root, verbose=True)


def _format_summary(rewrites: list[tuple[str, str, str]]) -> str:
    if not rewrites:
        return "No case-mismatched references found."
    lines = [f"Rewrote {len(rewrites)} reference(s):"]
    for file, old, new in rewrites:
        lines.append(f"  {file}: '{old}' -> '{new}'")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python _repo_case.py <repo_root_or_solution_path>")
        sys.exit(1)
    target = Path(sys.argv[1]).resolve()
    if target.is_dir():
        result = normalize_repo(target, verbose=True)
    else:
        result = normalize_solution(target, verbose=True)
    print(_format_summary(result))
