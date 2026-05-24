---
name: repository-analysis
description: Generate or refresh `.ai/repository-analysis.instructions.md` whenever the user needs a repository-wide map of architecture, projects, technology stack, developer workflows, CI/testing, documentation, or Mermaid diagrams. Use this skill even when the request only names one slice of that work—such as “summarize the repo”, “map dependencies”, “document the stack”, “refresh onboarding context”, or “update architecture notes”—because those tasks usually need the same factual analysis workflow.
---

# Repository analysis

## What this skill is for

Use this skill to create or refresh [`.ai/repository-analysis.instructions.md`](.ai/repository-analysis.instructions.md) as a factual repository reference for humans and AI coding agents. The goal is not just to summarize files, but to explain how the repository is organized, what it builds, how it is operated, and which constraints matter when making changes.

When the user asks for only one slice of repository understanding—such as project mapping, dependency analysis, tech stack documentation, CI/test workflow discovery, or architecture diagrams—still use the same repository-wide workflow so the resulting document stays internally consistent.

## Core principles

- Work from repository evidence first: manifests, source files, configuration, scripts, workflow files, and documentation.
- Keep the output factual and descriptive. Do not turn the analysis into recommendations, refactoring advice, or implementation instructions.
- Preserve valuable existing content in [`.ai/repository-analysis.instructions.md`](.ai/repository-analysis.instructions.md) unless it is outdated, contradicted by stronger evidence, or replaced with something clearly better.
- Distinguish between observed facts and concise synthesis. If something is inferred, make the inference cautious and evidence-based.
- Prefer completeness over novelty. Missing a key project, workflow, or diagram is worse than writing a shorter summary.

## Required working files

Before analyzing the repository, create and maintain these temporary files under [`.tmp/`](.tmp/) at the repository root:

- [`.tmp/repository-analysis.Requirements.md`](.tmp/repository-analysis.Requirements.md) — a sectioned checklist of what must be captured.
- [`.tmp/repository-analysis.TODO.md`](.tmp/repository-analysis.TODO.md) — the same work converted into an execution checklist.
- [`.tmp/repository-analysis.instructions.bak.md`](.tmp/repository-analysis.instructions.bak.md) — a backup copy of the previous report, but only if [`.ai/repository-analysis.instructions.md`](.ai/repository-analysis.instructions.md) already exists.

Update the TODO file after each major discovery or writing step. Remove all three temporary files only after the refreshed report has been validated successfully.

## Read these inputs first

Start every run by reading the highest-value context files that define the repository's purpose and conventions:

1. [`.ai/developer-info.md`](.ai/developer-info.md) if it exists. Treat developer-provided clarifications as authoritative unless the user explicitly overrides them.
2. [`.ai/repository-analysis.instructions.md`](.ai/repository-analysis.instructions.md) if it exists, so you can preserve useful sections and structure.
3. [`ReadMe.md`](ReadMe.md) and [`Requirements.md`](Requirements.md).
4. [`.ai/instructions.md`](.ai/instructions.md) and any nearby repository-specific instruction files that materially affect developer workflow.
5. Top-level solution, manifest, and dependency files such as `*.sln*`, `*.csproj`, `Directory.Build.props`, `Directory.Packages.props`, `package.json`, `requirements.txt`, `Dockerfile`, `Containerfile`, `appsettings*.json`, and CI workflow files under [`.github/workflows/`](.github/workflows/).

Then expand outward from those anchors into the relevant source folders, documentation folders, scripts, and infrastructure manifests.

## Discovery workflow

### 1. Set up the task

- Create the requirements and TODO files in [`.tmp/`](.tmp/) at the repository root.
- If [`.ai/repository-analysis.instructions.md`](.ai/repository-analysis.instructions.md) exists, back it up before editing.
- Convert the user request into explicit analysis tasks. If the user asked for a narrow slice, add the minimum surrounding tasks needed to keep the report coherent.

### 2. Inventory repository structure

- Identify every top-level directory and explain its purpose.
- Detect major source areas, documentation areas, generated-output areas, test areas, and infrastructure/configuration areas.
- For very large repositories, sample representative file names rather than dumping huge trees.

### 3. Inspect build and dependency manifests

Always inspect the repo's real manifests rather than inferring from folder names alone.

- For .NET repositories, inspect every `*.csproj` and capture `AssemblyName`, `Description`, `TargetFramework` or `TargetFrameworks`, key `PackageReference` items, and `ProjectReference` relationships.
- Preserve an existing project `<Description>` verbatim when present. If it is missing or empty, supply a concise factual summary.
- Resolve MSBuild variables by checking `Directory.Build.props`, then `Directory.Packages.props`, then project-local props files, and note the source of resolved values when that context matters.
- For JavaScript/TypeScript, inspect `package.json`, lockfiles when relevant, and documented scripts.
- For Python, inspect `requirements.txt`, `pyproject.toml`, `setup.py`, or equivalent files.
- For container/infrastructure tooling, inspect `Dockerfile`, `Containerfile`, compose/manifests, deployment scripts, and runtime configuration files.

### 4. Map runtime architecture and responsibilities

Document how the repository is meant to run, not just how it is stored on disk.

