---
name: solution-patterns
description: Establish and enforce deterministic path patterns across Code ↔ UI route/menu ↔ Test for any project. Use this skill before creating, renaming, or relocating any UI component, page, view, view-model, route, controller, desktop panel, or test file — it tells you the exact expected path in each of the three columns before you touch disk. Also use when onboarding a repo (generates `.ai/solution-patterns.instructions.md` + `.ai/solution-patterns.csv`), when auditing a project for structural consistency, when asked "where does X live?", or whenever the user mentions folder layout, route mapping, breadcrumbs, menu structure, project structure, naming conventions, solution structure, or "which file is the UI for this route". Load this skill before modifying any coding project — if you skip it you will invent paths instead of deriving them, and you will drift from the project's declared convention.
---

# Solution Patterns (Code ↔ UI ↔ Test path governance)

> **Core idea:** The code folder is the single source of truth. UI routes and test paths are *derivable* from code paths via stack-specific rules. Once the mapping is explicit and machine-readable, "where does X live?" stops being a guess.

## 1. Why this skill exists

The [`qa-tester`](../qa-tester/SKILL.md) skill already proved the value of a deterministic Code → Test mirror (§5.2 of qa-tester): you compute the test path from the product path with a pure string transform, and "locate or create the test for file X" becomes a one-shot answer instead of a semantic search.

This skill generalises that idea along two axes:

1. **The folder/code spine** — every artifact (page, controller, model, test, CSS, migration, sqlproj item) sits somewhere in the solution's folder tree. The folder path is the artifact's primary key; nothing else needs to be invented.
2. **Typed correspondences between artifacts** — given one artifact, deterministic rules derive the others that correspond to it: its test, its URL route, its breadcrumb, its sidebar position, its REST endpoint, its companion file (e.g. `.cshtml` ↔ `.cshtml.cs`), its SQL table.

A single page like `Pages/Agents/Jobs/Index.cshtml` projects into all four navigation forms — URL route `/Agents/Jobs`, breadcrumb `Home > Agents > Jobs`, sidebar position under "Agents", and (if exposed) REST endpoint `GET /api/agents/{id}/jobs` — from the same spine coordinate. The skill stores one nav column per artifact and **derives** breadcrumb and sidebar as projections; it does not duplicate them.

When the spine and the correspondence rules are machine-readable, the AI can:

- Predict every related path before a file is read ("add a Dashboard page" → code path, route, breadcrumb, sidebar parent, test path, AutomationId — all known in advance).
- Generate complete navigation views (route table, breadcrumb map, sidebar tree) from code alone.
- Flag artifacts that disagree with the project's declared convention.
- Nudge a messy project toward consistency incrementally, instead of a single risky rewrite.

**Correspondence types and ownership** — this skill owns only the path-derivable ones:

| Type | Examples | Owned by |
|---|---|---|
| **Path-mirror** | `App/Foo.cs` ↔ `App.Tests/FooTests.cs` | this skill (reuses qa-tester rule) |
| **Folder→nav family** | `Pages/Agents/Jobs/Index.cshtml` ↔ `/Agents/Jobs` ↔ `Home > Agents > Jobs` ↔ sidebar position ↔ REST equivalent | this skill |
| **Companion** | `.cshtml` ↔ `.cshtml.cs`, `View.xaml` ↔ `View.xaml.cs`, `View.xaml` ↔ `ViewModel.cs` | this skill |
| **Name-mapping (directional)** | `Models/Agent.cs` ↔ `dbo.Agent` table | this skill (CSV); per-project `.instructions.md` declares which side is canonical (see §2 principle 2) |
| **Reference** | markup `class="icon-btn"` ↔ `.icon-btn` in CSS | [`layout-guidelines.instructions.md`](../../layout-guidelines.instructions.md) — verified by grep/lint, not in the CSV |
| **Convention** | `Agent` ↔ `AgentService` ↔ `IAgentRepository` | `developer.instructions.md` — review-only, not in the CSV |

