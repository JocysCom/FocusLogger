#!/usr/bin/env python3
"""Fetch Azure DevOps work item and pull request information.

Queries Azure DevOps REST API to fetch work item details and pull request
information, updating context.json and meta.json for the review.

Usage:
    python s02_get_azure_devops_info.py [--config PATH] [--pat TOKEN]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_config import (
    get_auth_headers, get_review_config, get_work_folder, get_workspace_root,
    print_header, print_info, print_success, print_warning, write_utf8_no_bom,
)


def invoke_api(url, headers, description, use_default_credentials=False):
    """Make an API call safely, returning the response JSON or None."""
    import requests

    print(f"Fetching {description}...")
    try:
        kwargs = {"headers": headers}
        if use_default_credentials and os.name == "nt":
            # Try NTLM on Windows
            try:
                from requests_ntlm import HttpNtlmAuth
                kwargs["auth"] = HttpNtlmAuth("", "")
            except ImportError:
                pass
        response = requests.get(url, **kwargs)
        response.raise_for_status()
        print("  Success")
        return response.json()
    except Exception as exc:
        print_warning(f"Failed to fetch {description}: {exc}")
        return None


def require_config(config, *field_names):
    """Fail with a clear message when required values cannot be derived."""
    missing = [name for name in field_names if not config.get(name)]
    if missing:
        joined = ", ".join(missing)
        print(
            f"ERROR: Could not derive required configuration value(s): {joined}.\n"
            "Set them in pr-review.json or ensure the repository origin remote is an Azure DevOps URL.",
            file=sys.stderr,
        )
        sys.exit(1)


def get_current_branch_name(config):
    """Return the feature branch name derived from config/Git context."""
    branch_name = config.get("BranchName")
    if branch_name:
        return branch_name

    print(
        "ERROR: Could not derive the current branch name. Set BranchName in pr-review.json.",
        file=sys.stderr,
    )
    sys.exit(1)


def fetch_pull_request_by_branch(config, api_base_url, headers, use_default_creds):
    """Fetch the active PR for the current source branch when PullRequestId is omitted."""
    source_ref = f"refs/heads/{get_current_branch_name(config)}"
    repo_name = config["RepoName"]
    url = (
        f"{api_base_url}/git/repositories/{repo_name}/pullrequests"
        f"?searchCriteria.sourceRefName={source_ref}"
        f"&searchCriteria.status=active"
        f"&api-version={config['AzureApiVersion']}"
    )
    response = invoke_api(url, headers, "Pull Request by current branch", use_default_creds)
    values = response.get("value", []) if response else []

    if len(values) == 1:
        return values[0]
    if len(values) > 1:
        print(
            f"ERROR: Pull Request ID can't be identified because {len(values)} active "
            f"Pull Request IDs were found for branch {source_ref}. "
            "Set PullRequestId in pr-review.json to disambiguate.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"ERROR: Pull Request ID can't be identified because no active PR was found "
        f"for branch {source_ref}. Set PullRequestId in pr-review.json or create/open "
        "the PR first.",
        file=sys.stderr,
    )
    sys.exit(1)


def fetch_work_items_for_pull_request(config, api_base_url, headers, use_default_creds):
    """Return work item IDs linked to the pull request."""
    url = (
        f"{api_base_url}/git/repositories/{config['RepoName']}"
        f"/pullrequests/{config['PullRequestId']}/workitems"
        f"?api-version={config['AzureApiVersion']}"
    )
    response = invoke_api(url, headers, "Pull Request linked Work Items", use_default_creds)
    values = response.get("value", []) if response else []
    return [item.get("id") for item in values if item.get("id")]


def main():
    parser = argparse.ArgumentParser(description="Fetch Azure DevOps PR and work item info.")
    parser.add_argument("--config", dest="config_path", help="Path to pr-review.json")
    parser.add_argument("--pat", default=os.environ.get("AZDO_PAT", ""),
                        help="Personal Access Token (default: $AZDO_PAT)")
    parser.add_argument("--quiet", action="store_true", help="Suppress detailed output")
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    root = get_workspace_root(str(scripts_dir))
    config_path = Path(args.config_path) if args.config_path else Path(root) / "pr-review.json"
    config_path = config_path.resolve()

    # Load trusted root certificates helper (Windows only)
    cert_script = scripts_dir / "Setup_Util_TrustedRootCertificates_Save.ps1"
    if cert_script.is_file() and os.name == "nt":
        try:
            subprocess.run(
                ["powershell", "-File", str(cert_script)],
                capture_output=True, timeout=30
            )
        except (OSError, subprocess.TimeoutExpired):
            pass

    print_header("Azure DevOps Info Fetcher")

    if not config_path.is_file():
        print(f"ERROR: Configuration file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    config = get_review_config(str(config_path))
    require_config(config, "BaseUrl", "OrganizationName", "ProjectName", "RepoName", "AzureApiVersion")
    print_success(f"Loaded configuration for {config.get('RepoName')} on {config.get('BranchName', 'current branch')}")

    # Build base URLs
    base_project_url = f"{config['BaseUrl']}/{config['OrganizationName']}/{config['ProjectName']}"
    api_base_url = f"{base_project_url}/_apis"

    print_info(base_project_url, "Project URL")
    print_info(api_base_url, "API Base URL")
    print()

    # Prepare authentication
    headers, use_default_creds = get_auth_headers(args.pat)

    # Initialize context
    context = {}

    # Fetch Pull Request information
    if config.get("PullRequestId"):
        pr_url = (f"{api_base_url}/git/repositories/{config['RepoName']}"
                  f"/pullrequests/{config['PullRequestId']}"
                  f"?api-version={config['AzureApiVersion']}")
        pr_info = invoke_api(pr_url, headers, "Pull Request details", use_default_creds)
    else:
        pr_info = fetch_pull_request_by_branch(config, api_base_url, headers, use_default_creds)

    if pr_info:
        source_branch = (pr_info.get("sourceRefName") or "").replace("refs/heads/", "")
        target_branch = (pr_info.get("targetRefName") or "").replace("refs/heads/", "")
        context["BranchName"] = source_branch
        context["TargetBranchName"] = target_branch
        context["PullRequestId"] = pr_info.get("pullRequestId")
        config["PullRequestId"] = pr_info.get("pullRequestId")
        context["PullRequestTitle"] = pr_info.get("title", "")
        context["PullRequestDescription"] = pr_info.get("description", "")

        created_by = pr_info.get("createdBy") or {}
        context["PullRequestCreatedBy"] = created_by.get("displayName", "")
        context["PullRequestCreatedDate"] = pr_info.get("creationDate", "")
        context["PullRequestStatus"] = pr_info.get("status", "")
        context["PullRequest"] = pr_info

        if not args.quiet:
            print()
            print_header("Pull Request Information")
            print_info(pr_info.get("title", ""), "Title")
            print_info(pr_info.get("status", ""), "Status")
            print_info(created_by.get("displayName", ""), "Created by")
            print_info(pr_info.get("creationDate", ""), "Created")
            print_info(source_branch, "Source")
            print_info(target_branch, "Target")

            if pr_info.get("description"):
                print()
                print("Description:")
                print(pr_info["description"])

    # Fetch Work Item information
    work_item_ids = list(config.get("WorkItemIds") or [])
    if not work_item_ids and config.get("PullRequestId"):
        work_item_ids = fetch_work_items_for_pull_request(config, api_base_url, headers, use_default_creds)
        if work_item_ids:
            context["WorkItemIds"] = work_item_ids

    if work_item_ids:
        ids_string = ",".join(str(wid) for wid in work_item_ids)
        wi_url = (f"{api_base_url}/wit/workitems"
                  f"?ids={ids_string}&api-version={config['AzureApiVersion']}")
        wi_info = invoke_api(wi_url, headers, "Work Items details", use_default_creds)

        if wi_info and wi_info.get("value"):
            work_items = wi_info["value"]
            context["WorkItems"] = work_items

            first_wi = work_items[0]
            fields = first_wi.get("fields", {})

            context["WorkItemTitle"] = fields.get("System.Title", "")
            context["WorkItemType"] = fields.get("System.WorkItemType", "")
            context["WorkItemState"] = fields.get("System.State", "")
            assigned_to = fields.get("System.AssignedTo") or {}
            context["WorkItemAssignedTo"] = assigned_to.get("displayName", "")
            context["WorkItem"] = first_wi

            if not args.quiet:
                print()
                print_header("Work Items Information")
                for wi in work_items:
                    wi_fields = wi.get("fields", {})
                    print_info(str(wi.get("id", "")), "ID")
                    print_info(wi_fields.get("System.Title", ""), "Title")
                    print_info(wi_fields.get("System.WorkItemType", ""), "Type")
                    print_info(wi_fields.get("System.State", ""), "State")
                    at = wi_fields.get("System.AssignedTo") or {}
                    if at.get("displayName"):
                        print_info(at["displayName"], "Assigned to")
                    print("---")

    # Write context.json
    work_dir = Path(get_work_folder(config, root))
    work_dir.mkdir(parents=True, exist_ok=True)

    context_path = work_dir / "context.json"
    write_utf8_no_bom(str(context_path), json.dumps(context, indent=2, ensure_ascii=False))
    print()
    print_success(f"Dynamic context saved to: {context_path}")

    # Write meta.json with branch names
    meta = {
        "baseBranch": context.get("TargetBranchName", ""),
        "featureBranch": context.get("BranchName", ""),
    }
    meta_path = work_dir / "meta.json"
    write_utf8_no_bom(str(meta_path), json.dumps(meta, indent=2, ensure_ascii=False))
    print_success(f"Branch metadata written to: {meta_path}")

    # Generate reference URLs
    print()
    print_header("Reference URLs")
    if config.get("PullRequestId"):
        pr_web_url = (f"{base_project_url}/_git/{config['RepoName']}"
                      f"/pullrequest/{config['PullRequestId']}")
        print_info(pr_web_url, "Pull Request")
    for wid in work_item_ids:
        url = f"{base_project_url}/_workitems/edit/{wid}"
        print_info(url, f"Work Item [{wid}]")

    print()
    print_header("Info Fetch Complete")


if __name__ == "__main__":
    main()