- Identify the main product surfaces, services, libraries, utilities, scripts, and support assets.
- Describe the primary architectural pattern only when the evidence supports it.
- Capture configuration patterns, dependency injection approach, runtime boundaries, communication paths, persistence technologies, and external integrations.
- Explain how infrastructure scripts, manifests, or orchestration layers relate to application code.

### 5. Map developer workflows

- Detect build, run, test, packaging, deployment, backup, and restore workflows from scripts, workflow files, manifests, and docs.
- Detect test projects and test harnesses automatically and explain how they are run.
- Prefer repository-owned scripts and documented commands over generic guesses.
- Capture CI/CD systems, validation scripts, and any automation that affects contributor workflows.

### 6. Map documentation

- Detect documentation folders regardless of their names or locations.
- Summarize the role of each documentation cluster and highlight the most important files.
- Include a documentation taxonomy diagram when the repo has multiple documentation areas or audiences.

### 7. Compile and validate the report

- Update or rewrite [`.ai/repository-analysis.instructions.md`](.ai/repository-analysis.instructions.md).
- Keep useful existing headings where possible, but do not preserve inaccurate or thin sections just for continuity.
- Run a diff against the backup and make sure high-value content was not accidentally lost.
- Verify the TODO file shows all major tasks complete before cleanup.

## Minimum content the report must contain

The finished report in [`.ai/repository-analysis.instructions.md`](.ai/repository-analysis.instructions.md) must cover these areas, even if some sections are brief:

1. **Repository overview** — what the repository is for, its major product or platform goals, and the main audiences.
2. **Top-level structure** — every top-level directory and its purpose.
3. **Technology stack and versions** — languages, frameworks, major packages or libraries, storage technologies, infrastructure tools, and version evidence.
4. **Architecture and runtime model** — main layers, services, modules, orchestration, and interaction patterns.
5. **Project inventory** — application projects, libraries, tests, scripts, and important non-code assets.
6. **Dependency and data flow** — project references, service relationships, integration paths, and notable shared resources.
7. **Developer workflows** — build, run, test, CI/CD, setup, deployment, backup/restore, and other repo-owned operational flows.
8. **Documentation map** — documentation folders, key documents, and their intended use.
9. **AI-agent-relevant conventions or constraints** — coding standards, operational guardrails, or repository rules that materially affect automated edits.

## Output structure

Use this structure unless an existing report already has a clearly better equivalent that should be preserved:

```markdown
# Repository Analysis

## 1. Repository Overview

## 2. Top-Level Structure

## 3. Technology Stack & Key Dependencies

## 4. Architecture & Runtime Model

## 5. Project Inventory

## 6. Dependency & Data Flow

## 7. Build, Test, CI/CD & Operational Workflows

## 8. Documentation Map

## 9. AI-Agent-Relevant Conventions and Constraints
```

For each main `##` section, begin with 1-2 sentences explaining why the section is useful. Use tables where they improve scanability, especially for project inventories, technology stacks, workflows, and documentation clusters.

## Required diagrams

Include Mermaid diagrams that match the repository shape:

- **Architecture layers or component model** — required.
- **Project dependency or service interaction graph** — required.
- **Documentation taxonomy** — required when the repository has more than one documentation area or audience.

Keep diagrams compact, syntactically valid, and evidence-based. Prefer a few readable diagrams over a single giant graph.

## Project inventory requirements

When the repository contains multiple code projects or manifests, include structured metadata for each important unit.

- For `*.csproj`, capture path, assembly name, framework target, description, and notable dependencies or references.
- For test projects, explicitly mark them as tests and explain how they are run.
- For scripts or infrastructure-only components that are central to the repository, describe their role even if they are not traditional application projects.
- For non-.NET stacks, use the equivalent metadata that best explains the unit: package name, runtime, entrypoint, key dependencies, and purpose.

## Constraints and safety rules

- Never treat generated artifacts or dependency caches as primary evidence.
- Do not recurse into `node_modules`, `bin`, `obj`, `.git`, `.vs`, `packages`, `.nuget`, or similarly generated/cache folders unless the user explicitly asks for them.
- Limit large folder listings to manageable samples. Show real names, not placeholders.
- If a file is missing, inaccessible, or clearly corrupted, document the gap and continue.
- If no `*.csproj` files exist, record that as a repository characteristic rather than a failure.
- Do not guess version numbers. If a version cannot be verified from inspected files, say so.
- Do not force .NET-centric structure onto repositories that primarily use another stack. Inspect whatever manifests the repository actually uses.

## Final validation checklist

Before finishing, confirm all of the following:

- The temporary requirements and TODO files were created and kept current.
- Every important top-level directory has been accounted for.
- Every relevant project or manifest type discovered in the repo has been analyzed.
- Technology versions are backed by inspected files.
- Existing project descriptions were preserved where present.
- Required Mermaid diagrams are present and readable.
- Build, test, CI/CD, and operational workflows are documented from repository evidence.
- Valuable content from the previous report was not lost accidentally.
- Temporary files in [`.tmp/`](.tmp/) were deleted after successful validation.

## Completion behavior

When the report is complete, explicitly confirm that [`.ai/repository-analysis.instructions.md`](.ai/repository-analysis.instructions.md) was refreshed successfully and that the temporary tracking files were cleaned up.
