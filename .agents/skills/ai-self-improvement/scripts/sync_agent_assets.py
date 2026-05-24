#!/usr/bin/env python3
"""Sync AI agent instruction files, skills, and custom agents from master sources under `.ai/`.

Agent definitions are loaded from `agents.json` next to this script's parent folder.

Usage:
    python sync_agent_assets.py [MODE] [--global] [--no-clear]

MODE:
    ALL         Update all known agent outputs
    AUTO        Update only agents detected in this repository
    <name>      Update a specific agent (e.g. "Claude Code", "roo-code")
    (omitted)   Interactive menu

Options:
    --global    Also sync global agents (.ai/.global/agents/) AND global skills
                (.ai/.global/skills/) to user-level paths. Skills are added/updated
                without purging — to remove a skill, list it in
                .ai/.global/removed-skills.json.
    --no-clear  Do not clear the console on start

Cross-platform: runs on Windows, macOS, Linux. Requires Python 3.8+.
"""
from __future__ import annotations

import argparse
import filecmp
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any

# ── Paths ────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SCRIPT_DIR.parents[3]
AI_DIR = REPO_ROOT / ".ai"
CONFIG_PATH = SKILL_DIR / "agents.json"

EXCLUDED_DIR_NAMES = {".git", ".vs", "bin", "obj"}


# ── Utility functions ────────────────────────────────────────────────────────

def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_text_auto(path: Path) -> str:
    """Read text with BOM auto-detection. Returns string without BOM."""
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8")
    if data.startswith(b"\xff\xfe"):
        return data[2:].decode("utf-16-le")
    if data.startswith(b"\xfe\xff"):
        return data[2:].decode("utf-16-be")
    return data.decode("utf-8")


def write_utf8_no_bom(path: Path, content: str) -> None:
    ensure_directory(path.parent)
    # Use binary write to guarantee no BOM and consistent newlines.
    path.write_bytes(content.encode("utf-8"))


def files_equal(a: Path, b: Path) -> bool:
    if not a.exists() or not b.exists():
        return False
    if a.stat().st_size != b.stat().st_size:
        return False
    return filecmp.cmp(str(a), str(b), shallow=False)


def copy_file_if_different(source: Path, target: Path) -> None:
    ensure_directory(target.parent)
    if not target.exists():
        shutil.copy2(source, target)
        print(f"Created: {target}")
        return
    if files_equal(source, target):
        print(f"Up-to-date: {target}")
        return
    shutil.copy2(source, target)
    print(f"Updated: {target}")


def assert_instruction_sync(source_dir: Path, target_dir: Path, source_files: list[Path]) -> None:
    for sf in source_files:
        src_path = source_dir / sf.name
        dst_path = target_dir / sf.name
        if not dst_path.is_file():
            raise RuntimeError(f"Binary comparison failed. Destination file missing: {dst_path}")
        if not files_equal(src_path, dst_path):
            raise RuntimeError(
                f"Binary comparison failed between: {src_path} and {dst_path}"
            )


def resolve_target_path(template: str) -> str:
    """Resolve {UserProfile}, {AppData}, {LocalAppData}, {Home} placeholders.

    Cross-platform: on non-Windows, {AppData} falls back to ~/.config and
    {LocalAppData} to ~/.local/share so VS Code extension paths still resolve.
    """
    home = str(Path.home())
    if os.name == "nt":
        appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        local_appdata = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        user_profile = os.environ.get("USERPROFILE") or home
    else:
        # VS Code stores user data under ~/.config on Linux and ~/Library/Application Support on macOS.
        if sys.platform == "darwin":
            appdata = str(Path.home() / "Library" / "Application Support")
            local_appdata = str(Path.home() / "Library" / "Application Support")
        else:
            appdata = str(Path.home() / ".config")
            local_appdata = str(Path.home() / ".local" / "share")
        user_profile = home

    resolved = (
        template.replace("{UserProfile}", user_profile)
        .replace("{AppData}", appdata)
        .replace("{LocalAppData}", local_appdata)
        .replace("{Home}", home)
    )
    # Normalise separators to the local OS.
    if os.name == "nt":
        resolved = resolved.replace("/", "\\")
    else:
        resolved = resolved.replace("\\", "/")
    return resolved


# ── YAML frontmatter parser ──────────────────────────────────────────────────

