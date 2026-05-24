---
name: pr-review
description: AI-assisted pull request review workflow for Azure DevOps Git repositories. Use when the user asks to review a pull request, perform a PR review, analyse PR changes, or run the PR review pipeline. Provides a complete scripted workflow to fetch PR metadata, prepare a local branch folder, export diffs, generate review reports and checklists, and post review comments back to Azure DevOps. Requires Python 3.9+ and Git.
---

# AI Pull Request Review Agent SOP (Azure DevOps + Python)

Purpose-built standard operating procedures and minimal workspace structure for an AI-assisted PR review workflow targeting Azure DevOps Git repositories using Python as the cross-platform scripting language.

For script invocation guidance, see [references/tool-instructions.md](references/tool-instructions.md).

1. Objectives

   - Provide a reproducible, minimal workspace for offline PR review artifacts.
   - Fetch and normalize diffs and changed files against a base branch.
   - Drive a consistent, checklist-led review that is easy to audit.
   - Keep authentication safe and avoid leaking PATs or secrets into logs.
   - Always confirm the existence of `pr-review.json` by first calling list_files on the workspace directory before using read_file or asking follow-up questions. This prevents assumptions about its presence.

2. Workspace layout

   The repository is organized into the following structure:

   ```text
   .
   ├── pr-review.json                      Read-only user configuration (NEVER modified)
   ├── .ai/
   │   └── skills/
   │       └── pr-review/
   │           ├── SKILL.md                         This SOP file
   │           ├── scripts/                         Python workflow scripts
   │           │   ├── review_config.py             Helper module for merged configuration
   │           │   ├── invoke_build.py              Cross-platform build wrapper (dotnet msbuild / MSBuild)
   │           │   ├── Setup_Util_TrustedRootCertificates_Save.ps1  Windows corporate cert helper
   │           │   ├── s01_reset_workspace.py       Clean previous review artifacts
   │           │   ├── s02_get_azure_devops_info.py Fetch PR and work item metadata
   │           │   ├── s03_extract_attachments.py   Download images from PR/work-item comments + descriptions
   │           │   ├── s04_fetch_repository.py      Prepare BranchFolder and fetch branches when PullBranch is true
   │           │   ├── s05_reset_templates.py       Create review templates with actual PR data
   │           │   ├── s06_export_diff_artifacts.py Export per-file diffs and changed files
   │           │   ├── s07_consolidate_diffs_and_content.py Consolidate patches and snapshots
   │           │   ├── s08_rasterize_images.py      Render ```mermaid blocks to PNG (offline, no upload)
   │           │   ├── s09_upsert_review_attachments.py Upload diagrams + local images to PR attachments
   │           │   ├── s10_upsert_review_comment.py Post review comment to Pull Request
   │           │   ├── s11_upsert_pr_description.py Upsert PR description (guarded; refuses to overwrite real content)
   │           │   └── s12_upsert_suggestion_threads.py Post suggestion threads to Pull Request
   │           ├── assets/                          Templates (SSOT)
   │           │   ├── review.template.md           Template for review.md
   │           │   ├── checklist.template.md        Template for checklist.md
   │           │   └── config.template.json         Template for pr-review.json
   │           └── references/
   │               └── tool-instructions.md         Python invocation rules
   └── {WorkFolder}/                    Configurable via WorkFolder in pr-review.json
       ├── review.md                    Consolidated findings and verdict (generated)
       ├── checklist.md                 Checklist and scoring rubric (generated)
       ├── pr-description.md            Brief PR description (generated; posted only when original PR description is empty)
       ├── diagrams/                    Optional generated images (when GenerateImages: true)
       ├── attachments/                 Screenshots from PR + work items (written by s02b; see manifest.json)
       ├── context.json                 Dynamic Azure DevOps data (written by scripts)
       ├── meta.json                    Git repository metadata (written by scripts)
       ├── changes/                     Working tree copies of changed files
       ├── diffs/                       Per-file unified diff patches (path.patch)
       ├── base/                        Optional base versions of changed files
       └── branch/                      Default local PR branch folder when BranchFolder is not `.`
   ```

3. PR configuration and file structure

   The configuration system uses three separate files to maintain clean separation between user input, fetched data, and Git metadata:

   **pr-review.json** - Read-only user configuration (root of workspace)
   - This file is NEVER modified by scripts
   - Can be version controlled without dynamic data
   - Should contain as little as possible. Scripts derive Azure DevOps values from the current Git checkout first, then ask the user only for values that cannot be derived.
   - Default derived values:
     - `BaseUrl`, `OrganizationName`, `ProjectName`, and `RepoName` are parsed from `git remote get-url origin` for Azure DevOps HTTPS or SSH remotes.
     - `BranchName` is derived from the current Git branch.
     - `TargetBranchName` is derived from `origin/HEAD` and falls back to `master`.
     - `PullRequestId` is optional. If omitted, `s02_get_azure_devops_info.py` finds the active PR whose source branch is the current branch. If none or multiple active PRs are found, the workflow stops with a clear message and asks for `PullRequestId`.
     - `WorkItemIds` is optional. If omitted, `s02_get_azure_devops_info.py` reads linked work items from the PR.
     - `AzureApiVersion` defaults to `7.1`.
     - `WorkFolder` defaults to `.tmp/pr-review`.
     - `PullBranch` defaults to `false` and `BranchFolder` defaults to `.` so reviewing the current branch is the default workflow.
   - Optional override fields:
     - `BaseUrl`, `OrganizationName`, `ProjectName`, `RepoName` - only set these when the Git remote cannot be parsed.
     - `PullRequestId` - only set this when multiple/no active PRs are found for the current branch.
     - `WorkItemIds` - only set this when PR work item links are absent or incomplete.
     - `BranchName`, `TargetBranchName` - only set these when Git branch/default-branch detection is wrong.
     - `PullBranch` - set to `true` only when the scripts should clone/fetch the PR branch into a disposable checkout.
     - `BranchFolder` - local repository folder for the PR branch; use `.` to review the current workspace branch, or `.tmp/pr-review/branch` for a disposable checkout.
     - `BranchPath` - legacy alias for `BranchFolder`; prefer `BranchFolder` for new configurations.
     - `GenerateImages` - set to `true` to allow `ai-image-generation` to produce at most one image per PR when the AI judges a real picture (mockup, before/after, conceptual sketch) would meaningfully help. Default: `false`. Mermaid diagrams are always allowed regardless of this flag.
     - `ReviewAgentUrl` - URL of the review agent's home (typically a `.ai/skills/pr-review` link on the repository hosting the skill); used to expand `{review_agent_url}` inside `ReviewCommentHeader`.
     - `ReviewCommentHeader` - Markdown line(s) prepended below the mandatory `[AI Review]` tag when n8n posts the review as a PR comment. Supports the `{review_agent_url}` placeholder.

   All artifact paths below (context.json, meta.json, review.md, diffs/, etc.) are relative to the configured `WorkFolder`. `BranchFolder` is resolved relative to the repository root unless it is absolute.

   **{WorkFolder}/context.json** - Dynamic Azure DevOps data (written by s02_get_azure_devops_info.py)
   - Created/updated by `s02_get_azure_devops_info.py`
   - Cleaned by `s01_reset_workspace.py`
   - Contains fetched PR and work item details:
     - `BranchName`, `TargetBranchName` - Branch names from PR or Git-derived defaults
     - `PullRequestId`, `PullRequestTitle`, `PullRequestDescription`, `PullRequestStatus`
     - `PullRequestCreatedBy`, `PullRequestCreatedDate`
     - `WorkItemTitle`, `WorkItemType`, `WorkItemState`, `WorkItemAssignedTo` (based on first Work Item)
     - `PullRequest` - Full PR API response object
     - `WorkItems` - Full work item API response objects
     - `WorkItem` - First work item object (for backward compatibility)

   **{WorkFolder}/meta.json** - Git repository metadata (written by s04_fetch_repository.py)
   - Created/updated by `s04_fetch_repository.py`
   - Cleaned by `s01_reset_workspace.py`
   - Contains Git-specific information for the prepared branch folder:
     - `baseCommit`, `featureCommit` - Commit SHAs
     - `timestamp` - When repository was fetched
     - `workDir` - Local repository path resolved from `BranchFolder`
     - `baseRef`, `featureRef` - Git refs used for diff export (`featureRef` is `HEAD` when `PullBranch` is `false`)
     - `pullBranch` - Effective branch-pulling mode used by `s04_fetch_repository.py`
   - Note: Branch names originate from {WorkFolder}/context.json (single source of truth from Azure DevOps API) and are copied into metadata with the effective Git refs.

   **Configuration Merging:**
   Scripts automatically derive Git/Azure DevOps defaults, then merge pr-review.json + {WorkFolder}/context.json using the `review_config.py` helper module. Context values take precedence over config values, allowing runtime overrides.

4. Prerequisites

   - Python 3.9 or newer
   - Git 2.35 or newer with Git Credential Manager enabled
   - .NET SDK (for building solutions via `invoke_build.py`)
   - Access to Azure DevOps repositories
   - Install dependencies: `pip install -r .ai/skills/pr-review/scripts/requirements.txt`
   - Current Python dependencies include `requests` and `requests-ntlm` because the Windows Integrated Authentication fallback uses NTLM helpers when no PAT or Azure CLI token is available

   Authentication methods (scripts try in this order):

   1. **Personal Access Token (PAT)** - Set `AZDO_PAT` environment variable with a PAT that has Code (Read) scope. Works on all platforms.
   2. **Azure CLI** - Uses `az account get-access-token` if Azure CLI is installed and authenticated. Cross-platform.
   3. **Windows Integrated Authentication** - Final fallback for domain-joined Windows machines.

5. Quick start using scripts

   Use the Python scripts in the `.ai/skills/pr-review/scripts/` directory to prepare the workspace and export diffs and changed files. Scripts are prefixed with execution order (s01, s02, etc.). Run them in the following order:

   Run each script as a separate command and wait for it to finish before invoking the next script. Do not chain multiple scripts together on a single command line.

   - `python .ai/skills/pr-review/scripts/s01_reset_workspace.py` - Clean previous review artifacts
   - `python .ai/skills/pr-review/scripts/s02_get_azure_devops_info.py` - Fetch PR and work item metadata
   - `python .ai/skills/pr-review/scripts/s03_extract_attachments.py` - Download attached images from PR + linked work items into `{WorkFolder}/attachments/`
   - `python .ai/skills/pr-review/scripts/s04_fetch_repository.py` - Prepare the local branch folder; clones/fetches only when `PullBranch` is `true`
   - `python .ai/skills/pr-review/scripts/s05_reset_templates.py` - Create review templates with actual data
   - `python .ai/skills/pr-review/scripts/s06_export_diff_artifacts.py` - Export diffs and changed files
   - `python .ai/skills/pr-review/scripts/s07_consolidate_diffs_and_content.py` - Consolidate patches and generate before-and-after content snapshots
   - **AI writes `{WorkFolder}/review.md` with findings**
   - `python .ai/skills/pr-review/scripts/s08_rasterize_images.py` - Render ```mermaid blocks in review.md to PNGs (offline, always safe)
   - `python .ai/skills/pr-review/scripts/s09_upsert_review_attachments.py` - Upload diagrams + local images to PR; rewrite review.md (skipped when `SKIP_POST_COMMENT=1`)
   - `python .ai/skills/pr-review/scripts/s10_upsert_review_comment.py` - Upsert review comment to Pull Request

   ## Attachments

   If `{WorkFolder}/attachments/manifest.json` exists with `totalCount > 0`, the PR (or a linked work item) carries screenshots. For each entry: open `imagePath` (multimodal), read `contextPath` (why it was attached). Treat any `ai-vision-summary.md` inside a `workitem-*/` folder as authoritative unless the image contradicts it. Cite findings with the attachment path (e.g. `Source: attachments/workitem-238853/img-001-image.png`). A screenshot that documents a bug the diff doesn't fix is a Blocker.

   ## Analysis Preparation

   After running the scripts above, decide what to load based on *your available context window*.

   - If you do **not** know your context limit, assume a conservative budget of **~300KB** total input.
   - Check the output of `python .ai/skills/pr-review/scripts/s07_consolidate_diffs_and_content.py` — it prints:
     - consolidated artifact sizes, and
     - the split **part files** (names + sizes) when an artifact was too large.

   Recommended loading strategy:

   1. If it fits, load [`{WorkFolder}/all-pre-content.txt`]({WorkFolder}/all-pre-content.txt:1) (before) then [`{WorkFolder}/all-post-content.txt`]({WorkFolder}/all-post-content.txt:1) (after).
   2. If pre/post does not fit, load **part files** in order and summarize incrementally:
      - `{WorkFolder}/all-pre-content.txt.part001` → summarize → `...part002` → summarize → ...
      - then `{WorkFolder}/all-post-content.txt.part001` → summarize → ...
   3. For a diff-centric overview, load [`{WorkFolder}/all-diffs.txt`]({WorkFolder}/all-diffs.txt:1) or its parts instead of pre/post.

   Use per-file patches under `{WorkFolder}/diffs/**` or files under `{WorkFolder}/changes/**` only when you need to zoom into specific files.

   Refer to each script's `--help` for usage details.

