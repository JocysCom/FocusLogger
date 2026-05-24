#!/usr/bin/env python3
"""Create review and checklist files from templates with actual PR data.

Replaces placeholders with actual values from pr-review.json, context.json,
and meta.json.

Run order:
  1) s02_get_azure_devops_info.py (populates {WorkFolder}/context.json)
  2) s04_fetch_repository.py (populates {WorkFolder}/meta.json)
  3) This script (s05_reset_templates.py)

Usage:
    python s05_reset_templates.py [--config PATH]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_config import (
    get_review_config, get_work_folder, get_workspace_root,
    print_header, print_info, print_success, print_warning, read_text_file,
    skill_dir, write_utf8_no_bom,
)


def main():
    parser = argparse.ArgumentParser(description="Create review templates with actual PR data.")
    parser.add_argument("--config", dest="config_path", help="Path to pr-review.json")
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    root = get_workspace_root(str(scripts_dir))
    config_path = Path(args.config_path) if args.config_path else Path(root) / "pr-review.json"
    config_path = config_path.resolve()

    print_header("Reset Review Templates")
    print_info(root, "Root directory")
    print_info(str(config_path), "Config file")
    print()

    # Load merged configuration
    config = get_review_config(str(config_path))
    print_success(f"Loaded merged configuration from: {config_path}")

    # Resolve paths
    work_folder = Path(get_work_folder(config, root))
    skill_root = Path(skill_dir())
    review_template = skill_root / "assets" / "review.template.md"
    checklist_template = skill_root / "assets" / "checklist.template.md"
    pr_description_template = skill_root / "assets" / "pr-description.template.md"
    review_file = work_folder / "review.md"
    checklist_file = work_folder / "checklist.md"
    pr_description_file = work_folder / "pr-description.md"
    meta_path = work_folder / "meta.json"

    # Load metadata for branch names
    meta = None
    if meta_path.is_file():
        try:
            meta = json.loads(read_text_file(str(meta_path)))
            print_success(f"Loaded Git metadata from: {meta_path}")
        except Exception as exc:
            print_warning(f"Failed to load metadata file: {exc}")
    else:
        print_warning(f"Git metadata file not found: {meta_path}")
        print_warning("Branch names will not be available. Run s02_get_azure_devops_info.py first.")

    # Load Azure DevOps context
    context_json_path = work_folder / "context.json"
    ctx = None
    if context_json_path.is_file():
        ctx = json.loads(read_text_file(str(context_json_path)))
        print_success(f"Loaded Azure DevOps context from: {context_json_path}")
    else:
        print_warning(f"Context file not found: {context_json_path}")

    # Determine branch names
    base_branch = None
    if meta and meta.get("baseBranch"):
        base_branch = meta["baseBranch"]
    elif ctx and ctx.get("TargetBranchName"):
        base_branch = ctx["TargetBranchName"]
    if not base_branch:
        print("ERROR: Base branch name not found in metadata or context", file=sys.stderr)
        sys.exit(1)

    feature_branch = None
    if meta and meta.get("featureBranch"):
        feature_branch = meta["featureBranch"]
    elif ctx and ctx.get("BranchName"):
        feature_branch = ctx["BranchName"]
    if not feature_branch:
        print("ERROR: Feature branch name not found in metadata or context", file=sys.stderr)
        sys.exit(1)

    print()
    print("Creating review files from templates...")

    # Build URLs
    base_project_url = f"{config['BaseUrl']}/{config['OrganizationName']}/{config['ProjectName']}"
    pr_url = f"{base_project_url}/_git/{config['RepoName']}/pullrequest/{config['PullRequestId']}"

    work_item_urls = []
    for wid in config.get("WorkItemIds", []):
        work_item_urls.append(f"{base_project_url}/_workitems/edit/{wid}")
    work_item_links = ", ".join(work_item_urls) if work_item_urls else "N/A"

    # Replacement map
    replacements = {
        "{PR_LINK}": pr_url,
        "{REPO_NAME}": config.get("RepoName", ""),
        "{PROJECT_NAME}": config.get("ProjectName", ""),
        "{BASE_BRANCH}": base_branch,
        "{FEATURE_BRANCH}": feature_branch,
        "{WORK_ITEM_LINK}": work_item_links,
    }

    def apply_replacements(content):
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)
        return content

    # Create review.md from template
    if review_template.is_file():
        content = read_text_file(str(review_template))
        content = apply_replacements(content)
        work_folder.mkdir(parents=True, exist_ok=True)
        write_utf8_no_bom(str(review_file), content)
        print_success("  Created review.md from template")
    else:
        print_warning(f"Review template not found: {review_template}")

    # Create checklist.md from template
    if checklist_template.is_file():
        content = read_text_file(str(checklist_template))
        content = apply_replacements(content)
        write_utf8_no_bom(str(checklist_file), content)
        print_success("  Created checklist.md from template")
    else:
        print_warning(f"Checklist template not found: {checklist_template}")

    # Create pr-description.md from template
    if pr_description_template.is_file():
        content = read_text_file(str(pr_description_template))
        content = apply_replacements(content)
        write_utf8_no_bom(str(pr_description_file), content)
        print_success("  Created pr-description.md from template")
    else:
        print_warning(f"PR description template not found: {pr_description_template}")

    print()
    print_header("Template Reset Complete")
    print_success("Review configuration:")
    print_info(str(config.get("PullRequestId", "")), "  PR")
    if config.get("WorkItemIds"):
        print_info(", ".join(str(i) for i in config["WorkItemIds"]), "  Work Items")
    print_info(config.get("RepoName", ""), "  Repo")
    print_info(f"{feature_branch} -> Target: {base_branch}", "  Feature")


if __name__ == "__main__":
    main()