def read_agent_file(path: Path) -> dict[str, Any]:
    """Parse .ai/agents/*.agent.md or *.md into frontmatter fields + body.

    Only supports the subset used by this skill: scalar strings for
    name/description and inline JSON arrays for tools/groups. Matches the
    PowerShell implementation exactly.
    """
    content = read_text_auto(path)
    filename = path.name
    slug = re.sub(r"\.agent\.md$", "", filename)
    slug = re.sub(r"\.md$", "", slug)

    result: dict[str, Any] = {
        "Slug": slug,
        "Name": slug,
        "Description": "",
        "Tools": [],
        "Groups": ["read", "edit", "command"],
        "Body": content,
    }

    lines = content.split("\n")
    if len(lines) < 3 or lines[0].strip() != "---":
        return result

    closing = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing = i
            break
    if closing < 0:
        return result

    fm_lines = lines[1:closing]
    body_lines = lines[closing + 1:] if closing + 1 < len(lines) else []
    result["Body"] = "\n".join(body_lines).strip()

    for fm_line in fm_lines:
        trimmed = fm_line.strip()
        if not trimmed or trimmed.startswith("#"):
            continue
        colon_pos = trimmed.find(":")
        if colon_pos < 1:
            continue
        key = trimmed[:colon_pos].strip()
        val = trimmed[colon_pos + 1:].strip()

        # Strip surrounding quotes.
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]

        if key == "name":
            result["Name"] = val
        elif key == "description":
            result["Description"] = val
        elif key == "tools":
            if val.startswith("["):
                try:
                    result["Tools"] = list(json.loads(val))
                except json.JSONDecodeError:
                    pass
        elif key == "groups":
            if val.startswith("["):
                try:
                    result["Groups"] = list(json.loads(val))
                except json.JSONDecodeError:
                    pass

    return result


# ── Directory mirroring (robocopy /MIR equivalent) ──────────────────────────

def mirror_directory(source: Path, destination: Path, label: str) -> None:
    if not source.is_dir():
        print(f"No source folder found at: {source}")
        return

    ensure_directory(destination)

    print(f"\n--- Mirroring to {label} ---")
    print(f"Source:      {source}")
    print(f"Destination: {destination}")
    print("mirror <source> <destination> (excluding .git, .vs, bin, obj)")

    copied = 0
    updated = 0
    skipped = 0

    # Walk source and copy to dest.
    for root, dirs, files in os.walk(source):
        # Exclude directories in-place so os.walk skips them.
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIR_NAMES]
        rel = Path(root).relative_to(source)
        dst_root = destination / rel
        ensure_directory(dst_root)
        for fname in files:
            src_file = Path(root) / fname
            dst_file = dst_root / fname
            if dst_file.exists() and files_equal(src_file, dst_file):
                skipped += 1
                continue
            if dst_file.exists():
                updated += 1
            else:
                copied += 1
            shutil.copy2(src_file, dst_file)

    # Walk destination and delete files/dirs not present in source (mirror).
    deleted_files = 0
    deleted_dirs = 0
    for root, dirs, files in os.walk(destination, topdown=False):
        rel = Path(root).relative_to(destination)
        src_root = source / rel
        for fname in files:
            if not (src_root / fname).exists():
                dst_file = Path(root) / fname
                try:
                    dst_file.unlink()
                    deleted_files += 1
                except OSError as exc:
                    raise RuntimeError(f"Failed to delete stale mirrored file: {dst_file}") from exc
        for dname in dirs:
            dst_sub = Path(root) / dname
            src_sub = src_root / dname
            if dname in EXCLUDED_DIR_NAMES:
                continue
            if not src_sub.exists():
                try:
                    shutil.rmtree(dst_sub)
                    deleted_dirs += 1
                except OSError as exc:
                    raise RuntimeError(f"Failed to delete stale mirrored directory: {dst_sub}") from exc

    print(
        f"Mirrored to {label} "
        f"(copied={copied}, updated={updated}, up-to-date={skipped}, "
        f"removed_files={deleted_files}, removed_dirs={deleted_dirs})."
    )


# ── Additive copy / explicit-removal (for global skill activation) ───────────

def add_or_update_directory(source: Path, destination: Path, label: str) -> tuple[int, int, int]:
    """Copy source tree into destination additively (no destination-walk delete).

    Returns (copied, updated, skipped). Existing destination files not present in
    source are LEFT UNCHANGED — caller is responsible for any explicit removals.
    """
    if not source.is_dir():
        return (0, 0, 0)

    ensure_directory(destination)

    copied = 0
    updated = 0
    skipped = 0

    for root, dirs, files in os.walk(source):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIR_NAMES]
        rel = Path(root).relative_to(source)
        dst_root = destination / rel
        ensure_directory(dst_root)
        for fname in files:
            src_file = Path(root) / fname
            dst_file = dst_root / fname
            if dst_file.exists() and files_equal(src_file, dst_file):
                skipped += 1
                continue
            if dst_file.exists():
                updated += 1
            else:
                copied += 1
            shutil.copy2(src_file, dst_file)

    return (copied, updated, skipped)