6. Review flow
    - Think through upcoming steps deliberately and verify instructions (e.g., consult .github/copilot-instructions.md) before executing commands.
    - Prepare workspace using the quick start scripts. The s01_reset_workspace.py script cleans artifacts, then s02_get_azure_devops_info.py fetches PR data, then s03_extract_attachments.py downloads PR + work-item attachments into `{WorkFolder}/attachments/`, then s04_fetch_repository.py prepares `BranchFolder` and writes Git metadata, then s05_reset_templates.py creates {WorkFolder}/review.md and {WorkFolder}/checklist.md from their respective template files with actual PR data.
    - When `PullBranch` is `false`, `BranchFolder` is treated as the already checked-out PR branch and the head ref is `HEAD`; set `BranchFolder` to `.` to review the current workspace branch.
    - If present, read `.github/copilot-instructions.md` from the target repository (`BranchFolder`) and incorporate any guidance it contains into the review process, such as which projects to test.
    - Load {WorkFolder}/all-pre-content.txt – full "before" state of all changed files
    - Load {WorkFolder}/all-post-content.txt – full "after" state of all changed files
    - Use {WorkFolder}/all-diffs.txt – concise summary of changed lines and statuses
    - Skim {WorkFolder}/diffs/changed-files.tsv to understand scope.
    - Read per-file patches under {WorkFolder}/diffs and the corresponding working files under {WorkFolder}/changes.
    - Restore/build the solution **as a best-effort sanity check, not a gate**:
      - Pick the build target deterministically:
        - When both `.slnx` (modern XML format) and `.sln` (legacy INI format) exist with the same stem, **always use the `.slnx`** — it is the source of truth in repositories that have started migrating. `invoke_build.py` enforces this automatically when given a `.sln` with a sibling `.slnx`.
        - When only one of `.slnx` / `.sln` exists at the repo root, use it.
        - When no solution exists, build the most relevant changed project (`.csproj`/`.vbproj`/`.fsproj`).
      - Always invoke builds through `invoke_build.py` rather than bare `dotnet restore` / `dotnet build`. The wrapper rewrites the recorded project paths in the local clone so they match on-disk casing — necessary for Windows-authored solutions on case-sensitive Linux filesystems (e.g. `.sln` says `Web.Core/Web.Core.csproj` but git wrote `Web.Core/web.core.csproj`). Bare `dotnet` commands skip that pass and fail with "project not found" on those repos. The rewrites live in the disposable clone and never travel back to origin.
      - Restore first (prevents NETSDK1004 missing project.assets.json during MSBuild):
        - `python .ai/skills/pr-review/scripts/invoke_build.py {solution|project} /t:Restore`
      - Then build:
        - `python .ai/skills/pr-review/scripts/invoke_build.py {solution|project} /v:minimal /clp:Summary`
        - The build wrapper resolves the first argument to an absolute path before invoking MSBuild so the command works reliably when launched from the repository root on Windows
      - Note: `invoke_build.py` uses `dotnet msbuild` cross-platform, with full MSBuild via vswhere on Windows as an optimization for multi-targeting solutions

    - **Build/test is a best-effort sanity check, NOT a review gate.** A code review is still valuable when the local build can't be reproduced. If restore / build / test fails because of any of the following, record exactly what failed in the `## Testing` section of `review.md` (one or two lines, no apology, no retries past three attempts) and continue with the diff-level analysis:
        - Private package feeds the container can't reach or authenticate against (`pkgs.dev.azure.com/...` without `AZDO_PAT` wired, `npmjs.org/@scope` packages, Artifactory, etc.). When `AZDO_PAT` is set, the container auto-wires Azure DevOps Artifacts auth at clone time via `VSS_NUGET_EXTERNAL_FEED_ENDPOINTS` + PAT-injected `.npmrc`; if that didn't happen the env var is missing or the cloned repo references a non-Azure-DevOps feed.
        - Network blocks on public registries (`api.nuget.org`, `registry.npmjs.org`) — proxy / firewall / TLS-inspection issues. The container's smoke tests at install time validate these endpoints; if they passed at install but fail now, the proxy state changed.
        - SDK / toolchain extras the project assumes are installed globally (NSwag CLI, EF Core tools, Angular CLI, etc.). The agent container ships .NET / Python / Node / pwsh / Codex CLI / Claude Code CLI / Playwright Chromium and nothing else.
        - Write-blocked default paths (e.g. `~/.dotnet`, `~/.nuget`, `~/.npm`). The container pre-creates these under the `agent` user's home in `container-init.sh` and exports `DOTNET_CLI_HOME`, `NUGET_PACKAGES`, `npm_config_cache` so most tools land in writable dirs without configuration. If a tool still hits a write block, redirecting it to `/tmp` is acceptable for this review run.
      Do not pursue project-specific build fixes (renaming a file, editing the slnx, removing a ProjectReference) just to make the build pass — the PR is the source of truth, and a "review" that depends on edits the author hasn't approved is unverifiable.
    - Based on guidance (e.g., copilot-instructions or changed projects), find and run the most directly related automated tests you can identify; widen scope only as risk requires.
      - Prefer repository-specific conventions first (existing test projects, test roots, framework config, and naming patterns).
      - Use one canonical mirror pattern as the first guess for both locating related tests and suggesting new ones when the repo does not expose a stronger convention:
        - Code: `{repo_path}/{project_name_path}/{code_path}/{source_name}.{source_ext}`
        - Test: `{repo_path}/Tests/{project_name_path}.Tests/{code_path}/{source_name}{test_suffix}`
        - Mirror `{code_path}` exactly under the test project.
        - Keep `{project_name_path}` stable and append `.Tests`.
        - Choose `{test_suffix}` from the source language or the repo's dominant test framework convention.
        - If the repo has a generic source container such as `src`, `Source`, `app`, or `lib`, treat that container as outside `{project_name_path}` and do not mirror it under `Tests`.
        - Default `{test_suffix}` values:
          - C#: `Tests.cs`
          - TypeScript/JavaScript: `.test.ts`, `.test.tsx`, `.test.js`, or `.test.jsx`
          - Python: `_test.py`
          - Go: `_test.go`
          - Java/Kotlin: `Test.java` or `Test.kt`
        - Example: `Repo/src/Payments/Calculations/VatCalculator.cs` -> `Repo/Tests/Payments.Tests/Calculations/VatCalculatorTests.cs`
        - Example: `Repo/web/components/Button.tsx` -> `Repo/Tests/web.Tests/components/Button.test.tsx`
      - Existing codebases often contain older tests that do not follow the canonical pattern. Use the canonical pattern as the first guess, then search for nearby deviations before concluding that no related tests exist:
        - mirror-path candidates in existing test locations
        - test files or projects named after the changed class, component, module, route, or feature
        - broader integration or UI tests only when the change crosses boundaries that unit or component tests cannot cover confidently
      - Record the exact test commands you ran and whether they passed, failed, or were blocked.
      - If no suitable automated tests exist, say so explicitly and recommend the smallest durable set of new tests that covers stable behaviour rather than the PR diff itself.
        - For each recommendation, specify the test type (for example unit, integration, UI, data, calculation), the behaviour to cover, and the most likely file or project path where it should be created, using the canonical mirror pattern unless the repo clearly uses another established layout.
        - Prefer broad, reusable regression tests over narrow temporary tests.
    - Capture findings into `{WorkFolder}/review.md` by **copying the exact structure of `assets/review.template.md`** — do NOT invent sections, rename headings, or reorder. The template is the contract.

      **MANDATORY section order (top → bottom):**

      1. `# AI Review report` (title, only once)
      2. Risk and Confidence on separate lines, each with its own colored badge and a brief one-line reason:
         `{RISK_BADGE} **Risk: {RISK_LEVEL}** — {RISK_REASON}`
         `{CONFIDENCE_BADGE} **Confidence: {CONFIDENCE_LEVEL}** — {CONFIDENCE_REASON}`
         The two badges use **inverted color mappings** so 🟢 always means "good": Low Risk = 🟢, High Risk = 🔴; High Confidence = 🟢, Low Confidence = 🔴. Medium on either is 🟡.
      3. `## Decision` — symbol + label + one-line "Why:"
      4. `## Related` — bullets from `context.json.WorkItems[]` (or `- (no linked items)`)
      5. `## Blockers` — must-fix items, or `- (None.)`
      6. `## Suggestions` — concrete code blocks, each with severity tag
      7. `## How it works` — plain-English explanation (ALWAYS present; if sparse source material, end with `(Inferred from diff; verify intent.)`)
      8. `## How to test` — copy-pasteable steps (ALWAYS present)
      9. `## Files to review first` — top 3 highest-risk paths
      10. `<details><summary>Audit details</summary>` … `</details>` — Context, Scope, Strengths, Issues and risks, Testing, Security, Performance, Operations, Documentation, Diff overview

      **Anti-duplication rule (CRITICAL):**

      The visible block (sections 2–9) and the audit block (section 10) serve DIFFERENT audiences and **must not repeat the same information**:

      - **Suggestions (visible) ≠ Issues and risks (audit).** Suggestions are *actionable code changes the author can apply*. Issues and risks are *potential problems that don't have a concrete fix yet* (open questions, design concerns). If you've written the fix, it's a Suggestion — do not also write it in Issues and risks.
      - **How it works (visible) ≠ Scope (audit).** How it works explains *intent and behaviour*. Scope is the *file inventory* (count, paths, types of change). Do not narrate the file list in How it works.
      - **Why (in Decision) ≠ Strengths (audit).** Why is the *one-line rationale for the verdict*. Strengths is the *audit-level list of what the PR does well*. Do not restate the verdict in Strengths.
      - **Related (visible) ≠ Context (audit) Work Item line.** Related is the at-a-glance evidence the AI fetched + read each linked item. Context's Work Item line is the bare URL for the audit record. The audit Context section does NOT repeat the comment count.

      **Required content rules:**

      - **`[AI Review]` tag** lives in the template's H1 (`# [AI Review]`). The n8n workflow's marker detection accepts the tag whether it appears alone on a line or inside an H1. Do NOT add a separate `[AI Review]` line above the H1 — that would render twice in the posted comment.
      - Fill `{RISK_BADGE}`, `{RISK_LEVEL}`, `{RISK_REASON}`, `{CONFIDENCE_BADGE}`, `{CONFIDENCE_LEVEL}`, `{CONFIDENCE_REASON}`, `{DECISION_SYMBOL}`, `{DECISION_LABEL}` using the rubrics under heading 8. **Never leave or delete placeholders — the badge emoji MUST be the first character on its line**, before the bold label. If you omit the badge the rendered comment is missing its colour-coded severity cue. The two `_REASON` values are short one-line justifications (≤ ~12 words each) — e.g. Risk: "touches auth and adds a DB migration"; Confidence: "diff understood, tests reviewed, build verified".
      - **`## Related`** lists linked references using each platform's NATIVE auto-link syntax. **Do not wrap in markdown links and do not append state, comment counts, or "(title unavailable)" placeholders** — those add noise without information, and the platform already shows that data beneath the PR. Native syntax:
        - Azure DevOps work items:    `#<ItemId>`         (e.g. `#196182`)
        - Azure DevOps pull requests: `!<PullRequestId>`  (e.g. `!32147`)
        - GitHub issues / pull requests: `#<Number>`      (e.g. `#123`)

        Optionally append ` — <Title>` only when the title genuinely helps a scanner. If the title is unavailable in `context.json`, write just the bare reference — never invent one, never write `(title unavailable)`. For external references the platform does NOT auto-link (wiki page, ticket in another system, public docs URL), use a markdown link: `[Title](URL)`. If there are no references, write `- (no linked items)`. Quote a *specific* comment in "How it works" or audit "Issues and risks" only when it materially shapes the verdict — do not paste full threads.
      - **`## How it works` and `## How to test`** are MANDATORY — never omit, even for tiny PRs. For a one-line doc change, How it works = "User-facing wiki text was clarified to define X and Y" (one sentence) and How to test = "Re-render the wiki page; confirm the new sentence appears and renders cleanly" (one step).
      - **Suggestions** carry severity tags: 🔴 Blocking / 🟡 Recommended / ⚪ Optional. Reference Suggestion N from Blockers when a concrete fix is offered. Each suggestion's code body **must not contain bare triple-backtick fences** (they would close the outer `\`\`\`suggestion` block). If the body needs to show markdown code with backticks, replace the inner fences with `~~~` or 4-backtick fences.
      - **Cite sources.** Whenever a finding (Suggestion, Blocker, Issues-and-risks bullet, or How-it-works claim) relies on **external material** — project documentation (e.g., `.github/copilot-instructions.md`, `README.md`, SKILL files, wiki pages), an inline source comment, a linked work item, or a public docs URL — **include a `Source:` reference** with the path (and line range when applicable) or URL. Findings derived purely from the diff itself need no `Source:`. This lets the author resolve conflicts by updating either the code or the obsolete reference (e.g., if a developer added a clarifying comment that contradicts the AI suggestion, the citation makes it obvious whether the suggestion or the comment is out of date). Examples: `Source: .github/copilot-instructions.md`; `Source: src/Foo.cs:42-48 (comment)`; `Source: #196182` (work item).
      - **Prefer Mermaid** for diagrams. Only invoke `ai-image-generation` (at most one image per PR) when `GenerateImages: true` in `pr-review.json` AND a real picture would meaningfully help.
      - **Audit `## Testing`**: list related tests found, tests actually run, build / validation evidence, coverage adequacy. If no suitable automated test exists, add a `Recommended durable tests:` sub-list in the same block.
    - Also fill in `{WorkFolder}/pr-description.md` with a brief PR description (Changes / Why). **The file starts with a `<!-- pr-description:unfilled -->` sentinel — you MUST delete that line when you write real content; the n8n workflow's `Build Review Comment` skips pushing the file to the PR description if the sentinel is still present.** Do NOT add a `Related` section — Azure DevOps and GitHub already render linked work items / issues natively beneath the PR; only mention external references (wiki page, ticket in another system) when they exist. The n8n workflow updates the PR description from this file only when the original PR description is effectively empty (literally empty, whitespace-only, or a documented placeholder like "Please describe your change").
    - Complete {WorkFolder}/checklist.md following the structure in assets/checklist.template.md and compute the score.
    - Record verdict and any required follow-ups.
    - Ask user to review {WorkFolder}/review.md content before posting.
    - Run `python .ai/skills/pr-review/scripts/s08_rasterize_images.py` to render Mermaid diagrams in review.md to PNGs (offline, safe to always run).
    - Run `python .ai/skills/pr-review/scripts/s09_upsert_review_attachments.py` to upload the PNGs (and any local images the AI embedded) to the PR and rewrite review.md to embed the returned URLs.
    - Upon user confirmation, run `python .ai/skills/pr-review/scripts/s10_upsert_review_comment.py` to post review comment to the Pull Request (automatically marked as resolved if approved).
    - Run `python .ai/skills/pr-review/scripts/s11_upsert_pr_description.py` to update the PR description from pr-description.md. Refuses to overwrite if the PR already has a real description.
    - If the review contains suggestions, run `python .ai/skills/pr-review/scripts/s12_upsert_suggestion_threads.py` to post each suggestion as a dedicated inline PR comment thread with file/line context. **Suppressed in n8n/scheduled mode via `SKIP_POST_COMMENT=1`.**
      - To remove previously posted suggestion threads: `python .ai/skills/pr-review/scripts/s12_upsert_suggestion_threads.py --remove-posted`
      - Threads are identified by an agent marker so only threads created by this script are affected.

