---
name: repo-documentation-gatherer
description: Gather, improve, and curate repository documentation and wiki content. Use when asked to update, analyze, or modify WIKI instructions/documentation, or when asked to pull an external wiki snapshot into the repo and curate repo-relevant knowledge into a committed, searchable knowledge base under `.ai/wiki/`.
---

# Repo Documentation Gatherer (Wiki Improvement)

## Goal

Keep the external wiki as the source of truth, but make its **repo-relevant** knowledge usable inside this code-repo workspace by maintaining:

- a **raw snapshot** under `.ai/Temp/wiki/` (not committed)
- a **curated, repo-local KB** under `.ai/wiki/` (committed, AI-managed)

The repo-local KB must **copy** relevant content into `.ai/wiki/` so it is indexable by repo tooling (RAG). Do **not** rely on links back to the external wiki for the actual guidance content.

**Expectation:** curate *broadly* across the snapshot.

**Required:** build an explicit review checklist of *all* snapshot markdown pages (`.ai/Temp/wiki/**/*.md`) and work through it; do not skim only a small subset.

## Default behaviour (no questions)

When asked to update wiki documentation, do this **without asking questions**:

1. Refresh snapshot: run `.ai/skills/repo-documentation-gatherer/tools/PullWikiIntoTemp.ps1` to materialize the wiki under `.ai/Temp/wiki/`.
   - Note: The script already knows which WIKI to pull.
2. Inventory the snapshot (required): generate a complete list of snapshot markdown pages and use it as the checklist.

   **Command (PowerShell):**

   ```powershell
   Get-ChildItem -Path .ai/Temp/wiki -Recurse -Filter *.md -File | Select-Object -ExpandProperty FullName
   ```

   - Paste this list into the PR/notes and work through it.
   - Use `.order` files (when present) to follow intended reading order.
3. Curate: mirror a minimal subset of the wiki structure under `.ai/wiki/` and **copy** repo-relevant content into matching KB markdown files.
   - Keep filenames and headings aligned with the snapshot where possible.
   - Do **not** collapse everything into a single file unless the snapshot itself is tiny.

Do not ask clarifying questions about scope, target pages, or desired outcomes. Assume the task is: refresh the snapshot and curate repo-relevant content into the KB.

Only ask questions if the workflow is blocked (e.g., missing git credentials/access, missing script, or the snapshot cannot be pulled).

## What is repo-relevant (generic)

Treat content as repo-relevant if it enables work **in this repository**.

A section is repo-relevant if it answers any of these:

- What is this repo for and who uses it?
- How to build/run/test/debug/deploy/release this repo
- Repo-specific conventions and workflows (branching/versioning, environment names, generators, directory layout)
- Required external dependencies and how to configure them locally (databases, SSO, secrets sources, URLs/ports)
- Common troubleshooting and operational runbooks

The parent wiki may contain non-coding content (process, product, domain). Curate it only when it affects working with, operating, or changing **this repo**.

### What to extract (priority order)

Extract, in order:

1. Entry points (where to start, key concepts, how to navigate)
2. Build/run/test primitives (prefer repo-owned scripts and commands as SSOT)
3. Local environment & configuration (env names, required services, ports/URLs, where secrets come from)
4. Release/deploy workflow (steps, smoke checks, rollbacks)
5. Repo conventions (branching/versioning, structure, generators)
6. Troubleshooting (common failures and known fixes)

Do not extract secrets, credentials, or customer-sensitive data.

## KB output requirements (inside this repo)

### Required entry point

The KB must contain `.ai/wiki/index.md` as the **entry point**.

### Structure (required)

- Mirror a minimal subset of the snapshot structure under `.ai/wiki/` (e.g., `Illuminate/`, `Coding-Guidelines/`, `Accessibility/`).
- Create one KB markdown per snapshot page you extract from (copy relevant sections into the matching path).
- Keep `.ai/wiki/index.md` as a short table-of-contents linking to the curated KB pages.
- Remove/rename superseded KB files in the same change (no duplicates).

### Content style

Write short, actionable guidance (checklists and commands). Prefer distillation, but keep the guidance content itself inside `.ai/wiki/` (copy from the snapshot and distill there). Do not link back to the external wiki for long details; instead, copy any repo-relevant details that must be searchable.

Keep `.ai/wiki/` in sync with the snapshot: if content is removed or materially changed in the external wiki snapshot, remove/update it in `.ai/wiki/` in the same change.

Do not add any repo-derived facts, assumptions, or helpful background that is not explicitly present in the external wiki snapshot; when unsure, omit rather than invent.
