# WPF / WinUI / WinForms patterns

> Scope: Windows desktop apps using WPF, WinUI 3, UWP XAML, or WinForms. "UI path" for desktop means the **menu breadcrumb** (e.g. `MainWindow > Settings > Options`) rather than a URL. The AutomationId convention ties directly to qa-tester §6.4.

## 1. Stack signal

[`detect_stack.py`](../scripts/detect_stack.py) flags this stack when a `.csproj` contains one of:

- `<UseWPF>true</UseWPF>` → WPF
- `<UseWinUI>true</UseWinUI>` or `Microsoft.WindowsAppSDK` package → WinUI 3
- `<UseWindowsForms>true</UseWindowsForms>` → WinForms
- `TargetFramework` ending in `-windows10.0.*` with XAML files present → UWP

A project can declare more than one (rare but valid, e.g. WPF + WinForms interop); report each detected flavour.

## 2. Role inference (extension + filename → CSV `Role` column)

| File pattern | `Role` |
|---|---|
| `*.xaml` (main top-level window, usually `MainWindow.xaml`) | `shell` |
| `Views/**/*View.xaml`, `Views/**/*Page.xaml`, `Views/**/*Window.xaml` | `ui-view` |
| `Controls/**/*.xaml`, `UserControls/**/*.xaml` | `ui-view` (reusable panel/control) |
| `*.xaml.cs` (code-behind sibling of any `.xaml`) | `code-behind` |
| `ViewModels/**/*ViewModel.cs`, `**/*ViewModel.cs` | `view-model` |
| `Models/**/*.cs`, `Domain/**/*.cs` | `model` |
| `Services/**/*.cs`, `**/*Service.cs` | `service` |
| `Converters/**/*.cs` | `converter` |
| `Behaviors/**/*.cs` | `behavior` |
| `Resources/**`, `App.xaml` | `resource` |
| `App.xaml.cs`, `Program.cs` | `bootstrap` |
| WinForms only: `*.Designer.cs` | `designer-generated` (not scanned) |
| WinForms only: `*Form.cs` + `*Form.Designer.cs` + `*Form.resx` set | `ui-view` (the `*.cs` file is the row; `.Designer.cs` and `.resx` are associated but not separate rows) |

## 3. Default Code → UI (breadcrumb) path rule

Two legitimate default layouts — both ship as "on convention". The project declares its choice in `.instructions.md`.

### Layout A — by-type (flat `Controls/` or `Views/`)

```text
App/MainWindow.xaml
App/Controls/AboutPanel.xaml          → MainWindow > About
App/Controls/SettingsControl.xaml     → MainWindow > Settings
App/Controls/OptionsPanel.xaml        → MainWindow > Settings > Options
```

This is what the AiPlatform `WorkspaceManager/App/` project uses today. Breadcrumbs are derived from the nearest `MenuItem` / `TabItem` / `NavigationView.MenuItems` entry in `MainWindow.xaml` (or the shell XAML) that loads the control.

### Layout B — by-feature (MVVM, `Views/` mirrors the menu)

```text
App/MainWindow.xaml
App/Views/About/AboutView.xaml         → MainWindow > About
App/Views/Settings/SettingsView.xaml   → MainWindow > Settings
App/Views/Settings/OptionsView.xaml    → MainWindow > Settings > Options
App/ViewModels/About/AboutViewModel.cs (paired with AboutView)
```

Preferred for new projects — the folder tree *is* the menu tree, and Caliburn.Micro / Prism / MVVM Toolkit conventions all assume `{Name}View` ↔ `{Name}ViewModel` pairing.

**Default inferred breadcrumb:** `<Shell> > <Parent menu path> > <Name without suffix>`, where `<Name without suffix>` strips `View` / `Page` / `Panel` / `Control` / `Window` / `Form`.

## 4. Actual breadcrumb discovery

Where to look, in order:

1. **Shell XAML** (`MainWindow.xaml`, `Shell.xaml`, `App.xaml`'s startup target): scan for `<MenuItem>`, `<TabItem>`, `<NavigationViewItem>`, `<RadioButton>` in a nav region. Each has either `Content=` with a control name, a `Command=` binding to a view-model action, or a `DataTemplate` pointing at a view type.
2. **Navigation code** (`INavigationService`, frame `Navigate(typeof(SettingsPage))` calls in code-behind or view-models): map the target type to its `.xaml` file.
3. **WinForms**: `mainMenu.Items.Add(new ToolStripMenuItem(...))` and `new SettingsForm().Show()` calls. Parse the designer-generated `.Designer.cs` carefully (don't write to it).

If nothing references a control, flag it `ui-missing`.

## 5. AutomationId convention (for qa-tester interop)

Every interactive control gets `AutomationProperties.AutomationId` in the format `Screen.Element` — this is qa-tester §7 ("Selectors") and §6.4. The `Notes` column records the inferred or declared AutomationId prefix for each UI row:

```text
CodePath: Controls/AboutPanel.xaml   Notes: AutomationId prefix = About.
CodePath: Controls/SettingsControl.xaml  Notes: AutomationId prefix = Settings.
```

Interactive controls without AutomationIds are flagged as `off-convention` — qa-tester relies on them for stable selectors.

## 6. Default test path (reuses qa-tester §5.2)

Sibling `{Project}.Tests/` project, folder-mirrored:

| Code path | `ExpectedTestPath` |
|---|---|
| `App/Controls/AboutPanel.xaml` | `App.Tests/Controls/AboutPanelTests.cs` |
| `App/Controls/AboutPanel.xaml.cs` | (same — one test file covers both the XAML and its code-behind) |
| `App/ViewModels/AboutViewModel.cs` | `App.Tests/ViewModels/AboutViewModelTests.cs` |
| `App/Services/OrderService.cs` | `App.Tests/Services/OrderServiceTests.cs` |

Test for a view-model = MSTest direct instantiation (no framework, 90% of coverage). Test for the XAML = `System.Windows.Automation` smoke test launching the exe. See qa-tester §6.4.

## 7. Stack-specific anti-patterns

- **Code-behind holding business logic.** If `AboutPanel.xaml.cs` contains anything beyond event forwarding to the view-model, the `view-model` column in the CSV lies. Flag as `off-convention` and recommend moving logic to the view-model.
- **Missing AutomationId on interactive controls.** qa-tester test writers can't target the control without one. This is the single most common deviation and usually the reason a desktop test project is stuck.
- **Navigation expressed three different ways in the same app** (Frame.Navigate + INavigationService + direct `new Window().Show()`). Pick one; document in `.instructions.md`.
- **ViewModels in a sibling project without `InternalsVisibleTo`** to the `.Tests` project. Tests can't instantiate them. Report as a test-infrastructure deviation in `Notes`.
- **Flat `Controls/` folder mixed with `Views/{Feature}/` folder in one app.** Pick Layout A or Layout B (§3) and stick to it — crossing them makes the breadcrumb discovery ambiguous.

## 8. References

- WPF overview: <https://learn.microsoft.com/dotnet/desktop/wpf/>
- MVVM in .NET: <https://learn.microsoft.com/dotnet/architecture/maui/mvvm>
- UI Automation (for AutomationId): <https://learn.microsoft.com/dotnet/framework/ui-automation/>
- qa-tester §6.4 (desktop smoke tests) and §7 (selectors): [`../../qa-tester/SKILL.md`](../../qa-tester/SKILL.md)
