#!/usr/bin/env python3
"""Extract user-attached images and binary attachments referenced by the PR.

Walks the PR description, every PR comment thread, and every linked work item
(description + comments + AttachedFile relations). Downloads each referenced
image to {WorkFolder}/attachments/, captures the hosting markdown/HTML as
context, computes deterministic metadata (mime, dimensions, sha256), and
writes a manifest the reviewing AI can read.

This script does no AI inference. It bundles screenshots + their authoring
context into a folder so the reviewing AI can interpret pixel content as part
of its normal multimodal pass.

If a linked work item already has an [AI Vision] thread (produced by the n8n
'Refactoring - Review Work Item' workflow), its body is captured verbatim as
'ai-vision-summary.md' so the reviewer can prefer that pre-extracted summary
over re-interpreting the image.

Usage:
    python s03_extract_attachments.py [--config PATH] [--pat TOKEN]
        [--max-bytes N] [--skip-download]
"""

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_config import (
    get_auth_headers, get_review_config, get_work_folder, get_workspace_root,
    print_header, print_info, print_success, print_warning, write_utf8_no_bom,
)

DEFAULT_MAX_BYTES = 25 * 1024 * 1024
THUMB_MAX_DIM = 2048
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".svg"}
RASTER_EXTENSIONS = IMAGE_EXTENSIONS - {".svg"}
AI_VISION_MARKER = "[AI Vision]"

MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
HTML_IMG_RE = re.compile(r"<img\b[^>]*?\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
BARE_URL_RE = re.compile(
    r"https?://[^\s\"'<>)\]]+\.(?:png|jpe?g|gif|webp|svg|bmp|tiff?)(?:\?[^\s\"'<>)\]]*)?",
    re.IGNORECASE,
)
AZDO_INLINE_ATTACHMENT_RE = re.compile(
    r"https?://[^\s\"'<>)\]]+/_apis/(?:wit|git/repositories/[^/]+/pull[rR]equests/\d+)/attachments/[^\s\"'<>)\]]+",
    re.IGNORECASE,
)


def slugify(text, fallback="item"):
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "-", text).strip("-")
    return text[:60] or fallback


def normalize_url(url):
    """Strip surrounding whitespace and HTML entities.

    Also trims trailing HTML-entity fragments (e.g. '&quot' without semicolon)
    that bleed in when bare-URL detection runs over HTML attribute strings.
    """
    if not url:
        return ""
    url = url.strip().rstrip(".,);]")
    url = url.replace("&amp;", "&")
    # Strip trailing broken HTML entity like "&quot", "&apos", "&lt" (no semicolon
    # because the closing was consumed elsewhere or never matched).
    url = re.sub(r"&(?:quot|apos|lt|gt|nbsp|amp)$", "", url, flags=re.IGNORECASE)
    return url


def has_image_extension(url):
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in IMAGE_EXTENSIONS)


def filename_from_url(url, fallback):
    """Derive a sensible filename. Prefers query-param 'fileName' when the URL
    path lacks a recognisable extension (Azure DevOps work-item attachments use
    /_apis/wit/attachments/{guid}?fileName=image.png with the real name only
    in the query string).
    """
    parsed = urlparse(url)
    path_name = Path(unquote(parsed.path)).name
    qs_name = ""
    qs = parse_qs(parsed.query)
    for key in ("fileName", "filename", "name"):
        if key in qs and qs[key]:
            qs_name = qs[key][0]
            break

    path_has_ext = bool(Path(path_name).suffix)
    if qs_name and not path_has_ext:
        return qs_name
    if path_name and not path_name.startswith("."):
        return path_name
    if qs_name:
        return qs_name
    return fallback


def find_image_urls(text):
    """Return a list of (alt, url) pairs found in markdown/HTML text."""
    if not text:
        return []
    found = []
    seen = set()

    def add(alt, url):
        url = normalize_url(url)
        if not url or url in seen:
            return
        seen.add(url)
        found.append((alt or "", url))

    for m in MARKDOWN_IMAGE_RE.finditer(text):
        add(m.group(1), m.group(2))
    for m in HTML_IMG_RE.finditer(text):
        add("", m.group(1))
    for m in AZDO_INLINE_ATTACHMENT_RE.finditer(text):
        add("", m.group(0))
    for m in BARE_URL_RE.finditer(text):
        add("", m.group(0))

    return [(alt, url) for alt, url in found if url.startswith(("http://", "https://"))]


