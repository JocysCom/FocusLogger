#!/usr/bin/env python3
"""Generate combined before-and-after content snapshots for each changed file.

Consolidates per-file diffs and content snapshots into single files for
holistic review. Splits large files into chunks to stay within AI context limits.

Usage:
    python s07_consolidate_diffs_and_content.py [--changed-list PATH]
        [--base-dir DIR] [--changes-dir DIR] [--pre-output PATH]
        [--post-output PATH] [--diffs-dir DIR] [--diffs-output PATH]
"""

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from review_config import (
    get_work_folder, get_workspace_root, print_header, print_info,
    print_success, print_warning, read_text_file, write_utf8_no_bom,
)

CHUNK_SIZE_BYTES = 200000
AI_CONTEXT_LIMIT_BYTES = 300000


def format_size(num_bytes):
    """Format byte count as human-readable size."""
    if num_bytes >= 1_073_741_824:
        return f"{num_bytes / 1_073_741_824:.2f} GB"
    elif num_bytes >= 1_048_576:
        return f"{num_bytes / 1_048_576:.2f} MB"
    elif num_bytes >= 1024:
        return f"{num_bytes / 1024:.2f} KB"
    return f"{num_bytes} bytes"


def split_file_into_chunks(input_path, chunk_size=CHUNK_SIZE_BYTES, output_dir=None):
    """Split a file into smaller chunk files.

    Returns:
        List of chunk file paths.
    """
    input_path = Path(input_path)
    if output_dir is None:
        output_dir = input_path.parent
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = input_path.name
    chunks = []
    part = 0

    with open(input_path, "rb") as f:
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            part += 1
            part_name = f"{base_name}.part{part:03d}"
            out_path = output_dir / part_name
            out_path.write_bytes(data)
            chunks.append(str(out_path.resolve()))

    return chunks


