#!/usr/bin/env python3
"""Export per-file diffs, changed files, and base versions for a PR.

Generates unified diff patches for each changed file between base and feature
branches, exports the current (feature) versions of changed files, and optionally
exports the base versions for side-by-side comparison.

Usage:
    python s06_export_diff_artifacts.py [--config PATH] [--repo-path DIR]
        [--base-ref REF] [--head-ref REF] [--max-file-bytes N]
        [--detect-renames] [--write-changed-list]
"""

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_config import (
    assert_standalone_git_repository, get_branch_folder, get_review_config,
    get_work_folder, get_workspace_root, print_header, print_info,
    print_success, print_warning, read_text_file, run_git,
    should_pull_branch, write_utf8_no_bom,
)


def is_binary_file(file_path, max_check=8192):
    """Detect binary file by checking for NUL bytes in the first chunk."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(max_check)
        return b"\x00" in chunk
    except OSError:
        return False


def is_binary_git_blob(ref, path, cwd):
    """Check if a git blob is binary using NUL byte heuristic."""
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{path}"],
            capture_output=True, cwd=cwd
        )
        if result.returncode != 0:
            return False
        chunk = result.stdout[:8192]
        return b"\x00" in chunk
    except OSError:
        return False


def export_git_blob_utf8(ref, file_path, dest_path, cwd):
    """Export a git blob to a file as UTF-8 without BOM."""
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{file_path}"],
            capture_output=True, cwd=cwd
        )
        if result.returncode != 0:
            return False

        content = result.stdout
        # Strip BOM if present
        if content.startswith(b"\xef\xbb\xbf"):
            content = content[3:]

        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        return True
    except OSError:
        return False


def export_git_diff_utf8(diff_args, dest_path, cwd):
    """Export a git diff to a file as UTF-8 without BOM."""
    result = subprocess.run(
        ["git"] + diff_args,
        capture_output=True, cwd=cwd
    )
    content = result.stdout
    # Strip BOM if present
    if content.startswith(b"\xef\xbb\xbf"):
        content = content[3:]

    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)


def copy_text_file_utf8(src_path, dest_path):
    """Read a text file (auto-detect BOM) and write as UTF-8 without BOM."""
    content = read_text_file(str(src_path))
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    write_utf8_no_bom(str(dest_path), content)


def main():
    parser = argparse.ArgumentParser(description="Export per-file diffs and changed files.")
    parser.add_argument("--config", dest="config_path", help="Path to pr-review.json")
    parser.add_argument("--repo-path", help="Override path to local Git repository")
    parser.add_argument("--base-ref", help="Override base reference (e.g., origin/master)")
    parser.add_argument("--head-ref", help="Override head/feature reference")
    parser.add_argument("--out-diffs", help="Output directory for diff patches")
    parser.add_argument("--out-changes", help="Output directory for changed file versions")
    parser.add_argument("--out-base", help="Output directory for base file versions")
    parser.add_argument("--max-file-bytes", type=int, default=10485760,
                        help="Skip files larger than this (default: 10MB)")
    parser.add_argument("--detect-renames", action="store_true",
                        help="Enable rename detection in diffs")
    parser.add_argument("--write-changed-list", action="store_true",
                        help="Write legacy changed-files.txt")
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    root = get_workspace_root(str(scripts_dir))
    config_path = Path(args.config_path) if args.config_path else Path(root) / "pr-review.json"
    config_path = config_path.resolve()

    config = get_review_config(str(config_path))
    print_success(f"Loaded merged configuration from: {config_path}")

    work_folder = Path(get_work_folder(config, root))
    out_diffs = Path(args.out_diffs) if args.out_diffs else work_folder / "diffs"
    out_changes = Path(args.out_changes) if args.out_changes else work_folder / "changes"
    out_base = Path(args.out_base) if args.out_base else work_folder / "base"

    # Load Git metadata
    meta_path = work_folder / "meta.json"
    if not meta_path.is_file():
        print(f"ERROR: Git metadata file not found: {meta_path}. Run s04_fetch_repository.py first.",
              file=sys.stderr)
        sys.exit(1)
    meta = json.loads(read_text_file(str(meta_path)))
    print_success(f"Loaded Git metadata from: {meta_path}")

    # Load context
    context_path = work_folder / "context.json"
    if not context_path.is_file():
        print(f"ERROR: Context file not found: {context_path}. Run s02_get_azure_devops_info.py first.",
              file=sys.stderr)
        sys.exit(1)
    ctx = json.loads(read_text_file(str(context_path)))
    print_success(f"Loaded Azure DevOps context from: {context_path}")

    # Resolve refs
    repo_path = args.repo_path
    if not repo_path:
        repo_path = get_branch_folder(config, root, str(work_folder))
    repo_path = str(Path(repo_path).resolve())

    base_ref = args.base_ref
    if not base_ref:
        base_ref = meta.get("baseRef")
        if not base_ref:
            branch = meta.get("baseBranch") or ctx.get("TargetBranchName")
            if not branch:
                print("ERROR: Base branch name not found in metadata or context", file=sys.stderr)
                sys.exit(1)
            base_ref = f"origin/{branch}"

    head_ref = args.head_ref
    if not head_ref:
        head_ref = meta.get("featureRef")
        if not head_ref:
            branch = meta.get("featureBranch") or ctx.get("BranchName")
            if not branch:
                print("ERROR: Feature branch name not found in metadata or context", file=sys.stderr)
                sys.exit(1)
            head_ref = "HEAD" if not should_pull_branch(config) else f"origin/{branch}"

    out_diffs = out_diffs.resolve()
    out_changes = out_changes.resolve()
    out_base = out_base.resolve()

    print_header("Export Diff Artifacts Tool")
    print_info(str(config_path), "Configuration")
    print_info(repo_path, "Repository")
    print_info(base_ref, "Base ref")
    print_info(head_ref, "Head ref")
    print_info(str(out_diffs), "Output diffs")
    print_info(str(out_changes), "Output changes")
    print_info(str(out_base), "Output base")
    if config.get("PullRequestId"):
        print_info(str(config["PullRequestId"]), "Pull Request")
    print()

    # Ensure output directories exist
    out_diffs.mkdir(parents=True, exist_ok=True)
    out_changes.mkdir(parents=True, exist_ok=True)
    out_base.mkdir(parents=True, exist_ok=True)

    if not Path(repo_path).exists():
        print(f"ERROR: Repository path does not exist: {repo_path}", file=sys.stderr)
        sys.exit(1)

    assert_standalone_git_repository(repo_path, "Review workspace repository")

    # Get changed files with status
    print("Finding changed files with status...")
    status_args = ["diff", "--name-status", f"{base_ref}...{head_ref}"]
    if args.detect_renames:
        status_args.append("--find-renames")
    result = run_git(*status_args, cwd=repo_path)
    status_lines = [line for line in result.stdout.splitlines() if line.strip()]

    if not status_lines:
        # No diff between base and head. Common causes: feature branch was just
        # created from base and has no commits yet; PR was already merged so base
        # has caught up; pull_branch=false but local HEAD is stale. Write a
        # manifest with just the header plus a marker file recording the SHAs we
        # compared, so s06 can short-circuit cleanly and the operator can see
        # *why* the consolidated artifacts ended up empty.
        print_warning(
            f"No files changed between {base_ref} and {head_ref}. "
            f"Writing empty manifest + marker."
        )
        manifest_path = out_diffs / "changed-files.tsv"
        write_utf8_no_bom(str(manifest_path), "Status\tPath\tIsBinary\tReason\tHeadBytes\n")

        base_sha = meta.get("baseCommit", "")
        head_sha = meta.get("featureCommit", "")
        marker_lines = [
            "Empty diff: no files changed between the two refs.",
            f"  base_ref: {base_ref}  ({base_sha})",
            f"  head_ref: {head_ref}  ({head_sha})",
        ]
        if base_sha and head_sha and base_sha == head_sha:
            marker_lines.append(
                "  cause:    base and head point to the SAME commit "
                "(branch has no new work yet)."
            )
        write_utf8_no_bom(str(out_diffs / "EMPTY_DIFF.txt"),
                          "\n".join(marker_lines) + "\n")
        return

    # Parse entries
    entries = []
    for line in status_lines:
        parts = line.split("\t")
        if len(parts) >= 2:
            entries.append({"Status": parts[0].strip(), "Path": parts[-1].strip()})
        else:
            entries.append({"Status": parts[0].strip(), "Path": parts[0].strip()})

    print_success(f"Found {len(entries)} changed file(s)")
    print()

    exported_text = 0
    exported_binary = 0
    skipped_size = 0
    skipped_missing = 0
    manifest = []

    for e in entries:
        file = e["Path"]
        print(f"Processing: {file}")

        file_full = Path(repo_path) / file
        head_exists = file_full.exists()
        head_size = None

        if head_exists:
            head_size = file_full.stat().st_size
            if head_size > args.max_file_bytes:
                print(f"  Skipped content export (size: {head_size} bytes > {args.max_file_bytes})")
                skipped_size += 1
                manifest.append({
                    "Status": e["Status"], "Path": file, "IsBinary": "",
                    "Reason": "SkippedTooLarge", "HeadBytes": str(head_size),
                })
                continue

        # Determine binary-ness
        is_binary = False
        if head_exists:
            is_binary = is_binary_file(str(file_full))
        else:
            is_binary = is_binary_git_blob(base_ref, file, repo_path)

        manifest.append({
            "Status": e["Status"], "Path": file,
            "IsBinary": str(is_binary),
            "Reason": "Binary" if is_binary else "Text",
            "HeadBytes": str(head_size) if head_size is not None else "",
        })

        # Export text files only
        if not is_binary:
            dest_path = out_changes / file
            if head_exists:
                copy_text_file_utf8(str(file_full), str(dest_path))
                print("  Exported current version (text, normalized UTF-8 no BOM)")
            else:
                print("  File deleted in feature branch")
                skipped_missing += 1

            # Export base version
            base_dest = out_base / file
            try:
                exported = export_git_blob_utf8(base_ref, file, str(base_dest), repo_path)
                if exported:
                    print("  Exported base version (text, normalized UTF-8 no BOM)")
            except Exception:
                print("  Base version not available (new file?)")

            exported_text += 1
        else:
            print("  Detected binary file: skipping content export")
            exported_binary += 1

        # Export unified diff patch (always)
        patch_path = out_diffs / (file + ".patch")
        diff_args = ["diff", "--no-textconv", "--unified=3"]
        if args.detect_renames:
            diff_args.append("--find-renames")
        diff_args += [f"{base_ref}...{head_ref}", "--", file]
        export_git_diff_utf8(diff_args, str(patch_path), repo_path)
        print("  Exported diff patch (UTF-8 no BOM)")

    # Write manifest TSV
    manifest_path = out_diffs / "changed-files.tsv"
    lines = ["Status\tPath\tIsBinary\tReason\tHeadBytes"]
    for m in manifest:
        lines.append(f"{m['Status']}\t{m['Path']}\t{m['IsBinary']}\t{m['Reason']}\t{m['HeadBytes']}")
    write_utf8_no_bom(str(manifest_path), "\n".join(lines) + "\n")
    print()
    print_success(f"Changed files (SSOT): {manifest_path}")

    # Legacy output
    if args.write_changed_list:
        changed_list_path = out_diffs / "changed-files.txt"
        write_utf8_no_bom(str(changed_list_path), "\n".join(status_lines) + "\n")
        print(f"Changed files list (legacy): {changed_list_path}")

    print()
    print_header("Export Complete")
    print_success(f"Exported text files:   {exported_text}")
    print(f"Detected binary files: {exported_binary}")
    print(f"Skipped (too large):   {skipped_size}")
    print(f"Skipped (missing head):{skipped_missing}")


if __name__ == "__main__":
    main()