## 1.5. The chain — folder spine on top, typed correspondences below

The clearest way to see how the layers fit is as a tree where the **folder spine sits on top** as SSOT, code projects branch off it, files live in the projects, and **typed edges** connect files to their corresponding artifacts in other branches.

```
{Solution}/                                ← FOLDER SPINE (top SSOT — every artifact lives here)
│
├── {Project}/                             ← code project (csproj) — primary code branch
│   ├── {Sub}/{Name}.cs                    ← code file (page model, controller, view-model, …)
│   │   ├─ companion ──────────────────→   {Sub}/{Name}.{paired-ext}            (e.g. .cshtml ↔ .cshtml.cs, .xaml ↔ .xaml.cs)
│   │   ├─ path-mirror ────────────────→   ../{Project}.Tests/{Sub}/{Name}Tests.cs
│   │   ├─ folder→route ───────────────→   /{Sub}/{Name}                        (URL — for Role=page)
│   │   │     ├─ projection ──────────→    Home > {Sub} > {Name}                (breadcrumb, derived)
│   │   │     └─ projection ──────────→    sidebar position under "{Sub}"       (derived)
│   │   └─ convention ─────────────────→   {Name}Service, I{Name}Repository     (review-only — owned by developer.instructions.md)
│   ├── Api/{Endpoints}.cs                 ← REST endpoints
│   │   └─ folder→endpoint ────────────→   {VERB} /api/{path}                   (REST URL — for Role=endpoint)
│   ├── Models/{Name}.cs                   ← model class
│   │   └─ name-mapping ───────────────→   dbo.{Name}                           (SQL table — direction declared in .instructions.md)
│   └── wwwroot/css/{stylesheet}.css       ← style file
│         ←── reference ────────────────   markup `class="..."` references      (owned by layout-guidelines.instructions.md)
│
├── {Project}.Tests/                       ← test project (mirrors {Project}/ structurally — qa-tester §5.2)
│   └── {Sub}/{Name}Tests.cs               ←── path-mirror of {Project}/{Sub}/{Name}.cs
│                                              (linked by qa-tester `@under-test` header)
│
└── {DataProject}/                         ← SQL Data project — canonical iff `.instructions.md` declares it so
    └── dbo/Tables/{Name}.sql
          ──── {Generator}.ps1 ────────→   generates {Project}/Models/{Name}.cs (mirrored, not hand-edited)
```

**Reading the diagram:**