def main():
    parser = argparse.ArgumentParser(
        description="Consolidate diffs and generate before-and-after content snapshots.")
    parser.add_argument("--changed-list", help="Path to changed-files.txt (legacy)")
    parser.add_argument("--base-dir", help="Directory with base file versions")
    parser.add_argument("--changes-dir", help="Directory with changed file versions")
    parser.add_argument("--pre-output", help="Output path for all-pre-content.txt")
    parser.add_argument("--post-output", help="Output path for all-post-content.txt")
    parser.add_argument("--diffs-dir", help="Directory with per-file patches")
    parser.add_argument("--diffs-output", help="Output path for all-diffs.txt")
    args = parser.parse_args()

    scripts_dir = Path(__file__).resolve().parent
    root = get_workspace_root(str(scripts_dir))
    config_path = Path(root) / "pr-review.json"

    import json as json_mod
    with open(config_path, encoding="utf-8") as f:
        raw_config = json_mod.load(f)
    work_folder = Path(get_work_folder(raw_config, root))

    changed_list = Path(args.changed_list) if args.changed_list else work_folder / "diffs" / "changed-files.txt"
    base_dir = Path(args.base_dir) if args.base_dir else work_folder / "base"
    changes_dir = Path(args.changes_dir) if args.changes_dir else work_folder / "changes"
    pre_output = Path(args.pre_output) if args.pre_output else work_folder / "all-pre-content.txt"
    post_output = Path(args.post_output) if args.post_output else work_folder / "all-post-content.txt"
    diffs_dir = Path(args.diffs_dir) if args.diffs_dir else work_folder / "diffs"
    diffs_output = Path(args.diffs_output) if args.diffs_output else work_folder / "all-diffs.txt"

    # Resolve paths
    diffs_dir = diffs_dir.resolve()
    diffs_output = diffs_output.resolve()
    pre_output = pre_output.resolve()
    post_output = post_output.resolve()

    # Remove existing output files
    for f in [pre_output, post_output, diffs_output]:
        if f.exists():
            f.unlink()

    # Initialize empty files
    write_utf8_no_bom(str(diffs_output), "")
    write_utf8_no_bom(str(pre_output), "")
    write_utf8_no_bom(str(post_output), "")

    # Consolidate all patch files
    if not diffs_dir.exists():
        print(f"ERROR: Diffs directory not found: {diffs_dir}", file=sys.stderr)
        sys.exit(1)

    # When s05 detected an empty diff it leaves an EMPTY_DIFF.txt marker. Mirror
    # that into the consolidated artifacts so downstream readers (the AI review
    # prompt, the operator) get a clear "nothing to review" header instead of a
    # zero-byte file.
    empty_marker = diffs_dir / "EMPTY_DIFF.txt"
    if empty_marker.is_file():
        marker_text = read_text_file(str(empty_marker))
        empty_header = (
            "//// EMPTY DIFF — no files changed between base and head\n"
            "//// ----------------------------------------------------\n"
            f"{marker_text}\n"
        )
        write_utf8_no_bom(str(diffs_output), empty_header)
        write_utf8_no_bom(str(pre_output), empty_header)
        write_utf8_no_bom(str(post_output), empty_header)
        print_warning(f"Empty diff detected — wrote marker into consolidated artifacts.")
        print_header("Export Complete")
        return

    write_utf8_no_bom(str(diffs_output), "")

    diffs_content = []
    for patch_file in sorted(diffs_dir.rglob("*.patch")):
        relative = str(patch_file.relative_to(diffs_dir)).replace("\\", "/")
        diffs_content.append(f"//// FILE: {relative}")
        diffs_content.append("//// -------")
        patch_text = read_text_file(str(patch_file))
        diffs_content.append(patch_text)
        diffs_content.append("")

    write_utf8_no_bom(str(diffs_output), "\n".join(diffs_content) + "\n")
    print_success(f"Generated diffs file: {diffs_output}")

    # Chunking index
    chunks_index = {}

    # Split diffs if too large
    if diffs_output.stat().st_size > CHUNK_SIZE_BYTES:
        parts = split_file_into_chunks(diffs_output)
        chunks_index[str(diffs_output)] = parts
        print(f"Split {diffs_output.name} into {len(parts)} parts")

    # Load manifest
    manifest_path = diffs_dir / "changed-files.tsv"
    items = []

    if manifest_path.is_file():
        with open(manifest_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                items.append(row)
    else:
        print(f"Manifest not found ({manifest_path}). Falling back to {changed_list}")
        if changed_list.is_file():
            for line in changed_list.read_text(encoding="utf-8").splitlines():
                parts = line.split(None, 1)
                items.append({
                    "Status": parts[0].strip(),
                    "Path": parts[1].strip() if len(parts) > 1 else parts[0].strip(),
                    "IsBinary": "",
                    "Reason": "",
                    "HeadBytes": "",
                })

    exported_text = 0
    skipped_binary = 0
    listed_total = len(items)

    pre_lines = []
    post_lines = []

    for it in items:
        file = it.get("Path", "")
        is_binary_str = it.get("IsBinary", "")
        is_binary = is_binary_str.lower() == "true" if is_binary_str else False

        if is_binary:
            skipped_binary += 1
            continue

        # Pre content
        pre_lines.append(f"//// FILE: {file}")
        pre_lines.append("//// BEFORE")
        base_path = base_dir / file
        if base_path.is_file():
            base_text = read_text_file(str(base_path))
            pre_lines.append(base_text)
        else:
            pre_lines.append("[File missing or new]")
        pre_lines.append("")

        # Post content
        post_lines.append(f"//// FILE: {file}")
        post_lines.append("//// AFTER")
        post_path = changes_dir / file
        if post_path.is_file():
            post_text = read_text_file(str(post_path))
            post_lines.append(post_text)
        else:
            post_lines.append("[Deleted in feature branch]")
        post_lines.append("")

        exported_text += 1

    write_utf8_no_bom(str(pre_output), "\n".join(pre_lines) + "\n")
    write_utf8_no_bom(str(post_output), "\n".join(post_lines) + "\n")

    print_success(f"Generated pre-content file: {pre_output}")
    print_success(f"Generated post-content file: {post_output}")

    # Split large pre/post files
    for f in [pre_output, post_output]:
        if f.stat().st_size > CHUNK_SIZE_BYTES:
            parts = split_file_into_chunks(f)
            chunks_index[str(f)] = parts
            print(f"Split {f.name} into {len(parts)} parts")

    # Size summary
    diff_bytes = diffs_output.stat().st_size
    pre_bytes = pre_output.stat().st_size
    post_bytes = post_output.stat().st_size

    print()
    print("Artifacts summary (file sizes):")
    print(f"  all-diffs.txt:        {format_size(diff_bytes)}")
    print(f"  all-pre-content.txt:  {format_size(pre_bytes)}")
    print(f"  all-post-content.txt: {format_size(post_bytes)}")
    print(f"  assumed AI context:   ~{format_size(AI_CONTEXT_LIMIT_BYTES)} (conservative default)")
    print()

    print("Split artifacts (part files):")
    for key, parts in chunks_index.items():
        name = Path(key).name
        print(f"  {name} parts ({len(parts)}):")
        for p in parts:
            p_path = Path(p)
            print(f"    - {p_path.name} ({format_size(p_path.stat().st_size)})")

    print()
    print(f"  changed files total:  {listed_total}")
    print(f"  text files exported:  {exported_text}")
    print(f"  binary files skipped: {skipped_binary}")
    if manifest_path.is_file():
        print(f"  manifest:             {manifest_path}")

    # Advisory
    print()
    print("AI advisory:")
    print("  - If the consolidated files exceed your context limit, prefer reading the part files listed above")
    print("    (read part001 -> summarize -> part002 -> summarize -> ...).")
    print("  - If you do not know your context window, assume ~300KB maximum input and choose accordingly.")
    print("  - For diff-centric review, start with all-diffs.txt (or its parts).")
    print("  - For behavior-centric review, use all-pre-content.txt + all-post-content.txt (or their parts).")
    print("  - Consolidated pre/post content excludes binary files (when manifest is present).")
    print("  - Binary files are still represented in the manifest and usually have no textual diff.")
    print(f"  - Use per-file patches under: {diffs_dir} and the manifest to understand binary changes.")

    # Attachments advisory (manifest produced by s03_extract_attachments.py)
    attachments_manifest = work_folder / "attachments" / "manifest.json"
    if attachments_manifest.is_file():
        try:
            with open(attachments_manifest, encoding="utf-8") as f:
                am = json.load(f)
            count = am.get("totalCount", 0)
        except (OSError, json.JSONDecodeError):
            count = 0
        print()
        print("Attachments advisory:")
        print(f"  - {count} user-attached image(s) downloaded by s02b. Read: {attachments_manifest}")
        print("  - For each entry, open its imagePath (multimodal) AND its contextPath (hosting markdown).")
        print("  - Prefer ai-vision-summary.md inside any workitem-* folder when present (pre-extracted).")

    # Write chunks index
    if chunks_index:
        index_obj = {}
        for k, parts in chunks_index.items():
            leaf = Path(k).name
            index_obj[leaf] = parts

        index_path = work_folder / "chunks-index.json"
        write_utf8_no_bom(str(index_path), json.dumps(index_obj, indent=2, ensure_ascii=False))
        print_success(f"Wrote chunks index: {index_path}")

        # Validate chunks
        for name, parts in index_obj.items():
            for p in parts:
                size = Path(p).stat().st_size
                if size > CHUNK_SIZE_BYTES:
                    print_warning(f"chunk {p} exceeds {CHUNK_SIZE_BYTES} bytes: {size}")

    print()
    print_header("Export Complete")
    print_success(f"Listed changed files:    {listed_total}")
    print_success(f"Exported text snapshots: {exported_text}")
    print(f"Skipped binary snapshots:{skipped_binary}")


if __name__ == "__main__":
    main()
