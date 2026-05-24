#!/usr/bin/env python3
"""Reset the workspace for a new PR review.

Cleans up generated artifacts from previous reviews (diffs, changes, base,
meta.json, context.json), preparing a clean slate for analyzing a new PR.
Run this first before any other review scripts.

Usage:
    python s01_reset_workspace.py [--keep-repo]
"""

import argparse
import shutil
import sys
from pathlib import Path

# Allow running as script or module
sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_config import (
    get_branch_folder, get_work_folder, get_workspace_root, print_header,
    print_info, print_success, should_pull_branch,
)


def main():
    parser = argparse.ArgumentParser(description="Reset the workspace for a new PR review.")
    parser.add_argument(
        "--keep-repo", action="store_true",
        help="Keep the repository checkout in BranchFolder when it is under WorkFolder.",
    )
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    root = get_workspace_root(str(scripts_dir))

    # Load config to determine work folder
    import json
    config_path = Path(root) / "pr-review.json"
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    pr_dir = Path(get_work_folder(config, root))

    if pr_dir.resolve() == Path(root).resolve():
        raise RuntimeError(
            "WorkFolder resolves to the repository root. Refusing to reset because this "
            "would delete the working repository."
        )

    print_header("Reset Workspace")

    print_info(root, "Root directory")
    print_info(str(pr_dir), "Work directory")
    print()

    # Clean up previous review artifacts
    print("Cleaning up previous review artifacts...")
    preserve_branch_folder = args.keep_repo or not should_pull_branch(config)

    if args.keep_repo or preserve_branch_folder:
        if pr_dir.exists():
            exclude = {"workspace", "README.md"}
            if preserve_branch_folder:
                branch_folder = Path(get_branch_folder(config, root, str(pr_dir)))
                try:
                    branch_top = branch_folder.resolve().relative_to(pr_dir.resolve()).parts[0]
                    exclude.add(branch_top)
                except (IndexError, ValueError):
                    pass

            for item in pr_dir.iterdir():
                if item.name in exclude:
                    continue
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    print(f"    Removed: {item.name}")
                except OSError as exc:
                    print(f"WARNING: Failed to remove {item.name}: {exc}", file=sys.stderr)
        else:
            pr_dir.mkdir(parents=True, exist_ok=True)
    else:
        if pr_dir.exists():
            try:
                # Check if README exists to preserve it
                readme_path = pr_dir / "README.md"
                readme_content = None
                if readme_path.is_file():
                    readme_content = readme_path.read_text(encoding="utf-8")

                shutil.rmtree(pr_dir)
                print(f"    Removed: {pr_dir}")

                # Recreate empty pr directory
                pr_dir.mkdir(parents=True, exist_ok=True)

                # Restore README if it existed
                if readme_content is not None:
                    readme_path.write_text(readme_content, encoding="utf-8")
            except OSError as exc:
                raise RuntimeError(
                    f"Failed to fully remove {pr_dir}. The review workspace may now be "
                    "partially deleted, which is unsafe because Git can fall back to an "
                    "ancestor repository from within remaining folders. Stop any process "
                    "using files under WorkFolder, then rerun "
                    "s01_reset_workspace.py or s01_reset_workspace.py --keep-repo as "
                    f"appropriate. Original error: {exc}"
                ) from exc
        else:
            pr_dir.mkdir(parents=True, exist_ok=True)

    print()
    print_header("Workspace Reset Complete")


if __name__ == "__main__":
    main()