7. Review checklist

   The review checklist template is maintained in assets/checklist.template.md. This is the single source of truth for the checklist structure.

   The s05_reset_templates.py script creates {WorkFolder}/checklist.md from the template, replacing placeholders with actual values from the configuration and fetched data.

   **Template placeholders:**
   - `{PR_LINK}` - Pull request URL
   - `{BASE_BRANCH}` - Base branch name
   - `{FEATURE_BRANCH}` - Feature branch name
   - `{REPO_NAME}` - Repository name
   - `{PROJECT_NAME}` - Project name
   - `{WORK_ITEM_LINK}` - Link(s) to associated work item(s)

   The checklist includes sections for:
   - Preparation - workspace setup verification
   - Scope - change description and dependencies
   - Code quality - readability, maintainability, structure
   - Correctness - logic, edge cases, error handling
   - Security - credentials, validation, authorization
   - Performance - efficiency, algorithms, data access
   - Testing - unit tests, integration tests, coverage
   - Operations - migrations, configs, observability
   - Documentation - README, changelog, comments
   - Scoring rubric (0-5 per dimension)
   - Decision and follow-ups

8. Review report

   The review report template is maintained in `assets/review.template.md`. This is the single source of truth for the report structure.

   `s05_reset_templates.py` creates `{WorkFolder}/review.md` from the template, replacing static placeholders with values from configuration and fetched data. AI-judged placeholders are filled in by the agent during review.

   **Template placeholders (static, replaced by `s05_reset_templates.py`):**
   - `{PR_LINK}` — Pull request URL
   - `{REPO_NAME}` — Repository name
   - `{PROJECT_NAME}` — Project name
   - `{BASE_BRANCH}` — Base branch name
   - `{FEATURE_BRANCH}` — Feature branch name
   - `{WORK_ITEM_LINK}` — Link(s) to associated work item(s)

   **Template placeholders (AI-judged, filled in by the agent):**
   - `{RISK_BADGE}` — Low ⇒ 🟢, Medium ⇒ 🟡, High ⇒ 🔴
   - `{RISK_LEVEL}` — `Low` / `Medium` / `High`
   - `{RISK_REASON}` — short one-line justification (≤ ~12 words)
   - `{CONFIDENCE_BADGE}` — High ⇒ 🟢, Medium ⇒ 🟡, Low ⇒ 🔴 *(inverted vs. Risk so 🟢 always means "good")*
   - `{CONFIDENCE_LEVEL}` — `High` / `Medium` / `Low`
   - `{CONFIDENCE_REASON}` — short one-line justification (≤ ~12 words)
   - `{DECISION_SYMBOL}` — `✅` or `❌`
   - `{DECISION_LABEL}` — `Approve` / `Approve with comments` / `Request changes`

   **Visible block (above the collapsible audit):**
   - Risk header line: `{RISK_BADGE} **Risk: {RISK_LEVEL}** — {RISK_REASON}`
   - Confidence header line: `{CONFIDENCE_BADGE} **Confidence: {CONFIDENCE_LEVEL}** — {CONFIDENCE_REASON}`
   - Decision (symbol + label + one-line rationale)
   - **Related** — one bullet per linked reference, using each platform's native auto-link syntax (Azure DevOps work item `#<ItemId>`, Azure DevOps pull request `!<PullRequestId>`, GitHub issue/PR `#<Number>`). No markdown wrapping, no state, no comment count, no `(title unavailable)` placeholder — those add noise and the platform already shows that data. Optionally append ` — <Title>` only when the title is in `context.json` and genuinely helps the scanner. External references that the platform does not auto-link use `[Title](URL)`. Empty list → `- (no linked items)`.
   - Blockers (must-fix bullets; reference Suggestion N for the fix)
   - Suggestions (concrete code blocks, each tagged 🔴 Blocking / 🟡 Recommended / ⚪ Optional)
   - How it works (always present; flag with `(Inferred from diff; verify intent.)` when source material is sparse)
   - How to test (copy-pasteable steps + commands)
   - Files to review first (3 highest-risk changed files)

   **Audit details (inside `<details>` block at the bottom):**
   - Context, Scope, Strengths, Issues and risks, Testing, Security, Performance, Operations, Documentation, Diff overview

   **Decision symbols (canonical, used verbatim — downstream tooling matches on these labels):**

   | Symbol | Unicode | Label | Meaning |
   |--------|---------|-------|---------|
   | ✅ | U+2705 WHITE HEAVY CHECK MARK | `Approve` | No blocking issues; merge when ready |
   | ✅ | U+2705 WHITE HEAVY CHECK MARK | `Approve with comments` | No blockers; non-blocking suggestions present |
   | ❌ | U+274C CROSS MARK | `Request changes` | One or more blockers; do not merge until addressed |

   The label string is **exact and case-sensitive**.

   **Risk-level rubric (AI-judged):** badge tracks *severity* — green is low risk (safe), red is high risk (dangerous).

   | Badge | Level | Triggers |
   |-------|-------|----------|
   | 🟢 | Low | Touches non-critical paths, has tests, no security/perf/data implications |
   | 🟡 | Medium | Touches business logic, missing some test coverage, or moderate refactor |
   | 🔴 | High | Security, auth, payments, data migrations, breaking changes |

   **Confidence-level rubric (AI self-assessment):** badge tracks *certainty* — green is high confidence (sure), red is low confidence (unsure). **Note the inverted mapping vs. Risk**: 🟢 means "good" on both scales but corresponds to different levels (Low Risk ↔ High Confidence).

   | Badge | Level | Meaning |
   |-------|-------|---------|
   | 🟢 | High | Full context available, diff understood, tests reviewed |
   | 🟡 | Medium | Some context missing — sparse work item, build failed, etc. |
   | 🔴 | Low | Significant unknowns flagged in audit section |

   **Image generation:** off by default. The skill reads `GenerateImages` from `pr-review.json`; when `true`, the AI may invoke the `ai-image-generation` skill **at most once per PR**, only when it judges a real picture (mockup, before/after, conceptual sketch) would meaningfully help. Output goes to `{WorkFolder}/diagrams/` and is embedded via a Markdown image link inside the "How it works" section. Mermaid is always allowed and is the preferred path for flow / sequence / architecture diagrams.