def http_get(url, headers, use_default_creds, max_bytes=None, as_bytes=False):
    """Perform an authenticated GET. Returns (status, content_or_json, response_headers)."""
    import requests

    kwargs = {"headers": headers, "stream": True, "timeout": 60}
    if use_default_creds and os.name == "nt":
        try:
            from requests_ntlm import HttpNtlmAuth
            kwargs["auth"] = HttpNtlmAuth("", "")
        except ImportError:
            pass

    response = requests.get(url, **kwargs)
    response.raise_for_status()

    if as_bytes:
        chunks = []
        total = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if max_bytes and total > max_bytes:
                response.close()
                raise RuntimeError(f"Attachment exceeds max size {max_bytes} bytes")
            chunks.append(chunk)
        return response.status_code, b"".join(chunks), dict(response.headers)

    return response.status_code, response.json(), dict(response.headers)


def fetch_thread_list(api_base, config, headers, use_default_creds):
    url = (f"{api_base}/git/repositories/{config['RepoName']}"
           f"/pullrequests/{config['PullRequestId']}/threads"
           f"?api-version={config['AzureApiVersion']}")
    try:
        _, data, _ = http_get(url, headers, use_default_creds)
        return data.get("value", []) if data else []
    except Exception as exc:
        print_warning(f"Failed to fetch PR threads: {exc}")
        return []


def fetch_workitem_with_relations(api_base, work_item_id, api_version, headers, use_default_creds):
    url = (f"{api_base}/wit/workitems/{work_item_id}"
           f"?$expand=relations&api-version={api_version}")
    try:
        _, data, _ = http_get(url, headers, use_default_creds)
        return data
    except Exception as exc:
        print_warning(f"Failed to fetch work item {work_item_id} with relations: {exc}")
        return None


def fetch_workitem_comments(api_base, work_item_id, api_version, headers, use_default_creds):
    """Work item comments endpoint is preview-only; ignore if it 404s."""
    url = (f"{api_base}/wit/workItems/{work_item_id}/comments"
           f"?api-version={api_version}-preview.3")
    try:
        _, data, _ = http_get(url, headers, use_default_creds)
        return data.get("comments", []) if data else []
    except Exception as exc:
        print_warning(f"Could not fetch comments for work item {work_item_id}: {exc}")
        return []


def detect_mime(name, response_headers, sample_bytes):
    declared = (response_headers.get("Content-Type") or "").split(";")[0].strip().lower()
    if declared and declared != "application/octet-stream":
        return declared
    guessed, _ = mimetypes.guess_type(name)
    if guessed:
        return guessed
    if sample_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if sample_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if sample_bytes.startswith(b"GIF87a") or sample_bytes.startswith(b"GIF89a"):
        return "image/gif"
    if sample_bytes[:4] == b"RIFF" and sample_bytes[8:12] == b"WEBP":
        return "image/webp"
    if b"<svg" in sample_bytes[:512]:
        return "image/svg+xml"
    if sample_bytes.startswith(b"%PDF-"):
        return "application/pdf"
    return "application/octet-stream"


def try_image_info(path):
    """Return (width, height, animated) using Pillow if available, else (None, None, False)."""
    try:
        from PIL import Image
    except ImportError:
        return None, None, False
    try:
        with Image.open(path) as img:
            width, height = img.size
            animated = getattr(img, "is_animated", False) and getattr(img, "n_frames", 1) > 1
            return width, height, animated
    except Exception:
        return None, None, False


