# Solution Patterns — declared for FocusLogger

> **Scope:** This file records the per-project pattern overrides for the FocusLogger
> repository. Stack defaults live in
> [`.ai/skills/solution-patterns/references/wpf-winui-patterns.md`](./skills/solution-patterns/references/wpf-winui-patterns.md);
> the human-curated overrides below take precedence.
> The CSV companion [`.ai/solution-patterns.csv`](./solution-patterns.csv) is generated
> by [`scripts/pattern_map.py`](./skills/solution-patterns/scripts/pattern_map.py) and
> must not be hand-edited.

## Detected stacks

Auto-detected by [`detect_stack.py`](./skills/solution-patterns/scripts/detect_stack.py):

- **wpf** — `<UseWPF>true</UseWPF>` in both `FocusLogger/JocysCom.FocusLogger.csproj` and `FocusLogger.Tests/JocysCom.FocusLogger.Tests.csproj`.
- **winforms** — `<UseWindowsForms>true</UseWindowsForms>` in `FocusLogger/JocysCom.FocusLogger.csproj`.

WPF is the primary UI framework. WinForms is enabled only for P/Invoke and DPI-awareness helpers
shared with the embedded `JocysCom.ClassLibrary` source; there are no `*.Designer.cs` form files
in the tree and no WinForms windows are shown at runtime.

## Solution shape

```text
JocysCom.FocusLogger.slnx                       ← solution file (.slnx XML format)
├── FocusLogger/                                ← main product (WPF, net8.0-windows)
│   ├── App.xaml + App.xaml.cs                  Role=bootstrap
│   ├── MainWindow.xaml + MainWindow.xaml.cs    Role=shell — the only top-level window
│   ├── Controls/                               Reusable WPF UserControls (DataList, …)
│   ├── Resources/Icons/                        Static XAML resource dictionaries
│   └── JocysCom/                               Embedded class library — DO NOT EDIT IN PLACE
│       ├── Controls/                           Shared controls (InfoControl, MessageBoxWindow)
│       │   └── Themes/                         Shared resource dictionaries
│       ├── Configuration/                      Settings/serialization helpers
│       ├── Processes/                          P/Invoke + focus-tracking primitives
│       └── …                                   Other JocysCom.ClassLibrary subsystems
└── FocusLogger.Tests/                          ← MSTest test project (net8.0-windows)
    └── …                                       Mirrors FocusLogger/ folder-for-folder
```

## SSOT directions

This repo has no SQL data project and no code-generation pipeline. There are no name-mapping
correspondences (Model ↔ SQL table) to declare a canonical direction for.

The only structural SSOT direction in the codebase is the **embedded `JocysCom.ClassLibrary` source
tree** under `FocusLogger/JocysCom/`. It is copied in verbatim from the
[JocysCom.ClassLibrary](https://github.com/JocysCom/ClassLibrary) repository and should be treated
as upstream-canonical:

- **Canonical side:** the upstream JocysCom.ClassLibrary repository.
- **Generated/mirrored side:** `FocusLogger/JocysCom/**`.
- **Refresh path:** pull the latest sources from upstream rather than hand-editing in this repo.
- **Implication for the deviation report:** off-convention placements *inside* `FocusLogger/JocysCom/`
  reflect upstream choices, not FocusLogger choices — record them here as accepted overrides
  rather than recommend renames.

## Overrides

### wpf

- **Layout = A (by-type, flat `Controls/`)** — matches the WPF reference's "Layout A". The product
  has a single shell (`MainWindow.xaml`) hosting one reusable control (`Controls/DataListControl.xaml`)
  plus dialogs from the embedded library. There is no `Views/` + `ViewModels/` MVVM tree; logic lives
  in code-behind, which is acceptable for a single-window diagnostic utility of this size.
  - **Breadcrumb derivation:** `MainWindow > DataList` for the data grid panel; dialogs (e.g.
    `MessageBoxWindow`) are modal and not breadcrumb-reachable.
  - **Recommended future direction:** if the app grows a second top-level panel or settings dialog,
    introduce a `ViewModels/` folder and migrate per-control logic; until then, code-behind is the
    intentional default and `view-model = missing` is not a defect.

- **`view-model` Role is intentionally absent** — no `*ViewModel.cs` files exist in
  `FocusLogger/`. CSV rows for code-behind never project an `ExpectedViewModelPath` because the
  project does not declare an MVVM convention.

- **AutomationId convention** — the WPF reference (§5) mandates
  `AutomationProperties.AutomationId="Screen.Element"` on interactive controls. The
  `Notes` column on `ui-view` CSV rows records the inferred `Screen` prefix
  (e.g. `AutomationId prefix = DataList.`). Interactive controls that ship without an
  AutomationId are an `off-convention` defect to be fixed before adding qa-tester automation.

- **Embedded JocysCom.ClassLibrary path (`FocusLogger/JocysCom/**`) is an accepted override.**
  Pattern violations under this subtree (e.g. `Controls/Themes/Default.xaml` not following the
  WPF "themes are not ui-views" rule, deeper folder nesting than the host product uses) are
  not recommended for rename — they belong to upstream and must be fixed there, not here.
  `pattern_map.py` still emits rows for these files (so the table stays complete), but the
  deviation report should treat them as informational rather than actionable.

### winforms

- **Suppress `winforms` from breadcrumb derivation** — the stack is present only as an interop
  flag (P/Invoke, DPI). There are no `*Form.cs` files in the tree, no menu strips, no WinForms
  windows are shown. CSV rows derived from the `winforms` signal should be empty.

## Test layout

- **Test project:** `FocusLogger.Tests/` (MSTest v3, `net8.0-windows`).
- **Mirror rule:** path-for-path under `FocusLogger/` — per
  [qa-tester §5.2](./skills/qa-tester/SKILL.md). Example: `FocusLogger/Controls/DataListControl.xaml.cs`
  → `FocusLogger.Tests/Controls/DataListControlTests.cs`.
- **Current coverage:** sparse. The deviation report flags many `test-missing` rows — most are
  inside the embedded `JocysCom/` tree, where tests belong to the upstream class-library repo and
  are intentionally not duplicated here. Product-side `test-missing` rows (e.g.
  `Controls/DataListControl.xaml.cs`) are real deferrals tracked through `qa-tester`.

## Maintenance

1. **Regenerate the CSV** after structural changes:

   ```bash
   python3 .ai/skills/solution-patterns/scripts/pattern_map.py
   ```

2. **Run the deviation report** before opening structural PRs:

   ```bash
   python3 .ai/skills/solution-patterns/scripts/validate_patterns.py
   ```

3. **Fan out to agent folders** after editing any skill source:

   ```bash
   python3 .ai/skills/ai-self-improvement/scripts/sync_agent_assets.py AUTO
   ```