8a. PR description (auto-generated brief)

    `s05_reset_templates.py` also generates `{WorkFolder}/pr-description.md` from `assets/pr-description.template.md`. The AI overwrites it during review with `## Changes` + `## Why` content.

    **Unfilled sentinel:** the template opens with `<!-- pr-description:unfilled — agent: remove this line ... -->`. The agent MUST delete that sentinel line when writing real content. The n8n workflow's `Build Review Comment` node skips the PR-description update entirely if the sentinel is still present, so an unfilled scaffold cannot reach the PR.

    **Do NOT add a `Related` section.** Azure DevOps shows linked work items, and GitHub shows linked issues/PRs, in the native PR UI already — duplicating them in the description is noise. Only mention references that are *not* already auto-linked by the platform (external wiki page, ticket in another system, public docs link).

    The n8n workflow `Refactoring - Review Pull Request` reads this file and updates the actual PR description **only when** (a) the sentinel has been removed AND (b) the original PR description is effectively empty (literally empty, whitespace-only, or one of the documented placeholder patterns). Author content is never overwritten.

9. Script interfaces specification

   **review_config.py** - Helper module for configuration management

   Functions:
   - `get_review_config()` - Load and merge pr-review.json + {WorkFolder}/context.json
   - `get_git_repository_root()` - Find Git repository root for a path
   - `assert_standalone_git_repository()` - Ensure path is a standalone Git repo root
   - `get_workspace_root()` - Locate workspace root by walking up to pr-review.json
   - `get_work_folder()` - Resolve artifact output directory from config
   - `get_branch_folder()` - Resolve the local PR branch repository folder from `BranchFolder` or legacy `BranchPath`
   - `should_pull_branch()` - Normalize the `PullBranch` setting to a boolean
   - `get_auth_headers()` - Build Azure DevOps authentication headers (PAT / Azure CLI / fallback)

   **s02_get_azure_devops_info.py** - Fetch PR and work item metadata

   Purpose: Query Azure DevOps REST API and populate {WorkFolder}/context.json with dynamic data.
   Uses settings from `pr-review.json`.

   **s03_extract_attachments.py** - Download attached images from PR + linked work items

   Purpose: Scan PR and linked work items for image references and download each into `{WorkFolder}/attachments/` with a `.context.md` and `.meta.json` sidecar. The reviewing AI reads `attachments/manifest.json`. Deterministic; no AI calls.

   **s04_fetch_repository.py** - Prepare the local branch folder and fetch branches when configured

   Purpose: Clone or update `BranchFolder` and fetch base/feature refs when `PullBranch` is `true`; otherwise use `BranchFolder` as an existing local checkout and compare base against `HEAD`.
   Uses settings from `pr-review.json` and `{WorkFolder}/context.json`.

   **s05_reset_templates.py** - Create review templates with actual PR data

   Purpose: Create review.md and checklist.md from templates with actual PR data.
   Uses settings from `pr-review.json` and `{WorkFolder}/context.json`.

   **s06_export_diff_artifacts.py** - Export diffs and changed files

   Purpose: Export per-file diffs, patches, and changed files for base..feature comparison.
   Uses settings from `pr-review.json` and `{WorkFolder}/context.json`.

   **s07_consolidate_diffs_and_content.py** - Consolidate patches and snapshots

   Purpose: Concatenate per-file diffs and pre/post snapshots into single artifacts for the reviewing AI, with chunked output for large PRs.

   **s01_reset_workspace.py** - Clean previous review artifacts

   Purpose: Remove generated artifacts from previous review to prepare for new review.

   Parameters:
   - `--keep-repo` - Keep repository checkout in `BranchFolder` when it is under {WorkFolder} (faster for same repo)

   **s08_rasterize_images.py** - Render ```mermaid blocks in review.md to PNGs

   Purpose: Detect ```mermaid fenced blocks in review.md and render each to `{WorkFolder}/diagrams/diagram-NNN-<sha>.png` using `mmdc` (mermaid-cli). Writes `mermaid-manifest.json` linking each block to its PNG. Offline — no network or PR API calls — so safe to run unconditionally even when `SKIP_POST_COMMENT=1`. Idempotent on content sha256. No-op (with warning) when `mmdc` is not installed.

   Parameters:
   - `--scale N` - mmdc render scale (default: 2)
   - `--background-color COLOR` - mmdc background color (default: white)
   - `--mmdc PATH` - Explicit path to mmdc binary

   **s09_upsert_review_attachments.py** - Upload diagrams + local images to PR; rewrite review.md

   Purpose: For Azure DevOps PRs, upload each PNG produced by s08 to the PR's attachments endpoint and substitute ```mermaid fences in review.md with `![](attachment-url)` (collapsed source kept in `<details>`). Also uploads any `![alt](local-path)` references the AI embedded (e.g. ai-image-generation output) and substitutes their URLs. Skipped on GitHub (which renders mermaid natively).

   This script POSTs to the PR's attachments endpoint and **must not run when `SKIP_POST_COMMENT=1`** — entrypoint.sh gates it the same way as s10/s11.

   Parameters:
   - `--dry-run` - Print actions without uploading or rewriting

   **s10_upsert_review_comment.py** - Upsert review comment to Pull Request

   Purpose: Post the content of {WorkFolder}/review.md as a comment thread on the PR.
   Uses settings from `pr-review.json` and `{WorkFolder}/context.json`.

   Parameters:
   - `--dry-run` - Print payload without posting

   **s11_upsert_pr_description.py** - Upsert PR description from pr-description.md

   Purpose: Update the PR description from `{WorkFolder}/pr-description.md` ONLY when all four guards pass — file is non-empty, no `<!-- pr-description:unfilled -->` sentinel, no scaffold-signature phrases (`Briefly list what changed`, `One-line motivation`, `{WORK_ITEM_LINK}`), AND the PR's current description is literally empty. Refuses to overwrite real author content (institutional memory: the n8n equivalent once wiped a real description on PR 32147 when its guards were too loose).

   Parameters:
   - `--dry-run` - Evaluate guards and print decision without PATCHing

   **s12_upsert_suggestion_threads.py** - Upsert suggestion threads to Pull Request

   Purpose: Post suggestions as dedicated inline PR comment threads.
   Uses settings from `pr-review.json` and `{WorkFolder}/context.json`.

   Parameters:
   - `--remove-posted` - Remove previously posted suggestion threads
   - `--dry-run` - Print payloads without posting

   **invoke_build.py** - Build solutions or projects

   Purpose: Cross-platform build wrapper. Uses `dotnet msbuild` (all platforms) or full MSBuild via vswhere (Windows with Visual Studio).

   Parameters:
   - All arguments are passed through to the build tool (solution/project file path and any MSBuild switches).
   - The first argument is normalized to an absolute solution/project path before invocation.

   Behaviours worth knowing:

   - Always prefer `.slnx` over `.sln` when both exist with the same stem; the wrapper auto-substitutes.
   - On non-Windows hosts, the wrapper walks the solution/project graph and **rewrites recorded paths in-place** for any `ProjectReference` or solution-listed project whose casing doesn't match the on-disk file (e.g. `Web.Core/Web.Core.csproj` -> `Web.Core/web.core.csproj`). Rewrites are line-based string substitution against the matched span; no XML/INI reflow, BOMs preserved. The rewrites live in the disposable clone only and never reach a commit.

   Examples:

   ```bash
   python .ai/skills/pr-review/scripts/invoke_build.py {solution|project} /v:minimal /clp:Summary
   python .ai/skills/pr-review/scripts/invoke_build.py MyApp.slnx /p:Configuration=Release /t:Rebuild
   ```