def extract_gif_keyframes(source_path, target_dir):
    """Save first and middle frames of an animated GIF as PNGs. Returns list of new paths."""
    try:
        from PIL import Image
    except ImportError:
        return []
    paths = []
    try:
        with Image.open(source_path) as img:
            frame_count = getattr(img, "n_frames", 1)
            if frame_count <= 1:
                return []
            indices = sorted({0, frame_count // 2, frame_count - 1})
            for idx in indices:
                img.seek(idx)
                out = target_dir / f"{Path(source_path).stem}.frame-{idx:03d}.png"
                img.convert("RGBA").save(out, "PNG")
                paths.append(out)
    except Exception as exc:
        print_warning(f"GIF keyframe extraction failed for {source_path}: {exc}")
    return paths


def maybe_make_thumbnail(source_path, max_dim=THUMB_MAX_DIM):
    """Down-rescale oversize raster images. Returns thumb path if produced, else None."""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(source_path) as img:
            if max(img.size) <= max_dim:
                return None
            ratio = max_dim / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            out = source_path.with_suffix(source_path.suffix + ".thumb.png")
            img.convert("RGBA").resize(new_size, Image.LANCZOS).save(out, "PNG")
            return out
    except Exception as exc:
        print_warning(f"Thumbnail generation failed for {source_path}: {exc}")
        return None


def decode_data_uri(uri):
    """Decode a data: URI. Returns (mime, bytes) or None."""
    m = re.match(r"data:([^;,]+)(;base64)?,(.*)", uri, re.DOTALL)
    if not m:
        return None
    mime = m.group(1) or "application/octet-stream"
    is_b64 = bool(m.group(2))
    payload = m.group(3)
    try:
        if is_b64:
            data = base64.b64decode(payload)
        else:
            data = unquote(payload).encode("utf-8", errors="replace")
        return mime, data
    except Exception:
        return None


def collect_sources(config, api_base, headers, use_default_creds):
    """Build the list of (source_kind, source_id, comment_id, author, date, text, item_dir_slug) tuples.

    item_dir_slug is the per-source subfolder name under attachments/.
    """
    sources = []

    pr = config.get("PullRequest") or {}
    pr_id = config.get("PullRequestId")

    pr_desc = pr.get("description") or config.get("PullRequestDescription") or ""
    if pr_desc:
        sources.append({
            "kind": "pr-description",
            "sourceId": str(pr_id) if pr_id else "",
            "commentId": "",
            "author": (pr.get("createdBy") or {}).get("displayName", ""),
            "date": pr.get("creationDate", ""),
            "text": pr_desc,
            "dirSlug": "pr-description",
        })

    if pr_id:
        threads = fetch_thread_list(api_base, config, headers, use_default_creds)
        for thread in threads:
            if thread.get("isDeleted"):
                continue
            thread_id = thread.get("id")
            for comment in thread.get("comments", []) or []:
                if comment.get("isDeleted"):
                    continue
                content = comment.get("content") or ""
                if not content.strip():
                    continue
                sources.append({
                    "kind": "pr-comment",
                    "sourceId": f"thread-{thread_id}",
                    "commentId": str(comment.get("id", "")),
                    "author": (comment.get("author") or {}).get("displayName", ""),
                    "date": comment.get("publishedDate") or comment.get("lastUpdatedDate") or "",
                    "text": content,
                    "dirSlug": f"pr-thread-{thread_id}",
                })

    for wid in config.get("WorkItemIds") or []:
        wi = fetch_workitem_with_relations(api_base, wid, config["AzureApiVersion"], headers, use_default_creds)
        if not wi:
            continue

        fields = wi.get("fields", {}) or {}
        wi_desc = fields.get("System.Description") or ""
        wi_repro = fields.get("Microsoft.VSTS.TCM.ReproSteps") or ""
        wi_title = fields.get("System.Title", "")
        wi_text = "\n\n".join(t for t in (wi_desc, wi_repro) if t)

        wi_dir = f"workitem-{wid}"
        if wi_text:
            sources.append({
                "kind": "workitem-description",
                "sourceId": str(wid),
                "commentId": "",
                "author": (fields.get("System.CreatedBy") or {}).get("displayName", ""),
                "date": fields.get("System.CreatedDate", ""),
                "text": wi_text,
                "dirSlug": wi_dir,
                "title": wi_title,
            })

        for rel in wi.get("relations", []) or []:
            if rel.get("rel") != "AttachedFile":
                continue
            url = rel.get("url")
            if not url:
                continue
            attrs = rel.get("attributes") or {}
            sources.append({
                "kind": "workitem-attachment",
                "sourceId": str(wid),
                "commentId": "",
                "author": (attrs.get("authorizedBy") or {}).get("displayName", ""),
                "date": attrs.get("authorizedDate", ""),
                "text": f"![{attrs.get('name', 'attachment')}]({url})",
                "dirSlug": wi_dir,
                "title": wi_title,
            })

        comments = fetch_workitem_comments(api_base, wid, config["AzureApiVersion"], headers, use_default_creds)
        ai_vision_bodies = []
        for c in comments:
            text = c.get("text") or ""
            if not text.strip():
                continue
            if AI_VISION_MARKER in text:
                ai_vision_bodies.append(text)
            sources.append({
                "kind": "workitem-comment",
                "sourceId": str(wid),
                "commentId": str(c.get("id", "")),
                "author": (c.get("createdBy") or {}).get("displayName", ""),
                "date": c.get("createdDate", ""),
                "text": text,
                "dirSlug": wi_dir,
                "title": wi_title,
            })

        if ai_vision_bodies:
            sources.append({
                "kind": "workitem-ai-vision",
                "sourceId": str(wid),
                "commentId": "",
                "author": "",
                "date": "",
                "text": "\n\n---\n\n".join(ai_vision_bodies),
                "dirSlug": wi_dir,
                "title": wi_title,
                "writeAsVisionSummary": True,
            })

    return sources


def main():
    parser = argparse.ArgumentParser(description="Extract PR attachments into a deterministic folder.")
    parser.add_argument("--config", dest="config_path", help="Path to pr-review.json")
    parser.add_argument("--pat", default=os.environ.get("AZDO_PAT", ""),
                        help="Personal Access Token (default: $AZDO_PAT)")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                        help=f"Per-attachment max size (default: {DEFAULT_MAX_BYTES})")
    parser.add_argument("--skip-download", action="store_true",
                        help="Skip downloading; only enumerate and write manifest entries with status=skipped")
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

    print_header("Extract PR Attachments")

    if not config_path.is_file():
        print(f"ERROR: Configuration file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    config = get_review_config(str(config_path))

    for req in ("BaseUrl", "OrganizationName", "ProjectName", "RepoName", "AzureApiVersion"):
        if not config.get(req):
            print(f"ERROR: Missing required config value: {req}", file=sys.stderr)
            sys.exit(1)

    headers, use_default_creds = get_auth_headers(args.pat)
    api_base = f"{config['BaseUrl']}/{config['OrganizationName']}/{config['ProjectName']}/_apis"

    work_folder = Path(get_work_folder(config, root))
    attachments_root = work_folder / "attachments"
    attachments_root.mkdir(parents=True, exist_ok=True)

    print_info(str(attachments_root), "Output folder")
    print()

    sources = collect_sources(config, api_base, headers, use_default_creds)
    print_success(f"Collected {len(sources)} text sources to scan")

    # Build per-folder URL lists + write context files.
    folder_url_index = {}
    folder_ai_vision_text = {}

    for src in sources:
        folder = attachments_root / src["dirSlug"]
        folder.mkdir(parents=True, exist_ok=True)

        if src.get("writeAsVisionSummary"):
            folder_ai_vision_text.setdefault(src["dirSlug"], []).append(src["text"])
            continue

        image_refs = find_image_urls(src["text"])
        if not image_refs:
            continue

        folder_url_index.setdefault(src["dirSlug"], []).append((src, image_refs))

    # Materialize ai-vision-summary.md per folder.
    for slug, bodies in folder_ai_vision_text.items():
        out = attachments_root / slug / "ai-vision-summary.md"
        write_utf8_no_bom(str(out), "\n\n---\n\n".join(bodies) + "\n")
        print_success(f"Wrote {out.relative_to(work_folder)}")

    manifest = {
        "version": 1,
        "extractedAtUtc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pullRequestId": config.get("PullRequestId"),
        "workItemIds": list(config.get("WorkItemIds") or []),
        "totalCount": 0,
        "skipped": 0,
        "attachments": [],
    }
    non_image_log = []
    seen_hashes = {}  # sha256 -> manifest entry (for dedup across folders)
    seen_in_comment = set()  # (sha256, sourceId, commentId) — same image cited twice in one comment is one ref
    counter_per_folder = {}

    for slug, src_entries in folder_url_index.items():
        folder = attachments_root / slug
        for src, image_refs in src_entries:
            # Persist the hosting text once per (src, comment) pair for traceability.
            host_idx = counter_per_folder.get(slug, 0)
            for alt, url in image_refs:
                host_idx += 1
                seq = f"{host_idx:03d}"
                counter_per_folder[slug] = host_idx

                # Handle data: URIs inline.
                if url.startswith("data:"):
                    decoded = decode_data_uri(url)
                    if not decoded:
                        non_image_log.append({"source": src["kind"], "url": "data:...", "reason": "undecodable data URI"})
                        continue
                    mime, content = decoded
                    ext = mimetypes.guess_extension(mime) or ".bin"
                    name = f"img-{seq}{ext}"
                    target = folder / name
                    target.write_bytes(content)
                    response_headers = {"Content-Type": mime}
                else:
                    parsed = urlparse(url)
                    ext = Path(parsed.path).suffix.lower() or ".bin"
                    base_name = filename_from_url(url, f"img-{seq}{ext}")
                    name = f"img-{seq}-{slugify(Path(base_name).stem, fallback='att')}{Path(base_name).suffix.lower() or ext}"
                    target = folder / name

                    if args.skip_download:
                        non_image_log.append({"source": src["kind"], "url": url, "reason": "skip-download flag"})
                        continue

                    try:
                        _, content, response_headers = http_get(
                            url, headers, use_default_creds,
                            max_bytes=args.max_bytes, as_bytes=True,
                        )
                    except Exception as exc:
                        non_image_log.append({"source": src["kind"], "url": url, "reason": f"download failed: {exc}"})
                        print_warning(f"Download failed for {url}: {exc}")
                        continue
                    target.write_bytes(content)

                mime = detect_mime(target.name, response_headers, content[:64])

                if not mime.startswith("image/"):
                    non_image_log.append({
                        "source": src["kind"],
                        "url": url if not url.startswith("data:") else "data:...",
                        "savedAs": str(target.relative_to(work_folder)),
                        "mime": mime,
                        "sizeBytes": len(content),
                    })
                    target.unlink(missing_ok=True)
                    continue

                sha = hashlib.sha256(content).hexdigest()
                same_comment_key = (sha, src["sourceId"], src["commentId"])
                if same_comment_key in seen_in_comment:
                    # Same image referenced twice inside the same comment (e.g. once
                    # in markdown and once in an <img> tag) — collapse silently.
                    target.unlink(missing_ok=True)
                    continue
                seen_in_comment.add(same_comment_key)

                if sha in seen_hashes:
                    # Image already saved under another comment/work-item — drop the
                    # duplicate file but keep a manifest entry pointing at the original
                    # so reviewers see that the same screenshot was attached in
                    # multiple places.
                    target.unlink(missing_ok=True)
                    existing = seen_hashes[sha]
                    manifest["attachments"].append({
                        **{k: v for k, v in existing.items() if k != "id"},
                        "id": f"{slug}-img-{seq}",
                        "source": src["kind"],
                        "sourceId": src["sourceId"],
                        "commentId": src["commentId"],
                        "author": src["author"],
                        "createdDate": src["date"],
                        "altText": alt,
                        "downloadUrl": url,
                        "deduplicatedFrom": existing["id"],
                    })
                    manifest["totalCount"] += 1
                    continue

                width = height = None
                animated = False
                thumb_path = None
                keyframe_paths = []

                if mime != "image/svg+xml":
                    width, height, animated = try_image_info(target)
                    if mime == "image/gif" and animated:
                        keyframe_paths = extract_gif_keyframes(target, folder)
                    if (width and width > THUMB_MAX_DIM) or (height and height > THUMB_MAX_DIM):
                        thumb_path = maybe_make_thumbnail(target)

                context_path = folder / f"{target.stem}.context.md"
                context_lines = [
                    f"# Hosting context for {target.name}",
                    "",
                    f"- Source kind: {src['kind']}",
                    f"- Source id: {src['sourceId']}" + (f" — {src.get('title')}" if src.get("title") else ""),
                ]
                if src["commentId"]:
                    context_lines.append(f"- Comment id: {src['commentId']}")
                if src["author"]:
                    context_lines.append(f"- Author: {src['author']}")
                if src["date"]:
                    context_lines.append(f"- Date: {src['date']}")
                if alt:
                    context_lines.append(f"- Alt text: {alt}")
                context_lines.extend(["", "## Hosting markdown / HTML", "", src["text"].strip()])
                write_utf8_no_bom(str(context_path), "\n".join(context_lines) + "\n")

                meta_path = folder / f"{target.stem}.meta.json"
                meta = {
                    "id": f"{slug}-img-{seq}",
                    "filename": target.name,
                    "mime": mime,
                    "sizeBytes": len(content),
                    "sha256": sha,
                    "width": width,
                    "height": height,
                    "animated": animated,
                    "downloadUrl": url if not url.startswith("data:") else None,
                }
                if thumb_path:
                    meta["thumbnail"] = thumb_path.name
                if keyframe_paths:
                    meta["keyframes"] = [p.name for p in keyframe_paths]
                write_utf8_no_bom(str(meta_path), json.dumps(meta, indent=2, ensure_ascii=False))

                entry = {
                    "id": meta["id"],
                    "source": src["kind"],
                    "sourceId": src["sourceId"],
                    "commentId": src["commentId"],
                    "author": src["author"],
                    "createdDate": src["date"],
                    "imagePath": str(target.relative_to(work_folder)).replace("\\", "/"),
                    "contextPath": str(context_path.relative_to(work_folder)).replace("\\", "/"),
                    "metaPath": str(meta_path.relative_to(work_folder)).replace("\\", "/"),
                    "altText": alt,
                    "mimeType": mime,
                    "width": width,
                    "height": height,
                    "sizeBytes": len(content),
                    "sha256": sha,
                    "downloadUrl": url if not url.startswith("data:") else None,
                }
                if thumb_path:
                    entry["thumbnailPath"] = str(thumb_path.relative_to(work_folder)).replace("\\", "/")
                if keyframe_paths:
                    entry["keyframePaths"] = [
                        str(p.relative_to(work_folder)).replace("\\", "/") for p in keyframe_paths
                    ]
                if src.get("title"):
                    entry["workItemTitle"] = src["title"]

                manifest["attachments"].append(entry)
                seen_hashes[sha] = entry
                manifest["totalCount"] += 1

    manifest_path = attachments_root / "manifest.json"
    write_utf8_no_bom(str(manifest_path), json.dumps(manifest, indent=2, ensure_ascii=False))
    print()
    print_success(f"Manifest: {manifest_path.relative_to(work_folder)} ({manifest['totalCount']} attachments)")

    if non_image_log:
        non_image_path = attachments_root / "non-image-attachments.json"
        write_utf8_no_bom(str(non_image_path), json.dumps(non_image_log, indent=2, ensure_ascii=False))
        print_warning(f"Non-image / failed attachments logged: {non_image_path.relative_to(work_folder)} "
                      f"({len(non_image_log)} entries)")

    print()
    print_header("Attachment Extraction Complete")
    print_info(str(manifest["totalCount"]), "Image attachments")
    print_info(str(len(non_image_log)), "Non-image / failed")
    if folder_ai_vision_text:
        print_info(str(len(folder_ai_vision_text)), "Work items with pre-existing [AI Vision] summary")


if __name__ == "__main__":
    main()
