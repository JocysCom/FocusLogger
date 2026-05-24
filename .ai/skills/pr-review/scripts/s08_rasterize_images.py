#!/usr/bin/env python3
"""Rasterize diagram blocks in review.md to PNG files on disk.

Scans {WorkFolder}/review.md for fenced ```mermaid blocks and renders each
to {WorkFolder}/diagrams/diagram-NNN.png using the Mermaid CLI (mmdc).
Writes a manifest linking each block (and its content hash) to its rendered
PNG so s09_upsert_review_attachments.py can upload + substitute later.

OFFLINE: this script performs no network or PR API calls. It is safe to run
unconditionally even when SKIP_POST_COMMENT=1.

The review.md file is NOT modified here — fences stay as ```mermaid. URL
substitution happens in s09_upsert_review_attachments.py.

Idempotency: blocks with an unchanged content sha256 reuse the existing PNG
on re-runs. Stale PNGs from previous runs (no matching block in current
review.md) are removed.

Usage:
    python s08_rasterize_images.py [--config PATH] [--review PATH]
        [--scale N] [--background-color COLOR] [--mmdc PATH]
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_config import (
    get_review_config, get_work_folder, get_workspace_root,
    print_header, print_info, print_success, print_warning, write_utf8_no_bom,
)

MERMAID_FENCE_RE = re.compile(r"```mermaid\s*\n(.*?)\n```", re.DOTALL)


def find_mmdc(explicit_path=None):
    """Locate the mermaid-cli binary. Returns absolute path or None."""
    if explicit_path:
        p = Path(explicit_path)
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
    found = shutil.which("mmdc")
    if found:
        return found
    # npm-global on the agent container puts mmdc at /usr/bin/mmdc; locally
    # devs may have it under their npm prefix. shutil.which already covers
    # PATH so this is just a final guess for common Windows installs.
    for candidate in ("/usr/bin/mmdc", "/usr/local/bin/mmdc"):
        if Path(candidate).is_file():
            return candidate
    return None


def ensure_puppeteer_sandbox_config():
    """Create the no-sandbox config mmdc needs when running headless in Linux.

    Containers don't allow user-namespace cloning; without --no-sandbox,
    Chromium crashes on launch. We write the config file once at /tmp and
    pass --puppeteerConfigFile every render.
    """
    cfg = Path("/tmp/mermaid-puppeteer.json") if os.name != "nt" else None
    if cfg is None:
        return None
    try:
        if not cfg.is_file():
            cfg.write_text('{"args":["--no-sandbox","--disable-setuid-sandbox"]}', encoding="utf-8")
        return str(cfg)
    except OSError:
        return None


def render_mermaid(mmdc, mmd_path, png_path, scale, background, puppeteer_cfg):
    """Run mmdc to produce png_path from mmd_path. Returns (success, stderr)."""
    cmd = [
        mmdc,
        "-i", str(mmd_path),
        "-o", str(png_path),
        "--scale", str(scale),
        "--backgroundColor", background,
    ]
    if puppeteer_cfg:
        cmd += ["--puppeteerConfigFile", puppeteer_cfg]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "mmdc exited non-zero").strip()
    if not Path(png_path).is_file():
        return False, "mmdc produced no PNG output"
    return True, ""


def main():
    parser = argparse.ArgumentParser(description="Rasterize ```mermaid blocks in review.md to PNGs.")
    parser.add_argument("--config", dest="config_path", help="Path to pr-review.json")
    parser.add_argument("--review", dest="review_path", help="Path to review.md")
    parser.add_argument("--scale", type=int, default=2, help="mmdc render scale (default: 2)")
    parser.add_argument("--background-color", default="white",
                        help="mmdc background color (default: white)")
    parser.add_argument("--mmdc", help="Explicit path to mmdc binary (overrides PATH lookup)")
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    root = get_workspace_root(str(scripts_dir))
    config_path = Path(args.config_path) if args.config_path else Path(root) / "pr-review.json"

    if not config_path.is_file():
        print(f"ERROR: Configuration file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    print_header("Rasterize Diagrams")

    config = get_review_config(str(config_path))
    work_folder = Path(get_work_folder(config, root))
    review_path = Path(args.review_path) if args.review_path else work_folder / "review.md"

    if not review_path.is_file():
        print(f"ERROR: review.md not found at: {review_path}", file=sys.stderr)
        sys.exit(1)

    content = review_path.read_text(encoding="utf-8")
    blocks = MERMAID_FENCE_RE.findall(content)
    if not blocks:
        print_success("No ```mermaid blocks in review.md — nothing to rasterize.")
        # Still write an empty manifest so s09 can rely on its presence.
        diagrams_dir = work_folder / "diagrams"
        diagrams_dir.mkdir(parents=True, exist_ok=True)
        write_utf8_no_bom(str(diagrams_dir / "mermaid-manifest.json"),
                          json.dumps({"version": 1, "totalCount": 0, "diagrams": []},
                                     indent=2, ensure_ascii=False))
        return

    diagrams_dir = work_folder / "diagrams"
    diagrams_dir.mkdir(parents=True, exist_ok=True)

    mmdc = find_mmdc(args.mmdc)
    if not mmdc:
        print_warning("mmdc (mermaid-cli) not found on PATH. ```mermaid blocks will not render. "
                      "Install via: npm install -g @mermaid-js/mermaid-cli")
        # Write an empty manifest; review.md stays unchanged. n8n/s10 will post
        # the review with raw ```mermaid fences. Better than failing the run.
        write_utf8_no_bom(str(diagrams_dir / "mermaid-manifest.json"),
                          json.dumps({"version": 1, "totalCount": 0, "diagrams": [],
                                      "warning": "mmdc not available"},
                                     indent=2, ensure_ascii=False))
        return

    puppeteer_cfg = ensure_puppeteer_sandbox_config()

    # Index existing PNGs so we can reuse hashed ones and remove stale ones.
    existing = {p.name: p for p in diagrams_dir.glob("diagram-*.png")}
    kept = set()

    manifest = {
        "version": 1,
        "extractedAtUtc": "",
        "totalCount": 0,
        "failed": 0,
        "diagrams": [],
    }

    for index, source in enumerate(blocks, start=1):
        source = source.strip()
        sha = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
        png_name = f"diagram-{index:03d}-{sha}.png"
        png_path = diagrams_dir / png_name

        if png_path.is_file():
            # Same content already rendered.
            print_info(png_name, f"  [{index:03d}] reused")
            manifest["diagrams"].append({
                "index": index,
                "sha256": sha,
                "png": png_name,
                "blockText": source,
            })
            manifest["totalCount"] += 1
            kept.add(png_name)
            continue

        with tempfile.NamedTemporaryFile("w", suffix=".mmd", delete=False, encoding="utf-8") as tf:
            tf.write(source)
            mmd_tmp = tf.name

        try:
            ok, err = render_mermaid(mmdc, mmd_tmp, png_path, args.scale,
                                     args.background_color, puppeteer_cfg)
        finally:
            try:
                Path(mmd_tmp).unlink(missing_ok=True)
            except OSError:
                pass

        if not ok:
            # Print the full error to STDOUT (not just stderr) so the failure
            # is visible in the n8n SSH command output rather than buried in a
            # separate stderr stream. Execution 3878 had mmdc dying on a
            # missing Chrome binary, but the stdout summary just said
            # "Rendered diagrams: 0" — the actual reason ("Could not find
            # Chrome (ver. 148.0.7778.97)") only appeared on stderr.
            err_short = err.splitlines()[0] if err else "unknown"
            err_full = err.strip() if err else "(no stderr captured)"
            print(f"  [{index:03d}] mmdc FAILED: {err_short}")
            if err_full and err_full != err_short:
                for line in err_full.splitlines()[1:8]:  # first ~8 lines
                    print(f"            {line}")
            chrome = os.environ.get("PUPPETEER_EXECUTABLE_PATH", "(unset)")
            print(f"            PUPPETEER_EXECUTABLE_PATH={chrome}")
            print_warning(f"  [{index:03d}] mmdc failed: {err_short}")
            manifest["failed"] += 1
            manifest["diagrams"].append({
                "index": index,
                "sha256": sha,
                "png": None,
                "blockText": source,
                "error": err_short,
                "errorFull": err_full,
            })
            continue

        print_success(f"  [{index:03d}] rendered {png_name} ({png_path.stat().st_size} bytes)")
        manifest["diagrams"].append({
            "index": index,
            "sha256": sha,
            "png": png_name,
            "blockText": source,
        })
        manifest["totalCount"] += 1
        kept.add(png_name)

    # Remove stale PNGs from previous runs.
    for name, path in existing.items():
        if name not in kept:
            try:
                path.unlink()
                print_info(name, "  stale removed")
            except OSError:
                pass

    from datetime import datetime, timezone
    manifest["extractedAtUtc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    manifest_path = diagrams_dir / "mermaid-manifest.json"
    write_utf8_no_bom(str(manifest_path), json.dumps(manifest, indent=2, ensure_ascii=False))

    print()
    print_info(str(manifest["totalCount"]), "Rendered diagrams")
    if manifest["failed"]:
        print_warning(f"Failed: {manifest['failed']}")
    print_header("Rasterization Complete")


if __name__ == "__main__":
    main()