def sync_global_skills(
    agent_name: str,
    src_global_skills_dir: Path,
    dst_root: Path,
    removed_list: list[str],
) -> None:
    """Activate global skills for an agent: additively copy each skill folder
    from .ai/.global/skills/{name}/ to {dst_root}/{name}/, then remove any folder
    listed in removed-skills.json.

    Pre-existing user-level skills not in source and not in removed_list are left
    alone — protects skills installed by other tools (e.g. GSD's gsd-* set).
    """
    label = f"{agent_name} GLOBAL skills"
    print(f"\n--- Activating {label} ---")
    print(f"Source:      {src_global_skills_dir}")
    print(f"Destination: {dst_root}")

    if not src_global_skills_dir.is_dir():
        print(f"No global skills source folder: {src_global_skills_dir}")
        return

    ensure_directory(dst_root)

    skill_folders = [p for p in sorted(src_global_skills_dir.iterdir())
                     if p.is_dir() and p.name not in EXCLUDED_DIR_NAMES]

    total_copied = 0
    total_updated = 0
    total_skipped = 0
    folders_promoted = 0

    for skill_dir in skill_folders:
        dst_skill_dir = dst_root / skill_dir.name
        c, u, s = add_or_update_directory(skill_dir, dst_skill_dir, skill_dir.name)
        total_copied += c
        total_updated += u
        total_skipped += s
        if c or u:
            folders_promoted += 1

    removed_count = 0
    for skill_name in removed_list:
        target = dst_root / skill_name
        if target.is_dir():
            try:
                shutil.rmtree(target)
                removed_count += 1
                print(f"  Removed (per removed-skills.json): {target}")
            except OSError as exc:
                raise RuntimeError(f"Failed to remove user-level skill: {target}") from exc

    print(
        f"Promoted to {label}: "
        f"folders_touched={folders_promoted}/{len(skill_folders)}, "
        f"files_copied={total_copied}, files_updated={total_updated}, "
        f"files_up-to-date={total_skipped}, folders_removed={removed_count}"
    )


def report_obsolete_paths(
    label: str,
    obsolete: dict[str, list[str]],
    primary_targets,
    repo_relative: bool,
) -> None:
    """Warn about obsolete (position 1+) paths that still exist on disk.

    `obsolete` maps a path to the list of agents that declared it as a legacy
    alternative. A path that is also the primary target of some other agent is
    NOT obsolete — that agent still writes there — so it is filtered out.
    `repo_relative=True` resolves paths under REPO_ROOT (project-level
    targets); `False` treats them as already-resolved absolute paths.
    """
    if not obsolete:
        return
    primary_set = set(primary_targets)
    flagged: list[tuple[str, Path, list[str]]] = []
    for path_str, agents in obsolete.items():
        if path_str in primary_set:
            continue
        target = (REPO_ROOT / path_str) if repo_relative else Path(path_str)
        if target.exists():
            flagged.append((path_str, target, agents))
    if not flagged:
        return
    print(f"\n--- Obsolete {label} paths detected ---")
    print("These paths are listed as legacy alternatives in agents.json and still")
    print("exist on disk. The script does NOT write to them. Delete them when ready:")
    for path_str, target, agents in flagged:
        users = ", ".join(agents)
        print(f"  - {target}  (legacy for: {users})")