- **Vertical edges (`├── └──`)** are *containment* — the folder hierarchy. This is the only universal SSOT.
- **Horizontal arrows (`──→`)** are *typed correspondences* — each one is one of the six types in §1's table. Some are path-derivable (in the CSV); others are reference-based or convention-only (owned elsewhere).
- **Direction matters for name-mapping.** SQL ↔ Model is bidirectional in shape but unidirectional in authority — the per-project `.instructions.md` declares which side is canonical (in this repo: SQL is canonical, models are generated by `Generate-Models.ps1`).
- **Breadcrumb and sidebar are projections, not separate nodes.** They derive from the URL tree once every `page` row's route + title is known. The CSV stores the route; `pattern_map.py` emits the breadcrumb map and sidebar tree as a sidecar view (§4.1).
- **Tests are first-class.** The path-mirror edge from every code file to its test file is the qa-tester §5.2 rule, reused verbatim by this skill — the join column in the CSV is `ExpectedTestPath`.
- **The expectation invariant (§2 #2) is the payoff.** A reader looking at *any* node should be able to imagine — without searching — the corresponding nodes in every other branch: sidebar entry → code path → URL → breadcrumb → test path → SQL table → model file. When the diagram fits the codebase, navigation becomes a free reference index. When a node breaks the pattern, every future read pays a search tax. Off-convention placement is a defect (`off-convention` in §5), not a design choice; declared overrides in `.instructions.md` are the only legitimate exceptions.

## 2. First principles

Each rule has a *Why* so you can judge edge cases instead of pattern-matching on the rule.

1. **The folder/code spine is the universal SSOT for path-based correspondences.** UI routes, breadcrumbs, sidebar positions, REST endpoints, test paths, and companion files are all *derived* from code paths. *Why:* folders are what the filesystem, git, and the IDE navigate by — deriving the other artifacts means they're always in sync with reality, not a stale hand-maintained list. This is the **default direction for derivation when nothing yet exists**; during refactors, principle #2 applies.

2. **Bidirectional simplification (two-way street).** When two components in the chain share a structural relationship — code ↔ folder, folder ↔ route, route ↔ REST endpoint, route ↔ breadcrumb ↔ sidebar, code ↔ test (mirror), code ↔ companion, model ↔ SQL table, descriptor catalog ↔ generated form — always consider adjusting **either** side to simplify the other. The right fix is whichever change makes the joint system smaller and more consistent: sometimes rename a controller to match a clean route, sometimes rename the route to match a clean controller; sometimes move a file to match its sidebar position, sometimes restructure the sidebar to match the file. Do not treat one side as immutable. *Why:* principle #1 sets the *default* derivation direction when nothing yet exists. During refactors, both sides are existing artifacts; treating either as sacred forces ugly names on the other for no engineering benefit. The rule keeps the joint system the focus, not the individual side. *How to apply:* propose the rename that produces (a) the smaller diff, (b) the cleaner naming, and (c) the fewer downstream renames. *Exceptions:* extremely rare when all components live in one solution. Hard exceptions — a wire format other systems already consume, a schema with external readers, a public API contract you don't own — must be named explicitly in `.instructions.md` before any workaround is added. Reference-based pairs (markup ↔ CSS) follow the same principle but are owned by [`layout-guidelines.instructions.md`](../../layout-guidelines.instructions.md); convention-only pairs (`{Name}` ↔ `{Name}Service` ↔ `I{Name}Repository`) follow it under `developer.instructions.md`.

3. **The expectation invariant: any one layer must let a reader imagine the others — divergence is a defect.** Looking at a sidebar entry like `{Sub} > {Name}` should let any developer or AI predict, *without searching*: the code path (`{Project}/{Sub}/{Name}.{ext}`), the URL (`/{Sub}/{Name}`), the breadcrumb (`Home > {Sub} > {Name}`), the test path (`{Project}.Tests/{Sub}/{Name}Tests.cs`), and — when an SSOT direction is declared — the SQL table (`dbo.{Name}` or similar) and the model file. The reverse must also hold: opening any code file should let a reader predict its sidebar entry, URL, breadcrumb, REST equivalent, and test path. *Why:* mirrored layers turn navigation into a free reference index — every "where is X?" question becomes a string transform instead of a grep. The moment any layer stops mirroring, every future read of the codebase pays a search tax that compounds with every new file. *How to apply:* before placing a new file, mentally derive the sidebar entry, URL, and test path it implies; if any of those would surprise a careful reader, fix the *placement*, not the entry — and use principle #2 to decide which side moves. *Exceptions:* genuinely rare — must be declared in `.instructions.md` with an explicit "why" (compliance constraint, third-party contract, externally-frozen schema, historical migration). An undeclared deviation is always a defect — its strongest signal is the `off-convention` code in §5; a declared deviation is a recorded override.

4. **Name-mapping correspondences have a per-project canonical direction.** SQL table ↔ model class can have either side as SSOT — Code-First (model canonical, SQL generated by EF migrations) or Database-First (SQL canonical, models generated by a script). *Why:* the choice depends on who owns the schema and who consumes it. The per-project `.instructions.md` declares the direction (see §4); the deviation report respects it — drift means the *generated* side is stale, never the canonical side.
5. **Opinionated defaults per stack, explicit overrides per project.** The skill ships default patterns in [`references/`](references/). A repo records its *actual* patterns in `.ai/solution-patterns.instructions.md` — that file **overrides** the defaults. *Why:* one-size-fits-all fights Angular's deliberate divergence from route=folder mirroring; no-defaults-at-all fails green-field projects that have nothing declared yet.
6. **Record deviations, don't silently enforce.** When a file deviates from both the project's declared pattern AND the stack default, flag it with a deviation code. Recommend moving only when the deviation is arbitrary ("the developer had no information on expected patterns when they created it") — not when the `.instructions.md` documents an intentional choice. *Why:* a flagged mismatch is a conversation, not a build failure. Projects evolve faster than rewrites.
7. **The CSV is generated; the `.instructions.md` is written by humans.** [`scripts/pattern_map.py`](scripts/pattern_map.py) regenerates `.ai/solution-patterns.csv` on demand. Never hand-edit the CSV — it gets overwritten. Never auto-generate the `.instructions.md` (except as a first draft during onboarding) — its value is the human reasoning behind each override. *Why:* mixing generated and hand-written data in one file guarantees losing one or the other.
8. **Every rule in the skill has a *Why*.** If you can't explain the motivation for a pattern, it's dogma the next AI will misapply. *Why:* (the rule itself is the demonstration.)
9. **Prefer subtraction.** Remove any stack rule, default, or deviation code that earns its keep fewer than 1 call in 20. *Why:* this file must stay under ~400 lines or it stops being loaded as reference and starts being skipped as noise.

## 3. Decision matrix — pick the stack reference file

Once [`scripts/detect_stack.py`](scripts/detect_stack.py) has identified the stack(s) in the repo, load only the reference file(s) you actually need:

| Stack signal (auto-detected) | Reference file | Scope |
|---|---|---|
| `angular.json` or `@angular/core` in `package.json` | [`references/angular-patterns.md`](references/angular-patterns.md) | Component-set folder convention, lazy routes, feature folders |
| `next.config.js` / `next.config.ts` or `"next"` in `package.json` | [`references/nextjs-patterns.md`](references/nextjs-patterns.md) | `app/` or `pages/` → URL segments |
| `.csproj` with `Microsoft.NET.Sdk.Web` + any `Pages/` or `Controllers/` folder | [`references/razor-patterns.md`](references/razor-patterns.md) | Razor Pages + MVC + minimal-API variants |
| `.csproj` with `<UseWPF>true</UseWPF>` / `<UseWinUI>true</UseWinUI>` / `<UseWindowsForms>true</UseWindowsForms>` | [`references/wpf-winui-patterns.md`](references/wpf-winui-patterns.md) | WPF, WinUI 3, WinForms — Views/Controls/ViewModels → menu breadcrumb + AutomationId |
| `Architecture/` folder with a multi-environment hosts/IP/cluster plan, OR an `## Network patterns` block in `.ai/solution-patterns.instructions.md` | [`references/network_patterns.md`](references/network_patterns.md) | Deployment-side spine: server name → IP → DNS → port → cluster, across LIVE/UAT/DEV (with Azure CAF alignment for cloud / hybrid repos). Loaded **in addition** to the code-side stack references |
| `.sln` / `.slnx` whose project files follow `{Company}.{Solution}.{Feature}.{Project}.{ext}`, OR an `## Project patterns` block in `.ai/solution-patterns.instructions.md` | [`references/project_patterns.md`](references/project_patterns.md) | Build/install-side spine: project name → namespace → folder → install path → server-suffix tier (the bridge to `network_patterns.md`). Loaded alongside code-side and network references |

Repos with multiple stacks (e.g. ASP.NET Core + WPF in the same solution) load **all** matching reference files. Each stack owns its rows in the CSV independently.

## 4. The per-project contract

Two files, both at `.ai/` inside the target repo — never inside the skill itself:

### `.ai/solution-patterns.instructions.md` (human-written, overrides defaults)

Minimal shape — the AI drafts this during onboarding; the human confirms and edits:

```markdown
# Solution Patterns — declared for this repo

## Detected stacks
- aspnet-core (from `{WebProject}/{WebProject}.csproj` — `Microsoft.NET.Sdk.Web`)
- sql-data (from `{DataProject}/{DataProject}.sqlproj`)

## SSOT directions

For correspondences where either side could in principle be canonical, declare which is.

### sql-model
- **Canonical side:** SQL Data project (`{DataProject}/{DataProject}.sqlproj`).
- **Generated side:** model classes under `{WebProject}/Data/`.
- **Generator:** `{WebProject}/Data/Generate-Models.ps1`.
- **Why:** schema is shared with other systems and DBA-owned; models are a consumer view.
- **Implication for the deviation report:** if a model drifts from its table, the *model* is stale — regenerate. Hand-edits to generated model files are flagged as `manual-edit-of-generated`.

## Overrides

### aspnet-core
- `http_api = <flat>` — minimal-hosting endpoints registered in `{WebProject}/Api/ApiEndpoints.cs`; no `Controllers/` or per-resource files.
  - **Why:** the API is a small façade; full MVC controllers would add ceremony for no benefit.
  - **Recommended future direction:** if endpoints grow past ~15, split into `{WebProject}/Api/{Area}Endpoints.cs`.
```

### `.ai/solution-patterns.csv` (generated, one row per artifact)

One row per code file. Columns — names are the contract, don't rename them. **Path-derivable correspondences get a column; reference-based and convention-only ones don't (they're owned by `layout-guidelines.instructions.md` and `developer.instructions.md` respectively).**

| Column | Example | Source |
|---|---|---|
| `CodePath` | `{Project}/{Sub}/{Name}.cs` | Filesystem scan (primary key). |
| `Role` | `page`, `endpoint`, `desktop-view`, `view-model`, `companion`, `model`, `service`, `style`, `test` | Inferred from extension + name suffix via the stack's reference file. |
| `ExpectedNavPath` | `/{Sub}/{Name}` (page); `{VERB} /api/{path}` (endpoint); `{Top} > {Sub} > {Name}` (desktop-view). Blank when Role is not navigation-facing. **Interpretation depends on Role.** | Stack default, overridable via `.instructions.md`. |
| `ActualNavPath` | Read from route table / endpoint registration / nav XAML / attribute routes. | Stack-specific discovery (see `references/{stack}-patterns.md`). |
| `ExpectedCompanionPath` | `{Sub}/{Name}.cshtml` for `{Name}.cshtml.cs`; `{Sub}/{Name}.xaml.cs` for `{Name}.xaml`; `ViewModels/{Name}ViewModel.cs` for `Views/{Name}.xaml`. Blank when Role has no companion. | Companion rule from stack reference. |
| `ActualCompanionPath` | Filesystem scan. | |
| `ExpectedTestPath` | `{Project}.Tests/{Sub}/{Name}Tests.cs` | qa-tester §5.2 mirror. |
| `ActualTestPath` | Filesystem scan + `@under-test` header lookup (reuses qa-tester logic). | |
| `ExpectedSqlTable` | `dbo.{Name}` — only set when the project declares an `sql-model` SSOT direction in `.instructions.md`. Blank otherwise. | Per-project SSOT block. |
| `ActualSqlTable` | Read from sqlproj / migration files. | |
| `Deviation` | enum (see §5) | Computed. |
| `Notes` | `AutomationId={Screen}.{Element}` or `See override: aspnet-core.http_api` | Free text. Only set when the AI has a concrete remark. |

**Why a CSV, not JSON/YAML:** Excel-native, diffable in PR review, trivially grep-able, and the column contract forces a flat shape. Power Query can refresh an Excel view straight from the file — see [`assets/`](assets/) for an optional template (deferred for v1).

### `.ai/solution-patterns.nav.json` (derived sidecar — DO NOT hand-edit)

Generated from the CSV by `pattern_map.py`. Three projections of the URL tree, computed from `Role=page` rows + their `ExpectedNavPath` + page titles:

- **Route table:** `{ "/Agents/Jobs": { codePath: "...", title: "Jobs" }, ... }` — every page keyed by route.
- **Breadcrumb map:** `{ "/Agents/Jobs": ["Home", "Agents", "Jobs"], ... }` — each route's parent walk joined into a breadcrumb.
- **Sidebar tree:** nested `{ name, route, children: [...] }` — pages grouped by URL parent into a navigable tree.

These are pure projections — never hand-edit; regenerate. They give the AI human-readable navigation without bloating CSV columns. Compare this sidecar against the project's actual sidebar source (e.g. a `NavTree.cs`, sidebar XAML, or `_Layout.cshtml` partial — exact location lives in the per-project `.instructions.md`) to catch nav-tree drift from the route truth.

## 5. Deviation codes (enumerated, append-only)

| Code | Meaning | Agent action |
|---|---|---|
| `none` | All `Expected*` columns either match their `Actual*` counterpart or are blank. | Continue. |
| `nav-mismatch` | `ExpectedNavPath` is discoverable but differs from `ActualNavPath` (route, REST endpoint, or desktop breadcrumb depending on Role). | Open `.instructions.md`; if an override explains it, record as accepted. Otherwise recommend the expected path (may be declined). |
| `nav-missing` | Code file is navigation-facing but no route / endpoint / menu reference was found. | File may be orphaned, lazy-loaded via a non-standard mechanism, or dead. Ask the user. |
| `companion-missing` | Role has a companion rule but `ActualCompanionPath` doesn't exist (e.g. `.cshtml` without `.cshtml.cs`, or vice versa). | Create the missing companion or remove the orphan after confirming with the user. |
| `test-missing` | `ExpectedTestPath` does not exist. | Defer to qa-tester's §5.4 locate-or-create algorithm. |
| `test-relocated` | A test exists at a different path but its `@under-test` header points at this file. | Leave in place; add `// TODO: relocate to {expected}` per qa-tester §5.4. |
| `sql-model-stale` | `ExpectedSqlTable` is set, both sides exist, but their shapes (column set, types) disagree AND the `.instructions.md` declares a canonical side. | Regenerate the *generated* side using the declared generator (e.g. `Generate-Models.ps1`). Never hand-edit the generated artifact to "fix" the drift. |
| `manual-edit-of-generated` | Hand-edit detected on a file that the `.instructions.md` declares as generated (e.g. by file header marker, `[GeneratedCode]` attribute, or known generator-output path). | Revert the manual edit and re-run the generator; if the change must persist, update the *canonical* side (the SQL schema, in this repo's case) and regenerate. |
| `off-convention` | The code path itself doesn't match any recognised pattern for the detected stack — a reader cannot predict the sidebar entry, URL, or test path from the file's location. Violates the §2 expectation invariant. | The strongest signal of inconsistency. Recommend rename **unless** `.instructions.md` documents an explicit override with a "why" (compliance, third-party contract, externally-frozen schema, declared historical migration). Undeclared `off-convention` rows should always be raised as defects, not accepted silently. |

**Append-only rule:** add a new code when you genuinely can't fit a deviation into the existing set, not when an existing code feels "almost right".

## 6. Onboarding workflow (first run in a repo)

Run these in order. Each is idempotent; re-running costs nothing.

1. **Detect stacks.** `python .claude/skills/solution-patterns/scripts/detect_stack.py --json` → list of stacks (`wpf`, `winui`, `winforms`, `aspnet-core`, `angular`, `nextjs`). Zero matches → the skill has nothing to offer for this repo; exit gracefully.
2. **Draft `.ai/solution-patterns.instructions.md`** (if it doesn't exist): populate `## Detected stacks` with evidence (the `.csproj` / `package.json` line that matched), leave `## Overrides` empty. Ask the user to confirm before proceeding — they may know about a stack the auto-detector missed.
3. **Generate the CSV.** `python .../scripts/pattern_map.py` writes `.ai/solution-patterns.csv`. Output is deterministic — safe to commit.
4. **Run the deviation report.** `python .../scripts/validate_patterns.py` prints a summary by deviation code and highlights any `off-convention` rows. For each non-`none` row, show the user the reason and ask whether to (a) accept and record in `.instructions.md` as an override, (b) plan a rename, or (c) defer.

## 7. Per-task workflow (every coding task that touches a tracked artifact)

Before creating, renaming, or relocating any page, endpoint, view, view-model, model, companion file, or test:

1. **Read `.ai/solution-patterns.instructions.md`** — declared overrides and SSOT directions supersede stack defaults.
2. **Grep `.ai/solution-patterns.csv`** for the file you're about to touch (or the file that should exist). The row already answers all the predictable questions: where should it live? what's its expected route / REST endpoint / breadcrumb? what's its expected companion? what's its expected test path? what SQL table does it correspond to (if any)?
3. **Apply the expected paths** when creating new files, unless an override directs otherwise. When adding a `page`, predict the test path AND companion path AND nav position in advance — they should all land on the first try.
4. **For SQL ↔ Model work:** never hand-edit the *generated* side. If the generated artifact needs a new field, change the canonical side (per the SSOT direction declared in `.instructions.md`) and re-run the declared generator. Hand-edits to the generated side trigger `manual-edit-of-generated`.
5. **After the change:** `python .../scripts/pattern_map.py --affected <paths>` refreshes only the affected rows AND regenerates the `.nav.json` sidecar. Commit the CSV + sidecar alongside the code change — the diff shows the structural impact in a single glance.

**Shortcut for "where does X go?" questions:** the CSV alone answers. No need to rerun detection or validation.

## 8. Authoring a new `references/{stack}-patterns.md`

When a repo needs a stack we don't ship a reference for, add it. The reference file must define:

1. **Stack signal** — exact string that [`detect_stack.py`](scripts/detect_stack.py) looks for (file name, config key, NuGet/npm package). One regex or one filesystem probe.
2. **Role inference** — table mapping file extensions / name suffixes to the `Role` column enum. Example for Angular: `*.component.ts` → `ui-view`, `*.service.ts` → `service`, `*.module.ts` → `module`.
3. **Code → ExpectedNavPath rule** — the transform, per Role. Examples:
   - Angular `page`: `src/app/{feature}/{name}-page/{name}-page.component.ts` → `/{feature}/{name}` (derived from `Routes` declaration, not from folder alone — see the file).
   - Razor `page`: `Pages/{Area}/{Name}.cshtml` → `/{Area}/{Name}`.
   - Razor `endpoint`: row in `Api/ApiEndpoints.cs` → `{verb} /api/{path}` (when `http_api = <flat>` override is in effect).
   - WPF `desktop-view`: `Controls/{Name}Panel.xaml` → menu breadcrumb via the nearest `MenuItem`/`TabItem` in `MainWindow.xaml` whose `Content` loads this control.
4. **Companion rule** — for Roles that have one: `.cshtml` ↔ `.cshtml.cs` (Razor), `View.xaml` ↔ `View.xaml.cs` (WPF code-behind), `View.xaml` ↔ `ViewModel.cs` (WPF MVVM pairing — declare which convention this repo uses).
5. **ActualNavPath discovery** — where the AI looks to confirm the *actual* route/endpoint/breadcrumb (route table file, endpoint registration, navigation XAML, attribute on controller, folder-based inference for Next.js).
6. **Anti-patterns specific to the stack** — the top 3 ways projects on this stack drift (seed from lived experience, not theory).

Keep each reference under ~150 lines. When a rule applies to all stacks, it belongs in this SKILL.md, not in a stack file.

## 9. Anti-patterns (append-only)

- **Hand-editing the CSV.** It gets overwritten on the next run of `pattern_map.py`. Put the rule in `.instructions.md` overrides instead.
- **Writing stack-universal rules in the per-project `.instructions.md`.** If the rule applies to every Angular repo, it belongs in [`references/angular-patterns.md`](references/angular-patterns.md). The per-project file is for *this* repo's choices.
- **Forcing Angular to mirror routes in folders.** Goes against the official Angular style guide, which explicitly separates folder structure (developer convenience) from routing (user convenience). Angular deviations are normal; enforce the declared feature-folder pattern, not a fabricated folder=route rule.
- **Using `solution-patterns` without `qa-tester`.** The `ExpectedTestPath` / `ActualTestPath` columns depend on qa-tester's §5.2 mirror rule and `@under-test` headers. Without qa-tester, those two columns are blank and the deviation report loses its strongest signal.
- **Recommending a rename when `.instructions.md` documents an override.** The override is the declared truth for this repo. Recommend only when no override explains the deviation — and even then, propose, don't rewrite.
- **Shipping a stack reference file for a framework no project in the org uses.** Dead references age poorly and confuse the AI into applying rules nobody wanted. Add a file when a real project needs it.

## 10. Sync — propagating changes to all agents

This skill lives in `.ai/skills/solution-patterns/`, the single source of truth. After editing any file here, run the sync pipeline so the skill appears under `.claude/skills/`, `.roo/skills/`, `.github/skills/`:

```bash
python .ai/skills/ai-self-improvement/scripts/sync_agent_assets.py AUTO
```

See [`../ai-self-improvement/SKILL.md`](../ai-self-improvement/SKILL.md) for how the fan-out is configured.

## 11. Meta — rules for AIs editing this skill later

1. **Size budget.** Keep this SKILL.md under ~400 lines. Move anything deeper into [`references/`](references/) or [`scripts/`](scripts/).
2. **Four reference files max (one per stack) unless a new stack demands one.** Don't pre-emptively add MAUI, Flutter, Blazor, Svelte — ship them when a real project needs them.
3. **Deviation codes (§5) are append-only.** Removing a code breaks CSVs older tooling produced.
4. **CSV column names (§4) are the contract.** Never rename `CodePath`, `Role`, `ExpectedNavPath`, `ActualNavPath`, `ExpectedCompanionPath`, `ActualCompanionPath`, `ExpectedTestPath`, `ActualTestPath`, `ExpectedSqlTable`, `ActualSqlTable`, `Deviation`, `Notes` without updating every script and every consuming skill. Adding a column at the end is safe; renaming or reordering is not. *Note:* the v0 column names `ExpectedUiPath` / `ActualUiPath` were renamed to `ExpectedNavPath` / `ActualNavPath` to reflect that one column covers route, REST endpoint, and desktop breadcrumb (interpretation per Role). No CSVs were deployed under the old names; future renames must be migration-flagged.
5. **Scripts have zero required arguments.** They auto-discover the repo root. This matches [`qa-tester/scripts/test_map.py`](../qa-tester/scripts/test_map.py) and is the contract with calling AIs.
6. **`pattern_map.py` output must be deterministic** (sorted rows, stable column order, UTF-8, LF line endings). *Why:* unstable CSVs produce noisy PR diffs that obscure real structural changes.
7. **Never auto-apply renames.** The skill recommends; the human (or the AI acting on explicit instruction from the human) performs the rename. Structural refactors are a separate, reviewed activity.

## 12. Related skills

- [`qa-tester`](../qa-tester/SKILL.md) — Code ↔ Test mirror, `@under-test` headers, impact-scoped test selection. This skill reuses qa-tester's mirror rule to populate the test columns of the CSV.
- [`ai-self-improvement`](../ai-self-improvement/SKILL.md) — how and where to edit skills, the sync pipeline.
- [`repository-analysis`](../repository-analysis/SKILL.md) — broader repo architecture mapping. Useful companion when onboarding, but coarser-grained than this skill's per-file table.
