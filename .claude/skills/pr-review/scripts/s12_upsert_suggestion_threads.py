#!/usr/bin/env python3
"""Upsert Azure DevOps PR suggestion comment threads parsed from review.md.

Parses a markdown review for "#### Suggestion N" entries and creates or updates
dedicated PR comment threads with file/line context so Azure DevOps renders
them as inline suggestions.

Usage:
    python s12_upsert_suggestion_threads.py [--config PATH] [--review PATH]
        [--pat TOKEN] [--remove-posted] [--dry-run]
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


def normalize_repo_path(path):
    """Normalize a file path to forward-slash relative format."""
    p = path.strip()
    p = re.sub(r"^[\\/]+", "", p)
    p = re.sub(r"^(?:\./)+", "", p)
    p = p.replace("\\", "/")
    return p


def parse_line_range(range_text):
    """Parse 'start-end' line range text.

    Returns:
        dict with 'start' and 'end' integer keys.
    """
    m = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", range_text.strip())
    if not m:
        raise ValueError(f"Invalid line range '{range_text}'. Expected 'start-end' (e.g., 10-25).")

    start = int(m.group(1))
    end = int(m.group(2))
    if start < 1 or end < 1 or end < start:
        raise ValueError(f"Invalid line range '{range_text}'. Start/end must be >= 1 and end >= start.")

    return {"start": start, "end": end}


def parse_review_suggestions(markdown):
    """Parse suggestions from review markdown.

    Returns:
        List of dicts with keys: Id, FilePath, StartLine, EndLine, Reason, Suggestion.
    """
    lines = re.split(r"\r\n|\n|\r", markdown)
    suggestions = []
    i = 0

    while i < len(lines):
        line = lines[i]
        m = re.match(r"^\s*####\s+Suggestion\s+(.+?)\s*$", line)
        if not m:
            i += 1
            continue

        suggestion_title = m.group(1).strip()
        sid = f"Suggestion {suggestion_title}"

        file_path = None
        range_text = None
        reason_lines = []
        suggestion_block = None

        i += 1

        while i < len(lines):
            l = lines[i]

            if re.match(r"^\s*####\s+Suggestion\s+", l):
                i -= 1
                break

            if file_path is None and re.match(r"^\s*File:\s*(.+?)\s*$", l):
                file_path = normalize_repo_path(re.match(r"^\s*File:\s*(.+?)\s*$", l).group(1))
                i += 1
                continue

            if range_text is None and re.match(r"^\s*Line\s*range:\s*(.+?)\s*$", l):
                range_text = re.match(r"^\s*Line\s*range:\s*(.+?)\s*$", l).group(1).strip()
                i += 1
                continue

            if re.match(r"^\s*Reason:\s*(.*)\s*$", l):
                reason_lines.append(re.match(r"^\s*Reason:\s*(.*)\s*$", l).group(1))
                i += 1
                while i < len(lines) and not re.match(r"^\s*```suggestion\s*$", lines[i]):
                    if re.match(r"^\s*(File|Line\s*range):\s*", lines[i]):
                        break
                    reason_lines.append(lines[i])
                    i += 1
                continue

            if re.match(r"^\s*```suggestion\s*$", l):
                i += 1
                block_lines = []
                while i < len(lines) and not re.match(r"^\s*```\s*$", lines[i]):
                    block_lines.append(lines[i])
                    i += 1
                suggestion_block = "\n".join(block_lines).rstrip()
                if i < len(lines) and re.match(r"^\s*```\s*$", lines[i]):
                    i += 1
                continue

            i += 1

        if not file_path or not range_text or suggestion_block is None:
            print_warning(f"Skipping '{sid}' because required metadata or suggestion block is missing.")
        else:
            try:
                rng = parse_line_range(range_text)
            except ValueError as exc:
                print_warning(f"Skipping '{sid}': {exc}")
                i += 1
                continue

            reason = "\n".join(reason_lines).strip() or "(no reason provided)"
            suggestions.append({
                "Id": sid,
                "FilePath": file_path,
                "StartLine": rng["start"],
                "EndLine": rng["end"],
                "Reason": reason,
                "Suggestion": suggestion_block,
            })

        i += 1

    return suggestions


def find_thread_by_marker(threads, marker):
    """Find threads containing the given marker in their first comment."""
    escaped = re.escape(marker)
    matches = []
    for t in threads:
        comments = t.get("comments", [])
        if comments:
            content = comments[0].get("content", "")
            if re.search(escaped, content):
                matches.append(t)
    return matches


def main():
    parser = argparse.ArgumentParser(description="Upsert suggestion threads to Azure DevOps PR.")
    parser.add_argument("--config", dest="config_path", help="Path to pr-review.json")
    parser.add_argument("--review", dest="review_path", help="Path to review.md")
    parser.add_argument("--pat", default=os.environ.get("AZDO_PAT", ""),
                        help="Personal Access Token (default: $AZDO_PAT)")
    parser.add_argument("--remove-posted", action="store_true",
                        help="Remove previously posted suggestion threads")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print payloads without posting")
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    root = get_workspace_root(str(scripts_dir))
    config_path = Path(args.config_path) if args.config_path else Path(root) / "pr-review.json"
    config_path = config_path.resolve()

    print_header("Upsert Suggestion Threads")

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

    headers, use_default_creds = get_auth_headers(args.pat)

    api_base = (f"{config['BaseUrl']}/{config['OrganizationName']}"
                f"/{config['ProjectName']}/_apis")
    threads_uri = (f"{api_base}/git/repositories/{config['RepoName']}"
                   f"/pullrequests/{config['PullRequestId']}"
                   f"/threads?api-version={config['AzureApiVersion']}")

    # Parse suggestions
    md = read_text_file(str(review_path))
    suggestions = parse_review_suggestions(md)

    agent_name = "ROO CODE"
    marker_root = "[AI-SUGGESTION-THREAD]"
    agent_marker = f"{marker_root}[{agent_name}]"
    repo_marker = f"{config['OrganizationName']}/{config['ProjectName']}/{config['RepoName']}"
    marker_prefix = f"{agent_marker}[{repo_marker}][PR:{config['PullRequestId']}]"

    print_success(f"Parsed {len(suggestions)} suggestion(s) from review.")

    # Get existing threads
    threads_response = invoke_azdo(threads_uri, "GET", headers,
                                   use_default_creds=use_default_creds)
    threads = threads_response.get("value", []) if threads_response else []

    # Removal mode
    if args.remove_posted:
        to_remove = find_thread_by_marker(threads, marker_root)
        print(f"Found {len(to_remove)} previously posted suggestion thread(s) to delete.")

        for t in to_remove:
            thread_id = t["id"]
            delete_uri = (f"{api_base}/git/repositories/{config['RepoName']}"
                          f"/pullrequests/{config['PullRequestId']}"
                          f"/threads/{thread_id}"
                          f"?api-version={config['AzureApiVersion']}")
            if args.dry_run:
                print(f"[DRY RUN] Would DELETE thread {thread_id}")
            else:
                invoke_azdo(delete_uri, "DELETE", headers,
                            use_default_creds=use_default_creds)

        print_header("Done (remove)")
        return

    # Upsert suggestions
    for s in suggestions:
        thread_marker = (f"{marker_prefix}[{s['Id']}]"
                         f"[file:{s['FilePath']}]"
                         f"[lines:{s['StartLine']}-{s['EndLine']}]")

        content = (
            f"{thread_marker}\n\n"
            f"**\U0001f916 AI Suggestion ({agent_name})**\n\n"
            f"**File:** `{s['FilePath']}`\n"
            f"**Line range:** {s['StartLine']}-{s['EndLine']}\n\n"
            f"**Reason**\n"
            f"{s['Reason']}\n\n"
            f"```suggestion\n"
            f"{s['Suggestion']}\n"
            f"```"
        )

        thread_context = {
            "filePath": s["FilePath"],
            "rightFileStart": {"line": s["StartLine"], "offset": 1},
            "rightFileEnd": {"line": s["EndLine"], "offset": 999},
        }

        # Find existing by marker
        existing_list = find_thread_by_marker(threads, thread_marker)
        existing_thread = existing_list[0] if existing_list else None

        if existing_thread:
            thread_id = existing_thread["id"]
            comment_id = existing_thread["comments"][0].get("id")

            if not comment_id:
                print_warning(f"Thread {thread_id} matched marker but commentId missing; skipping update.")
                continue

            if args.dry_run:
                print(f"[DRY RUN] Would PATCH thread {thread_id}, comment {comment_id}")
                continue

            comment_uri = (f"{api_base}/git/repositories/{config['RepoName']}"
                           f"/pullrequests/{config['PullRequestId']}"
                           f"/threads/{thread_id}/comments/{comment_id}"
                           f"?api-version={config['AzureApiVersion']}")
            invoke_azdo(comment_uri, "PATCH", headers,
                        body={"content": content},
                        use_default_creds=use_default_creds)

            thread_uri = (f"{api_base}/git/repositories/{config['RepoName']}"
                          f"/pullrequests/{config['PullRequestId']}"
                          f"/threads/{thread_id}"
                          f"?api-version={config['AzureApiVersion']}")
            invoke_azdo(thread_uri, "PATCH", headers,
                        body={"status": "active"},
                        use_default_creds=use_default_creds)

            print_success(f"Updated suggestion thread: {s['Id']} (Thread ID: {thread_id})")

        else:
            new_thread = {
                "comments": [{
                    "parentCommentId": 0,
                    "content": content,
                    "commentType": 1,
                }],
                "status": "active",
                "threadContext": thread_context,
            }

            if args.dry_run:
                print(f"[DRY RUN] Would POST suggestion thread: {s['Id']}")
                continue

            resp = invoke_azdo(threads_uri, "POST", headers,
                               body=new_thread,
                               use_default_creds=use_default_creds)
            print_success(f"Created suggestion thread: {s['Id']} (Thread ID: {resp.get('id', '')})")

    pr_web_url = (f"{config['BaseUrl']}/{config['OrganizationName']}"
                  f"/{config['ProjectName']}/_git/{config['RepoName']}"
                  f"/pullrequest/{config['PullRequestId']}")
    print()
    print_info(pr_web_url, "View PR")
    print_header("Done (upsert)")


if __name__ == "__main__":
    main()