10. Python guidance

    - Run scripts with `python script.py` from the repository root.
    - All scripts use UTF-8 without BOM for text output.
    - All scripts accept `--help` for usage information.
    - Use `pathlib.Path` for cross-platform path handling.
    - Avoid writing secrets to disk or to logs.
    - Platform-specific: `Setup_Util_TrustedRootCertificates_Save.ps1` is automatically invoked on Windows by API scripts for corporate certificate environments using a direct `powershell -File` invocation.

11. Mermaid overview

    ```mermaid
    flowchart TD
      A[Start] --> B[Setup workspace dirs]
      B --> C{PullBranch?}
      C -->|true| D[Clone/update BranchFolder and fetch base and feature]
      C -->|false| E[Use current BranchFolder HEAD]
      D --> F[List changed files]
      E --> F
      F --> G[Export diffs]
      F --> H[Export changed files]
      G --> I[Review diffs and files]
      H --> I
      I --> J[Complete checklist]
      J --> K[Record verdict]
    ```

12. Quality bar for approvals

    - No known correctness issues.
    - Security and secrets posture unchanged or improved.
    - Risk appropriate tests present or clearly ticketed with timeline.
    - Operational concerns documented and migration risks addressed.
    - Code clarity acceptable or improved.

13. Known edge cases

    - Large binary or generated files should be excluded from export; skip via --max-file-bytes.
    - Line-ending normalization may affect patch readability; set core.autocrlf consistently.
    - Submodules and LFS objects require additional steps not covered here.

14. Maintenance

    - Keep this instructions file aligned with the scripts contract.
    - Update defaults when the target repository or branches change.
    - Consider adding a small validation script to lint the exported artifacts.