def load_removed_skills(removed_skills_path: Path) -> list[str]:
    """Load the list of skill folder names to remove from user-level paths."""
    if not removed_skills_path.is_file():
        return []
    try:
        data = json.loads(removed_skills_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {removed_skills_path}: {exc}") from exc
    entries = data.get("removed", [])
    names: list[str] = []
    for entry in entries:
        if isinstance(entry, str):
            names.append(entry)
        elif isinstance(entry, dict) and entry.get("skill"):
            names.append(str(entry["skill"]))
    return names


# ── Sync operations ──────────────────────────────────────────────────────────

def remove_stale_instruction_files(target_dir: Path, source_files: list[Path]) -> None:
    """Delete any *instructions.md files in target_dir that are not in source_files.

    Keeps the target in sync with the .ai/ source set so renamed or removed
    instruction files do not linger and confuse downstream agents.
    """
    if not target_dir.is_dir():
        return
    source_names = {sf.name for sf in source_files}
    for existing in target_dir.glob("*instructions.md"):
        if existing.name not in source_names:
            try:
                existing.unlink()
                print(f"Removed stale: {existing}")
            except OSError as exc:
                raise RuntimeError(f"Failed to remove stale instruction file: {existing}") from exc


def sync_multiple_file_instructions(agent_name: str, target_directory: str, source_files: list[Path]) -> None:
    print(f"\n--- Updating {agent_name} Instructions ---")
    target_dir = REPO_ROOT / target_directory
    ensure_directory(target_dir)

    remove_stale_instruction_files(target_dir, source_files)

    for sf in source_files:
        copy_file_if_different(sf, target_dir / sf.name)

    assert_instruction_sync(AI_DIR, target_dir, source_files)


def sync_single_file_instructions(agent_name: str, target_file_path: str, source_files: list[Path]) -> None:
    print(f"\n--- Updating {agent_name} Instructions ---")
    target_file = REPO_ROOT / target_file_path
    try:
        relative_target = target_file.relative_to(REPO_ROOT)
    except ValueError:
        relative_target = target_file

    parts: list[str] = []
    first = True
    for sf in source_files:
        source_content = read_text_auto(sf)
        if not source_content.strip():
            print(f"WARNING: Skipping empty file: {sf.name}")
            continue
        if not first:
            parts.append("")
        parts.append(f"==== START OF INSTRUCTIONS FROM: {sf.name} ====")
        parts.append("")
        parts.append(f"# Instructions from: {sf.name}")
        parts.append("")
        parts.append(source_content.strip())
        parts.append("")
        parts.append(f"==== END OF INSTRUCTIONS FROM: {sf.name} ====")
        first = False

    # PowerShell AppendLine uses "\r\n" on Windows; match line-ending behaviour
    # by emitting native newlines. We use LF for cross-platform consistency — the
    # PS script used \r\n on Windows but Git on Windows typically normalises.
    # To preserve Windows parity, use \r\n when on Windows, else \n.
    newline = "\r\n" if os.name == "nt" else "\n"
    final_content = newline.join(parts) + newline

    existing = read_text_auto(target_file) if target_file.is_file() else None
    if existing is not None and existing == final_content:
        print(f"Up-to-date: {relative_target}")
        return

    write_utf8_no_bom(target_file, final_content)
    print(f"Updated: {relative_target}")


def sync_copilot_folder_instructions(instructions_config: dict, source_files: list[Path]) -> None:
    print("\n--- Updating GitHub CoPilot Instructions (folder-based) ---")

    main_name = instructions_config.get("mainFile")
    main_source = next((sf for sf in source_files if sf.name.lower() == str(main_name).lower()), None)
    if main_source is None:
        raise RuntimeError(f"Expected source '{main_name}' under .ai but none found.")

    copilot_target = REPO_ROOT / instructions_config["target"]
    copy_file_if_different(main_source, copilot_target)

    folder_target = REPO_ROOT / instructions_config["folderTarget"]
    ensure_directory(folder_target)
    # The main file is concatenated into copilot-instructions.md, so it should
    # not also live in the folder target — exclude it from the "kept" set.
    folder_sources = [sf for sf in source_files if sf.name.lower() != str(main_name).lower()]
    remove_stale_instruction_files(folder_target, folder_sources)
    for sf in folder_sources:
        copy_file_if_different(sf, folder_target / sf.name)


def build_roomodes_json(source_directory: Path, label: str) -> str:
    agent_files = sorted(source_directory.glob("*.agent.md"))
    if not agent_files:
        print(f"  No agent files found in: {source_directory}")
        return json.dumps({"customModes": []}, indent=2)

    modes: list[dict[str, Any]] = []
    for af in agent_files:
        parsed = read_agent_file(af)
        print(f"  [{label}] {parsed['Name']} (slug: {parsed['Slug']})")
        modes.append({
            "slug": str(parsed["Slug"]),
            "name": str(parsed["Name"]),
            "roleDefinition": str(parsed["Description"]),
            "customInstructions": str(parsed["Body"]),
            "groups": [str(g) for g in parsed["Groups"]],
        })

    return json.dumps({"customModes": modes}, indent=2)


def sync_agents_to_target(
    agent_name: str,
    source_directory: Path,
    target_path: str,
    fmt: str = "mirror",
    label: str = "",
) -> None:
    if not source_directory.is_dir():
        print(f"No agent source folder: {source_directory}")
        return

    agent_files = list(source_directory.glob("*.agent.md"))
    if not agent_files:
        return

    if not label:
        label = agent_name

    if fmt == "roomodes-json":
        print(f"\n--- Building {label} custom modes ({target_path}) ---")
        new_json = build_roomodes_json(source_directory, label)
        target_file = Path(target_path)
        existing = read_text_auto(target_file) if target_file.is_file() else None
        if existing is not None and existing.strip() == new_json.strip():
            print(f"Up-to-date: {target_path}")
        else:
            write_utf8_no_bom(target_file, new_json)
            print(f"Updated: {target_path}")
    else:
        mirror_directory(source_directory, Path(target_path), f"{label} agents")


# ── Agent detection (AUTO mode) ──────────────────────────────────────────────

def _agent_marker_folders(agent: dict) -> list[Path]:
    """Top-level project-relative folders that uniquely identify this agent.

    Used as additional detection signals so that creating `.roo/`, `.kilo/`,
    `.gemini/`, etc. is enough to enable the agent — the user does not have
    to populate the inner `rules/` or `skills/` subfolders first. Filters out
    paths that are shared (.agents) or too generic (.github).
    """
    GENERIC = {".github"}    # always exists in GitHub repos — bad signal
    candidates: set[str] = set()

    def add_first_segment(raw: str) -> None:
        if not raw:
            return
        norm = raw.replace("\\", "/")
        if "/" not in norm:
            return    # root-level files (AGENTS.md, GEMINI.md, .roomodes)
        first = norm.split("/", 1)[0]
        if first and not first.startswith(".agents") and first not in GENERIC:
            candidates.add(first)

    add_first_segment(agent.get("instructions", {}).get("target", ""))
    for path in (agent.get("skills") or []):
        add_first_segment(path)
    add_first_segment((agent.get("agents") or {}).get("target", ""))
    mcp_cfg = (agent.get("mcp") or {}).get("config", "")
    add_first_segment(mcp_cfg)

    return [REPO_ROOT / c for c in candidates]


def is_fully_shared(agent: dict) -> bool:
    """True if every output of this agent lands under `.agents/` or — for
    single-file outputs only — at the repository root. Such an agent needs no
    agent-specific folder at all (e.g. OpenAI Codex: AGENTS.md + .agents/skills/).

    Distinction matters: `AGENTS.md` is a root *file* (universal protocol, OK),
    but `.clinerules` is a root *folder* (agent-specific, NOT shared).
    """
    def under_agents(raw: str) -> bool:
        norm = raw.replace("\\", "/")
        return (
            norm.startswith(".agents/")
            or norm.startswith("{UserProfile}/.agents/")
            or norm.startswith("{Home}/.agents/")
            or norm.startswith("~/.agents/")
        )

    def shared_file(raw: str) -> bool:
        if not raw:
            return True
        norm = raw.replace("\\", "/")
        # A root file (no separator) qualifies. Anything with a path segment
        # must be under `.agents/`.
        return ("/" not in norm) or under_agents(raw)

    def shared_folder(raw: str) -> bool:
        return not raw or under_agents(raw)

    instr = agent.get("instructions") or {}
    if instr.get("mode") == "single-file":
        if not shared_file(instr.get("target", "")):
            return False
        if not shared_folder(instr.get("folderTarget", "")):
            return False
    elif instr.get("mode") == "multiple-files":
        if not shared_folder(instr.get("target", "")):
            return False

    skills = agent.get("skills") or []
    if skills and not under_agents(skills[0]):
        return False

    global_skills = agent.get("globalSkills") or []
    if global_skills and not under_agents(global_skills[0]):
        return False

    ag = agent.get("agents") or {}
    if ag.get("target"):
        # `roomodes-json` format writes a single file (e.g. `.roomodes`); other
        # formats mirror to a folder.
        check = shared_file if ag.get("format") == "roomodes-json" else shared_folder
        if not check(ag["target"]):
            return False

    ga = agent.get("globalAgents") or {}
    if ga.get("target") and not under_agents(ga["target"]):
        return False

    return True


def test_agent_exists(agent: dict) -> bool:
    """Detect whether an agent is enabled in this repository.

    An agent counts as enabled when ANY of these is true:
      - the configured instructions target exists (file or folder, even empty);
      - the GitHub Copilot companion `folderTarget` exists;
      - any agent-specific marker folder exists (e.g. `.roo`, `.kilo`, `.gemini`).

    The marker-folder check lets a user signal "enable Roo Code" by simply
    creating `.roo/`, without having to also create `.roo/rules/`.
    """
    instr = agent["instructions"]
    target = REPO_ROOT / instr["target"]
    mode = instr["mode"]
    if mode == "multiple-files" and target.is_dir():
        return True
    if mode == "single-file":
        if target.is_file():
            return True
        folder_target = instr.get("folderTarget")
        if folder_target and (REPO_ROOT / folder_target).is_dir():
            return True
    for marker in _agent_marker_folders(agent):
        if marker.is_dir():
            return True
    return False


def get_agent_format(config_obj: dict | None) -> str:
    if not config_obj:
        return "mirror"
    return config_obj.get("format") or "mirror"


def collect_obsolete_paths(all_agents: list[dict]) -> list[tuple[Path, list[str]]]:
    """Walk every agent in the config and return obsolete (path, agents) pairs.

    A path is obsolete when it appears at position 1+ of an agent's `skills`
    or `globalSkills` array AND no other agent claims it as primary AND it
    actually exists on disk. Paths are returned as resolved absolute Paths.
    """
    primaries: set[str] = set()
    for a in all_agents:
        for paths in (a.get("skills") or [], a.get("globalSkills") or []):
            if paths:
                primaries.add(paths[0])

    obsolete: dict[str, list[str]] = {}     # absolute path -> [agents]
    for a in all_agents:
        for paths in (a.get("skills") or [], a.get("globalSkills") or []):
            for legacy in paths[1:]:
                if legacy in primaries:
                    continue
                # `{UserProfile}`/`~` style → resolve to absolute; otherwise
                # treat as project-relative.
                if "{" in legacy or legacy.startswith("~"):
                    abs_path = Path(resolve_target_path(legacy))
                else:
                    abs_path = REPO_ROOT / legacy
                key = str(abs_path)
                if abs_path.exists():
                    obsolete.setdefault(key, []).append(a["name"])
    return [(Path(k), v) for k, v in sorted(obsolete.items())]


def cleanup_obsolete_interactive(all_agents: list[dict]) -> int:
    """List obsolete folders, prompt y/N, delete on confirmation. Returns count deleted."""
    flagged = collect_obsolete_paths(all_agents)
    if not flagged:
        print("\nNo obsolete folders found on disk. Nothing to clean up.")
        return 0
    print("\n--- Obsolete folders flagged for cleanup ---")
    for path, agents in flagged:
        print(f"  - {path}  (legacy for: {', '.join(agents)})")
    answer = input(f"\nDelete these {len(flagged)} obsolete folders? [y/N]: ").strip().lower()
    if answer not in ("y", "yes"):
        print("Cleanup cancelled.")
        return 0
    deleted = 0
    for path, _agents in flagged:
        try:
            if path.is_dir():
                shutil.rmtree(path)
            elif path.is_file():
                path.unlink()
            else:
                continue
            print(f"Deleted: {path}")
            deleted += 1
        except OSError as exc:
            print(f"FAILED to delete {path}: {exc}", file=sys.stderr)
    print(f"\nCleanup complete. Removed {deleted}/{len(flagged)} folders.")
    return deleted


def _wait_before_exit(args) -> None:
    """Pause briefly so users running the script from a window can read the output.

    Skipped when --no-clear is set (signals scripted/piped use).
    """
    if getattr(args, "no_clear", False):
        return
    try:
        time.sleep(4)
    except KeyboardInterrupt:
        pass


# ── Main logic ───────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync AI agent instructions, skills, and custom agents from .ai/ sources.",
        allow_abbrev=False,
    )
    parser.add_argument("mode", nargs="*", help="ALL | AUTO | <agent name> | (omit for menu)")
    parser.add_argument("--global", dest="global_flag", action="store_true",
                        help="Also sync global agents to user-level paths")
    parser.add_argument("--no-clear", action="store_true", help="Do not clear the console")
    parser.add_argument("--cleanup-obsolete", dest="cleanup_obsolete", action="store_true",
                        help="After sync, prompt to delete legacy folders flagged as obsolete in agents.json")
    args = parser.parse_args()

    mode = " ".join(args.mode).strip() if args.mode else ""
    global_flag = args.global_flag
    cleanup_flag = args.cleanup_obsolete

    if not args.no_clear:
        # Cross-platform "clear".
        os.system("cls" if os.name == "nt" else "clear")

    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(f"Agent configuration not found: {CONFIG_PATH}")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    source_instruction_files = sorted(AI_DIR.glob("*instructions.md"))
    if not source_instruction_files:
        print(f"WARNING: No '*instructions.md' files found in '{AI_DIR}'. Nothing to process.")
        return 0

    src_skills_dir = REPO_ROOT / ".ai" / "skills"
    src_agents_dir = REPO_ROOT / ".ai" / "agents"
    src_global_agents_dir = REPO_ROOT / ".ai" / ".global" / "agents"
    src_global_skills_dir = REPO_ROOT / ".ai" / ".global" / "skills"
    removed_skills_path = REPO_ROOT / ".ai" / ".global" / "removed-skills.json"

    def count_subdirs(p: Path) -> int:
        return sum(1 for c in p.iterdir() if c.is_dir()) if p.is_dir() else 0

    print(
        f"Project instructions: {len(source_instruction_files)}"
        f", project skills: {count_subdirs(src_skills_dir)}"
        f", global skills: {count_subdirs(src_global_skills_dir)}"
    )

    if global_flag:
        print("Global agent + skills sync: ENABLED (--global flag)")

    all_agents: list[dict] = config["agents"]
    agents_to_update: list[dict] = []

    mode_upper = mode.upper()
    if mode_upper == "ALL":
        print("Selected: ALL (parameter mode)")
        agents_to_update = list(all_agents)
    elif mode_upper == "AUTO":
        print("Selected: AUTO (parameter mode)")
        agents_to_update = [a for a in all_agents if test_agent_exists(a)]
    elif mode == "":
        detected = [a for a in all_agents if test_agent_exists(a)]
        detected_set = {id(a) for a in detected}

        # ANSI bold-green for detected agents (modern Windows 10+/Linux/macOS terminals).
        ANSI_DETECTED = "\033[1;32m"
        ANSI_RESET = "\033[0m"

        # Width of the name column — pads so all menu rows line up regardless
        # of the longest entry. +2 trailing spaces for breathing room.
        name_width = max(
            len("AUTO + Global"),
            len("Cleanup"),
            *(len(a["name"]) for a in all_agents),
        ) + 2

        # Menu fixed slots:
        #   1   AUTO
        #   2   AUTO + Global
        #   3   Cleanup
        #   4+  individual agents (highlighted if detected)
        print()
        print("==============================================================")
        print("Select Agent Instruction Set to Update")
        print("--------------------------------------------------------------")
        print(f"{1:2}. {'AUTO':<{name_width}}- Update detected agents (project level only)")
        print(f"{2:2}. {'AUTO + Global':<{name_width}}- Update detected agents + global agents")
        print(f"{3:2}. {'Cleanup':<{name_width}}- Remove obsolete folders (interactive)")
        print("--------------------------------------------------------------")
        for i, agent in enumerate(all_agents, start=4):
            name_padded = f"{agent['name']:<{name_width}}"
            suffix = "[supported]" if is_fully_shared(agent) else ""
            if id(agent) in detected_set:
                print(f"{i:2}. {ANSI_DETECTED}{name_padded}{ANSI_RESET}{suffix}")
            else:
                print(f"{i:2}. {name_padded}{suffix}")
        print(f"{0:2}. Exit")
        print("==============================================================")
        print()
        selection = input("Enter your choice: ").strip()

        if selection == "0":
            print("Operation cancelled.")
            return 0
        if selection == "1":
            agents_to_update = detected
            print("Selected: AUTO")
        elif selection == "2":
            agents_to_update = detected
            global_flag = True
            print("Selected: AUTO + Global")
        elif selection == "3":
            print("Selected: Cleanup obsolete folders")
            cleanup_obsolete_interactive(all_agents)
            _wait_before_exit(args)
            return 0
        else:
            try:
                idx = int(selection) - 4
            except ValueError:
                raise RuntimeError("Invalid selection.")
            if 0 <= idx < len(all_agents):
                agents_to_update = [all_agents[idx]]
                print(f"Selected: {all_agents[idx]['name']}")
            else:
                raise RuntimeError("Invalid selection.")
    else:
        found = next(
            (a for a in all_agents if a["name"].lower() == mode.lower() or a.get("id", "").lower() == mode.lower()),
            None,
        )
        if found is None:
            valid = ", ".join(a["name"] for a in all_agents)
            raise RuntimeError(f"Unknown agent '{mode}'. Valid agents: {valid}")
        agents_to_update = [found]
        print(f"Selected: {found['name']} (parameter mode)")

    # ── Sync per-agent instructions and project custom-agents ───────────────

    for agent in agents_to_update:
        instr = agent["instructions"]
        mode_val = instr["mode"]

        if mode_val == "multiple-files":
            sync_multiple_file_instructions(agent["name"], instr["target"], source_instruction_files)
        elif mode_val == "single-file":
            folder_target = instr.get("folderTarget")
            if folder_target and (REPO_ROOT / folder_target).is_dir():
                sync_copilot_folder_instructions(instr, source_instruction_files)
            else:
                sync_single_file_instructions(agent["name"], instr["target"], source_instruction_files)

        agents_cfg = agent.get("agents")
        if agents_cfg and agents_cfg.get("target"):
            proj_target = str(REPO_ROOT / agents_cfg["target"])
            proj_format = get_agent_format(agents_cfg)
            sync_agents_to_target(agent["name"], src_agents_dir, proj_target, proj_format, f"{agent['name']} project")

    # ── Skills sync (project level) ─────────────────────────────────────────
    # `skills` is now an ordered array per agent: position 0 is the PRIMARY
    # target the script mirrors to. Positions 1+ are OBSOLETE alternatives that
    # the agent may still read but the script no longer writes to. Multiple
    # agents may share the same primary (e.g. `.agents/skills`) — dedupe so we
    # only mirror once per unique target.

    primary_skills: dict[str, list[str]] = {}     # target -> [agent names]
    obsolete_skills: dict[str, list[str]] = {}    # target -> [agent names]
    for agent in agents_to_update:
        paths = agent.get("skills") or []
        if not paths:
            continue
        primary_skills.setdefault(paths[0], []).append(agent["name"])
        for legacy in paths[1:]:
            obsolete_skills.setdefault(legacy, []).append(agent["name"])

    if primary_skills:
        print("\n==============================================================")
        print("Skills Sync (project)")
        print("==============================================================")
        for target in sorted(primary_skills):
            supporters = ", ".join(primary_skills[target])
            label = f"skills [{target}] - used by: {supporters}"
            mirror_directory(src_skills_dir, REPO_ROOT / target, label)

    report_obsolete_paths("project skills", obsolete_skills, primary_skills.keys(), repo_relative=True)

    # ── Global agent sync (only with --global flag) ─────────────────────────

    if global_flag:
        print("\n==============================================================")
        print("Global Agent Sync")
        print("==============================================================")

        if not src_global_agents_dir.is_dir():
            print(f"No global agents source folder: {src_global_agents_dir}")
        else:
            global_files = list(src_global_agents_dir.glob("*.agent.md"))
            print(f"Global agent source files ({len(global_files)}):")
            for gf in global_files:
                print(f"- {gf.name}")

            for agent in agents_to_update:
                ga_cfg = agent.get("globalAgents")
                if not ga_cfg or not ga_cfg.get("target"):
                    continue
                ga_target = resolve_target_path(ga_cfg["target"])
                ga_format = get_agent_format(ga_cfg)
                sync_agents_to_target(
                    agent["name"], src_global_agents_dir, ga_target, ga_format, f"{agent['name']} GLOBAL"
                )

    # ── Global skills sync (only with --global flag) ────────────────────────

    if global_flag:
        print("\n==============================================================")
        print("Global Skills Sync")
        print("==============================================================")

        removed_list = load_removed_skills(removed_skills_path)
        if removed_list:
            print(f"Skills marked for removal in {removed_skills_path.name}: "
                  f"{', '.join(removed_list)}")

        # Same array convention as project skills: position 0 = primary target
        # we mirror to, positions 1+ = obsolete alternatives we just report.
        primary_globals: dict[str, list[str]] = {}    # resolved path -> [agent names]
        obsolete_globals: dict[str, list[str]] = {}   # resolved path -> [agent names]
        for agent in agents_to_update:
            paths = agent.get("globalSkills") or []
            if not paths:
                continue
            primary_globals.setdefault(resolve_target_path(paths[0]), []).append(agent["name"])
            for legacy in paths[1:]:
                obsolete_globals.setdefault(resolve_target_path(legacy), []).append(agent["name"])

        if not primary_globals:
            print("No agents have a globalSkills target configured. Skipping.")
        else:
            for resolved, supporters in primary_globals.items():
                label = f"global skills [{resolved}] - used by: {', '.join(supporters)}"
                sync_global_skills(label, src_global_skills_dir, Path(resolved), removed_list)

            report_obsolete_paths("global skills", obsolete_globals, primary_globals.keys(), repo_relative=False)

    print("\n\033[1;32mAll selected operations completed successfully.\033[0m")

    if cleanup_flag:
        print()
        cleanup_obsolete_interactive(all_agents)

    _wait_before_exit(args)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
