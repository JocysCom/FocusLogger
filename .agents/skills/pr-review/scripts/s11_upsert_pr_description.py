#!/usr/bin/env python3
"""Update the PR description from {WorkFolder}/pr-description.md.

Refuses to overwrite a real author-written PR description. The update only
proceeds when ALL of these guards pass:

  1. pr-description.md exists and is non-empty after trim.
  2. pr-description.md does NOT contain the `<!-- pr-description:unfilled -->`
     sentinel from the template.
  3. pr-description.md does NOT match scaffold-signature phrases from the
     template ("One-line motivation", "Briefly list what changed",
     `{WORK_ITEM_LINK}`) — catches cases where the AI failed to replace the
     scaffold with real content.
  4. The PR's current description is literally empty (after trim).

History (do not loosen these): the n8n `Build Review Comment` Code node used
to apply a looser `looksEmpty()` check that stripped HTML and matched against
placeholder phrases. The Normalize node did not expose `Description`, so
`looksEmpty(undefined||'')` returned true and the workflow wiped Kevin Green's
real description on PR 32147 (execution 3509). Losing real author content is
far worse than skipping an empty-PR update, so the default here is REFUSE.

This script POSTs/PATCHes the PR. It must NOT run when SKIP_POST_COMMENT=1
(entrypoint.sh enforces this).

Usage:
    python s11_upsert_pr_description.py [--config PATH] [--description PATH]
        [--pat TOKEN] [--dry-run]
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_config import (
    get_auth_headers, get_review_config, get_work_folder, get_workspace_root,
    print_header, print_info, print_success, print_warning, read_text_file,
)

UNFILLED_SENTINEL_RE = re.compile(r"<!--\s*pr-description:unfilled", re.IGNORECASE)
SCAFFOLD_SIGNATURE_RE = re.compile(
    r"Briefly list what changed|One-line motivation|\{WORK_ITEM_LINK\}",
    re.IGNORECASE,
)


def invoke_azdo(url, method, headers, body=None, use_default_creds=False):
    import requests

    print(f"{method} {url}")
    kwargs = {"headers": {**headers, "Content-Type": "application/json"}}
    if body is not None:
        kwargs["data"] = json.dumps(body) if isinstance(body, dict) else body

    if "Authorization" not in headers and use_default_creds and os.name == "nt":
        try:
            from requests_ntlm import HttpNtlmAuth
            kwargs["auth"] = HttpNtlmAuth("", "")
        except ImportError:
            pass

    response = requests.request(method, url, **kwargs)
    response.raise_for_status()
    if response.content:
        return response.json()
    return None


def main():
    parser = argparse.ArgumentParser(description="Update PR description from pr-description.md.")
    parser.add_argument("--config", dest="config_path", help="Path to pr-review.json")
    parser.add_argument("--description", dest="description_path",
                        help="Path to pr-description.md")
    parser.add_argument("--pat", default=os.environ.get("AZDO_PAT", ""),
                        help="Personal Access Token (default: $AZDO_PAT)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Evaluate guards and print decision without PATCHing")
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    root = get_workspace_root(str(scripts_dir))
    config_path = Path(args.config_path) if args.config_path else Path(root) / "pr-review.json"
    config_path = config_path.resolve()

    cert_script = scripts_dir / "Setup_Util_TrustedRootCertificates_Save.ps1"
    if cert_script.is_file() and os.name == "nt":
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(cert_script)],
                capture_output=True, timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass

    print_header("Upsert PR Description")

    if not config_path.is_file():
        print(f"ERROR: Configuration file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    config = get_review_config(str(config_path))

    for required in ("BaseUrl", "OrganizationName", "ProjectName", "RepoName",
                     "PullRequestId", "AzureApiVersion"):
        if not config.get(required):
            print(f"ERROR: Missing required config value: {required}", file=sys.stderr)
            sys.exit(1)

    work_folder = Path(get_work_folder(config, root))
    description_path = (Path(args.description_path) if args.description_path
                        else work_folder / "pr-description.md")
    description_path = description_path.resolve()

    if not description_path.is_file():
        print_success("No pr-description.md present — nothing to update.")
        return

    candidate = read_text_file(str(description_path))
    candidate_stripped = candidate.strip()

    # Guard 1: non-empty
    if not candidate_stripped:
        print_success("pr-description.md is empty — skipping description update.")
        return

    # Guard 2: unfilled sentinel
    if UNFILLED_SENTINEL_RE.search(candidate):
        print_success("pr-description.md still contains the unfilled sentinel — "
                      "skipping description update.")
        return

    # Guard 3: scaffold-signature phrases
    if SCAFFOLD_SIGNATURE_RE.search(candidate):
        print_success("pr-description.md matches a scaffold-signature phrase "
                      "(e.g. 'One-line motivation') — skipping description update.")
        return

    # Guard 4: original PR description must be literally empty.
    # Fail-closed: if we can't observe the original, we refuse.
    #
    # `PullRequestDescription` is the flat field populated identically by both
    # entry paths:
    #   - IDE mode: s02_get_azure_devops_info.py sets it from the raw ADO API
    #     response (`description`, lowercase).
    #   - n8n mode: the `Build PR Review Config` Code node sets it from
    #     `pr.Description || pr.Body` (capitalized, from the source-provider
    #     abstraction).
    # Both paths land here as a string ('' or content). Before Phase 2 this
    # script looked at `PullRequest.description` (lowercase) only and refused
    # to overwrite in n8n mode where the nested key is capitalized — execution
    # 3871 hit that mismatch.
    if "PullRequestDescription" not in config:
        print_warning("PullRequestDescription field missing from merged config — "
                      "refusing to overwrite (fail-closed). Run "
                      "s02_get_azure_devops_info.py or ensure n8n's "
                      "Build PR Review Config populated PullRequestDescription "
                      "in PR_CONTEXT_JSON_B64.")
        return
    original_str = "" if config.get("PullRequestDescription") is None else str(
        config["PullRequestDescription"]
    )
    if original_str.strip() != "":
        print_success(f"PR already has a description ({len(original_str)} chars) — "
                      "skipping (refuses to overwrite real content).")
        return

    print_info(str(len(candidate_stripped)), "Description bytes to write")

    headers, use_default_creds = get_auth_headers(args.pat)

    pr_url = (f"{config['BaseUrl']}/{config['OrganizationName']}"
              f"/{config['ProjectName']}/_apis/git/repositories/{config['RepoName']}"
              f"/pullrequests/{config['PullRequestId']}"
              f"?api-version={config['AzureApiVersion']}")

    if args.dry_run:
        print("[DRY RUN] All guards passed. Would PATCH:")
        print(f"  URL:     {pr_url}")
        print(f"  Body:    {{'description': <{len(candidate_stripped)} chars>}}")
        return

    invoke_azdo(pr_url, "PATCH", headers,
                body={"description": candidate_stripped},
                use_default_creds=use_default_creds)
    print_success("PR description updated.")
    print_header("Description Update Complete")


if __name__ == "__main__":
    main()
