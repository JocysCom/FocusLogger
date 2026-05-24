#!/usr/bin/env python3
"""Post review comment to Azure DevOps Pull Request.

Posts the content of review.md as a comment thread on the PR.
The thread status is set to 'closed' if the review approves the PR.

Usage:
    python s10_upsert_review_comment.py [--config PATH] [--review PATH]
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


def invoke_azdo(url, method, headers, body=None, use_default_creds=False):
    """Make an Azure DevOps REST API call."""
    import requests

    print(f"{method} {url}")

    kwargs = {}
    if body is not None:
        kwargs["data"] = json.dumps(body) if isinstance(body, dict) else body
        kwargs["headers"] = {**headers, "Content-Type": "application/json"}
    else:
        kwargs["headers"] = headers

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
    parser = argparse.ArgumentParser(description="Post review comment to Azure DevOps PR.")
    parser.add_argument("--config", dest="config_path", help="Path to pr-review.json")
    parser.add_argument("--review", dest="review_path", help="Path to review.md")
    parser.add_argument("--pat", default=os.environ.get("AZDO_PAT", ""),
                        help="Personal Access Token (default: $AZDO_PAT)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print payload without posting")
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    root = get_workspace_root(str(scripts_dir))
    config_path = Path(args.config_path) if args.config_path else Path(root) / "pr-review.json"
    config_path = config_path.resolve()

    # Load trusted root certs (Windows only)
    cert_script = scripts_dir / "Setup_Util_TrustedRootCertificates_Save.ps1"
    if cert_script.is_file() and os.name == "nt":
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(cert_script)],
                capture_output=True, timeout=30
            )
        except (OSError, subprocess.TimeoutExpired):
            pass

    print_header("Add Review Comment to PR")

    # Authentication
    headers, use_default_creds = get_auth_headers(args.pat)

    if not config_path.is_file():
        print(f"ERROR: Configuration file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    config = get_review_config(str(config_path))
    work_folder = Path(get_work_folder(config, root))

    review_path = Path(args.review_path) if args.review_path else work_folder / "review.md"
    review_path = review_path.resolve()

    if not review_path.is_file():
        print(f"ERROR: Review file not found: {review_path}", file=sys.stderr)
        sys.exit(1)

    print_success(f"Loaded configuration for PR {config.get('PullRequestId')}")

    # Read review content
    review_content = read_text_file(str(review_path))

    # Safety guard (ported from the n8n 'If Review Has Content' node, which was
    # the n8n-side check before the container started owning the comment post).
    # An empty review.md or one with unfilled template placeholders means the
    # AI agent did not actually complete the review — refuse to post.
    placeholder_tokens = [
        "{RISK_BADGE}", "{RISK_LEVEL}", "{DECISION_SYMBOL}",
        "{CONFIDENCE_BADGE}", "{CONFIDENCE_LEVEL}",
    ]
    if not review_content.strip():
        print(f"ERROR: Review file is empty: {review_path}", file=sys.stderr)
        sys.exit(1)
    leaked = [t for t in placeholder_tokens if t in review_content]
    if leaked:
        print(f"ERROR: Review file still contains unfilled placeholder(s) "
              f"({', '.join(leaked)}): {review_path}\n"
              "Refusing to post — the AI agent did not complete the review.",
              file=sys.stderr)
        sys.exit(1)

    # Empty suggestion-fence guard. Azure DevOps renders a ```suggestion block
    # as a one-click "apply this code" widget — useful when populated, broken
    # noise when empty. An empty body means the AI wrote the rationale but had
    # no diff to extract the replacement from (e.g. s04/s06 silently produced
    # no diff artifacts and the AI improvised — see execution 3871). Refuse
    # rather than post a half-formed suggestion the author can't act on.
    empty_suggestion_re = re.compile(r"```suggestion\s*\n[ \t]*\n?```", re.MULTILINE)
    empty_blocks = empty_suggestion_re.findall(review_content)
    if empty_blocks:
        print(f"ERROR: Review contains {len(empty_blocks)} empty ```suggestion "
              f"block(s): {review_path}\n"
              "Refusing to post — empty suggestion fences render as broken "
              "widgets in Azure DevOps. The AI agent likely had no diff to "
              "extract replacement code from (check that s04/s06 produced "
              "diff artifacts).",
              file=sys.stderr)
        sys.exit(1)

    # Build header from configuration
    review_agent_repo_url = config.get(
        "ReviewAgentUrl",
        f"{config['BaseUrl']}/{config['OrganizationName']}/_git/BWAI?path=/.ai/skills/pr-review"
    )
    review_comment_header_template = config.get(
        "ReviewCommentHeader",
        "**🤖 AI-Assisted Review**\nCreated by [AI Platform agent with PR Review]({review_agent_url})"
    )
    review_comment_header = review_comment_header_template.replace(
        "{review_agent_url}",
        review_agent_repo_url,
    )

    header = (
        "---\n"
        f"{review_comment_header}\n"
        "\n---\n\n"
    )
    review_content = header + review_content

    # Parse review to detect approval status
    thread_status = "active"
    if re.search(r"##\s*Decision\s*\n[^\n]*\u2705\s*Approve", review_content):
        thread_status = "closed"
        print_success("Review approves PR - thread will be marked as resolved")
    else:
        print("Review requests changes - thread will remain active")

    # Build API URL
    api_base = (f"{config['BaseUrl']}/{config['OrganizationName']}"
                f"/{config['ProjectName']}/_apis")
    threads_uri = (f"{api_base}/git/repositories/{config['RepoName']}"
                   f"/pullrequests/{config['PullRequestId']}"
                   f"/threads?api-version={config['AzureApiVersion']}")

    print_info(threads_uri, "Threads URL")
    print()

    if args.dry_run:
        print("[DRY RUN] Would post/update review comment:")
        print(f"  Status: {thread_status}")
        print(f"  Content length: {len(review_content)} chars")
        return

    # Check for existing thread
    threads_response = invoke_azdo(threads_uri, "GET", headers,
                                   use_default_creds=use_default_creds)

    matching_threads = []
    for t in threads_response.get("value", []):
        comments = t.get("comments", [])
        if comments:
            content = comments[0].get("content", "")
            if "**\U0001f916 AI-Assisted Review**" in content and "# AI Review report" in content:
                matching_threads.append(t)

    if matching_threads:
        existing = matching_threads[0]
        if len(matching_threads) > 1:
            print_warning(f"Found multiple AI review threads. Updating the first one (ID: {existing['id']}).")

        thread_id = existing["id"]
        comment_id = existing["comments"][0].get("id")

        if not comment_id:
            print(f"ERROR: Found thread {thread_id} but could not determine comment ID.",
                  file=sys.stderr)
            sys.exit(1)

        print(f"Existing AI review thread found (Thread ID: {thread_id}, Comment ID: {comment_id}), updating...")

        # Update comment
        comment_uri = (f"{api_base}/git/repositories/{config['RepoName']}"
                       f"/pullrequests/{config['PullRequestId']}"
                       f"/threads/{thread_id}/comments/{comment_id}"
                       f"?api-version={config['AzureApiVersion']}")
        invoke_azdo(comment_uri, "PATCH", headers,
                    body={"content": review_content},
                    use_default_creds=use_default_creds)
        print_success("Comment content updated")

        # Update thread status
        thread_uri = (f"{api_base}/git/repositories/{config['RepoName']}"
                      f"/pullrequests/{config['PullRequestId']}"
                      f"/threads/{thread_id}"
                      f"?api-version={config['AzureApiVersion']}")
        invoke_azdo(thread_uri, "PATCH", headers,
                    body={"status": thread_status},
                    use_default_creds=use_default_creds)
        print_success(f"Thread status set to {thread_status}")

    else:
        print("No existing AI review thread found, creating new...")

        new_thread = {
            "comments": [{
                "parentCommentId": 0,
                "content": review_content,
                "commentType": 1,
            }],
            "status": thread_status,
        }
        response = invoke_azdo(threads_uri, "POST", headers,
                               body=new_thread,
                               use_default_creds=use_default_creds)
        print_success("Review comment posted successfully!")
        print_info(str(response.get("id", "")), "Thread ID")
        print_info(response.get("status", ""), "Status")

    # PR URL
    pr_web_url = (f"{config['BaseUrl']}/{config['OrganizationName']}"
                  f"/{config['ProjectName']}/_git/{config['RepoName']}"
                  f"/pullrequest/{config['PullRequestId']}")
    print()
    print_info(pr_web_url, "View PR")
    print()
    print_header("Comment Posted/Updated")


if __name__ == "__main__":
    main()
