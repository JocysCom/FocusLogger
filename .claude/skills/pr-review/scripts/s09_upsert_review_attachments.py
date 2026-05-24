#!/usr/bin/env python3
"""Upload rasterized diagrams + AI-generated images, rewrite review.md.

Reads the diagrams produced by s08_rasterize_images.py and any AI-generated
images the agent embedded in review.md as local paths, uploads each to the
Azure DevOps PR attachments endpoint, then rewrites review.md so embedded
URLs point at the uploaded copies instead of local paths.

ONLINE: this script POSTs to the PR's attachments endpoint. It must NOT run
when SKIP_POST_COMMENT=1.

Two substitution passes against review.md:

1. ```mermaid fenced blocks  ->  ![](uploaded-url) + collapsed source <details>
   Uses the per-block sha256 from {WorkFolder}/diagrams/mermaid-manifest.json
   to pair each fence with its rendered PNG. Blocks that mmdc could not
   render in s08 are left as ```mermaid fences (they'll appear as raw code
   in the posted comment, which is the same as the pre-change behaviour).

2. ![alt](local-or-relative-path)  ->  ![alt](uploaded-url)
   Any markdown image reference pointing at a file under {WorkFolder}/ that
   exists on disk is uploaded and its URL substituted. Covers
   ai-image-generation output and any other local image the AI embedded.

Skipped on Provider=GitHub (GitHub renders mermaid natively and accepts
relative image paths from the repo, so uploads are unnecessary).

Usage:
    python s09_upsert_review_attachments.py [--config PATH] [--review PATH]
        [--pat TOKEN] [--dry-run]
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_config import (
    get_auth_headers, get_review_config, get_work_folder, get_workspace_root,
    print_header, print_info, print_success, print_warning, write_utf8_no_bom,
)

MERMAID_FENCE_RE = re.compile(r"```mermaid\s*\n(.*?)\n```", re.DOTALL)
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def is_azure_devops(config):
    base = (config.get("BaseUrl") or "").lower()
    if "dev.azure.com" in base or "visualstudio.com" in base:
        return True
    provider = (config.get("Provider") or "").lower()
    return provider == "azure" or provider == "azuredevops" or provider == "azuredevopsserver"


def upload_attachment(api_base, repo, pr_id, api_version, filename, blob, headers,
                      use_default_creds, dry_run=False):
    """POST a file to the PR attachments endpoint. Returns the public URL or None.

    Azure DevOps PR-scoped attachment endpoint:
        POST {api_base}/git/repositories/{repo}/pullRequests/{prId}/attachments/{fileName}
    Body is raw octet-stream bytes; response includes the embeddable URL.
    """
    import requests
    url = (f"{api_base}/git/repositories/{repo}/pullRequests/{pr_id}"
           f"/attachments/{quote(filename)}?api-version={api_version}")
    if dry_run:
        print_info(filename, "  [DRY] would POST")
        return f"[dry-run-attachment-url://{filename}]"

    post_headers = {k: v for k, v in headers.items() if k.lower() != "content-type"}
    post_headers["Content-Type"] = "application/octet-stream"

    kwargs = {"headers": post_headers, "data": blob, "timeout": 60}
    if use_default_creds and os.name == "nt":
        try:
            from requests_ntlm import HttpNtlmAuth
            kwargs["auth"] = HttpNtlmAuth("", "")
        except ImportError:
            pass

    try:
        response = requests.post(url, **kwargs)
        response.raise_for_status()
        data = response.json() if response.content else {}
        return data.get("url") or data.get("href")
    except Exception as exc:
        print_warning(f"Upload failed for {filename}: {exc}")
        return None


def substitute_mermaid_blocks(content, manifest, uploader):
    """Replace ```mermaid fences with image markdown + collapsed source.

    uploader(filename, blob) -> URL or None. Failed uploads leave the fence
    untouched so the posted comment still shows the source rather than a
    broken link.
    """
    diagrams = {d["sha256"]: d for d in manifest.get("diagrams", []) if d.get("png")}
    if not diagrams:
        return content, 0

    diagrams_dir = manifest["_diagramsDir"]
    counter = {"replaced": 0}

    def _replace(match):
        source = match.group(1).strip()
        import hashlib
        sha = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
        entry = diagrams.get(sha)
        if not entry:
            return match.group(0)  # left as-is
        png_path = diagrams_dir / entry["png"]
        if not png_path.is_file():
            return match.group(0)
        url = uploader(entry["png"], png_path.read_bytes())
        if not url:
            return match.group(0)
        counter["replaced"] += 1
        alt = f"diagram-{entry['index']:03d}"
        # Collapsed source preserves editability without bloating the visible
        # comment. ~~~ inner fence avoids closing the outer code-block if any
        # surrounding tooling wraps the comment in markdown later.
        return (
            f"![{alt}]({url})\n"
            f"<details><summary>Mermaid source</summary>\n\n"
            f"~~~mermaid\n{source}\n~~~\n"
            f"</details>"
        )

    new_content = MERMAID_FENCE_RE.sub(_replace, content)
    return new_content, counter["replaced"]


def substitute_local_image_paths(content, work_folder, uploader):
    """Upload any ![alt](path) that resolves to a file under work_folder.

    Markdown image refs with HTTPS URLs are left alone. Refs pointing at a
    local path under {WorkFolder} are uploaded and substituted.
    """
    counter = {"replaced": 0}
    cache = {}  # local_path -> uploaded_url

    def _replace(match):
        alt, ref = match.group(1), match.group(2)
        if ref.startswith(("http://", "https://", "data:", "[dry-run-attachment-url://")):
            return match.group(0)

        # Resolve ref relative to work_folder; also try repo root as a fallback.
        candidates = [
            (work_folder / ref).resolve(),
            (work_folder.parent / ref).resolve(),
        ]
        local = next((c for c in candidates if c.is_file()), None)
        if not local:
            return match.group(0)

        if local in cache:
            url = cache[local]
        else:
            url = uploader(local.name, local.read_bytes())
            cache[local] = url
        if not url:
            return match.group(0)

        counter["replaced"] += 1
        return f"![{alt}]({url})"

    new_content = MARKDOWN_IMAGE_RE.sub(_replace, content)
    return new_content, counter["replaced"]


def main():
    parser = argparse.ArgumentParser(description="Upload review images + rewrite review.md.")
    parser.add_argument("--config", dest="config_path", help="Path to pr-review.json")
    parser.add_argument("--review", dest="review_path", help="Path to review.md")
    parser.add_argument("--pat", default=os.environ.get("AZDO_PAT", ""),
                        help="Personal Access Token (default: $AZDO_PAT)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print actions without uploading or writing")
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    root = get_workspace_root(str(scripts_dir))
    config_path = Path(args.config_path) if args.config_path else Path(root) / "pr-review.json"

    if not config_path.is_file():
        print(f"ERROR: Configuration file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    print_header("Upload Review Attachments")

    config = get_review_config(str(config_path))

    if not is_azure_devops(config):
        print_success("Provider is not Azure DevOps — skipping upload "
                      "(GitHub renders mermaid natively and accepts relative image paths).")
        return

    for required in ("BaseUrl", "OrganizationName", "ProjectName", "RepoName",
                     "PullRequestId", "AzureApiVersion"):
        if not config.get(required):
            print(f"ERROR: Missing required config value: {required}", file=sys.stderr)
            sys.exit(1)

    headers, use_default_creds = get_auth_headers(args.pat)
    api_base = (f"{config['BaseUrl']}/{config['OrganizationName']}"
                f"/{config['ProjectName']}/_apis")

    work_folder = Path(get_work_folder(config, root))
    review_path = Path(args.review_path) if args.review_path else work_folder / "review.md"

    if not review_path.is_file():
        print(f"ERROR: review.md not found at: {review_path}", file=sys.stderr)
        sys.exit(1)

    content = review_path.read_text(encoding="utf-8")

    diagrams_dir = work_folder / "diagrams"
    manifest_path = diagrams_dir / "mermaid-manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {"version": 1, "totalCount": 0, "diagrams": []}
    manifest["_diagramsDir"] = diagrams_dir

    def uploader(filename, blob):
        return upload_attachment(
            api_base, config["RepoName"], config["PullRequestId"],
            config["AzureApiVersion"], filename, blob, headers,
            use_default_creds, dry_run=args.dry_run,
        )

    new_content, mermaid_replaced = substitute_mermaid_blocks(content, manifest, uploader)
    new_content, image_replaced = substitute_local_image_paths(new_content, work_folder, uploader)

    if new_content == content:
        print_success("No diagrams or local image paths to upload — review.md unchanged.")
        return

    if args.dry_run:
        print_info(str(mermaid_replaced), "Mermaid blocks would be substituted")
        print_info(str(image_replaced), "Local image refs would be substituted")
        return

    write_utf8_no_bom(str(review_path), new_content)
    print()
    print_info(str(mermaid_replaced), "Mermaid blocks substituted")
    print_info(str(image_replaced), "Local image refs substituted")
    print_success(f"Rewrote: {review_path}")
    print_header("Attachment Upload Complete")


if __name__ == "__main__":
    main()
