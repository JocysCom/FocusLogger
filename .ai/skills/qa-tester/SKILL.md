---
name: qa-tester
description: Create and maintain automated tests in Microsoft-native/.NET projects with a minimal stack — MSTest runner, `System.Windows.Automation` for Windows desktop, Playwright for real browser smoke. Code-first, single-source-of-truth. Use whenever the user wants to write, review, structure, migrate, or plan tests for any .NET project (unit, API, database, WPF, WinUI, MAUI, Blazor, Razor) — even when the request says "test" without naming a framework.
---

# QA Tester

> **Core philosophy: one test runner, minimum tools, executable code is the spec.**
> The fewer different tools a codebase has, the lower the cognitive load on every engineer and AI that touches it. Prefer in-box Microsoft APIs; every extra dependency is a cost, not a feature.

## 1. First principles

Each principle has a *why* so you can judge edge cases instead of pattern-matching on the rule.

1. **Minimum tool surface.** Two tools that do the job beat five that do it elegantly. *Why:* every extra framework is cognitive debt owed by the next person who opens the repo.
2. **In-box first.** Prefer APIs that ship with .NET or Windows. *Why:* a test that runs with `dotnet test` on a clean checkout is the test that actually gets run.
3. **Code-first.** A test is the spec. Do not duplicate intent into Gherkin + bindings + helpers. *Why:* every layer of indirection is another place the next AI has to look.
4. **Readable beats clever.** A new engineer should understand a test in under 30 seconds.
5. **Lightest abstraction that still reads well.** Inline → helper → screen object → fixture. *Why:* page objects are a symptom of test duplication, not a solution.
6. **Stable selectors.** Roles, accessible names, `AutomationId`. Never CSS tied to layout internals. *Why:* a fragile selector is a test that will break for reasons unrelated to what it's checking. If a stable selector doesn't exist, fix the product first.
7. **Deterministic waits.** Use framework auto-waits or in-box event subscriptions. *Why:* `Thread.Sleep` hides real race conditions and taxes everyone else's suite time.
8. **Test the lowest layer that gives confidence.** Unit → API/integration → UI. *Why:* UI tests are slow, flaky, and tell you less than the integration test that already covers the same rule.
9. **Isolation.** No shared mutable state. Each test sets up and tears down its own world. *Why:* ordered tests and shared fixtures produce heisenbugs whose failure mode depends on run order — impossible to reproduce locally and demoralising for everyone on call.
10. **Minimal change.** Edit small. Don't rewrite suites unless asked. *Why:* a "while I'm in here" refactor turns a 5-line fix into a 500-line review and blocks the actual bug shipping.
11. **Test project must be simpler than the app.** One `{Project}.Tests` project by default. Mirror the product folder layout 1:1. Split into more projects only when a real constraint (headless CI, massive scale, different TFM) forces it. *Why:* a test project fractured into more pieces than the app it tests is absurd — every extra csproj duplicates infrastructure, slows the loop, and makes newcomers wonder which project to open.
12. **Performance data is a byproduct of functional tests.** If a code path already runs in CI under a unit / integration / UI test, attaching a lightweight in-box collector gives you perf coverage equal to your functional coverage at near-zero marginal cost. *Why:* a parallel "perf suite" that re-implements the same sign-in / order / search scenarios is pure duplication, and it creates coverage gaps wherever the two suites drift. Dedicated load/stress/soak tests exist only for what functional tests genuinely cannot express: concurrency, saturation, sustained throughput, and memory growth over time. See §6a.

## 2. The two-tool stack

| Tool | Ships from | Used for |
|---|---|---|
| **MSTest** (`Microsoft.NET.Test.Sdk` + `MSTest.TestFramework` + `MSTest.TestAdapter`) | NuGet / Microsoft | *Everything .NET*: unit, service, DB integration, API integration, **Windows desktop UI via `System.Windows.Automation`**, view-model tests for WPF/WinUI/MAUI-desktop. |
| **Playwright** (`Microsoft.Playwright` + `Microsoft.Playwright.MSTest`) | NuGet / Microsoft | Real-browser web UI smoke. Runs under the same MSTest runner as everything else — one test explorer, one `dotnet test` command. |

That's the whole stack. **`System.Windows.Automation`** is in-box (no NuGet), so it doesn't appear in the package list but is the default for any Windows desktop test.

**Performance collection (§6a)** uses only in-box instrumentation — `EventPipe` / `dotnet-trace`, `dotnet-gcdump`, `dotnet-counters`, SQL Server Extended Events, Playwright tracing, ETW via `wpr.exe` — plus one Microsoft-owned load generator (`Microsoft.Crank`). Collectors are runtime/OS facilities, not "tools", so the two-tool rule is unchanged.

**Quick exclusion list** (see [`references/legacy-bdd.md`](references/legacy-bdd.md) for inherited-project support):

| Excluded | Why |
|---|---|
| Appium / WinAppDriver | Driver process, HTTP wire protocol, installer step. `System.Windows.Automation` does the same job in-box. Exception: MAUI mobile (Android/iOS) — keep it in a dedicated `Tests/UI.Mobile/` project. |
| FlaUI | Thin wrapper around `System.Windows.Automation`. Use the in-box API directly. |
| Selenium | Playwright replaces it. |
| Cypress / TestCafe / WebDriverIO | Playwright replaces all of them. |
| NUnit / xUnit | One runner per repo — MSTest for Microsoft-aligned codebases. |
| SpecFlow / Reqnroll | Inherited-project support only. See [`references/legacy-bdd.md`](references/legacy-bdd.md). |
| Testcontainers for SQL Server | Use `SqlLocalDB` — no Docker dependency. |
| bunit | Use `WebApplicationFactory<T>` + HTTP first. |

Before adding any third tool, write one sentence justifying it. If the sentence is "it would be more convenient", reject it.

## 3. Layer → test type (the whole decision matrix)

| You want to test … | Use | Perf dimension it already measures (piggyback, §6a) |
|---|---|---|
| A pure business rule | **MSTest** unit test — direct instantiation, no framework | Method CPU, allocations, hot-path micro-regressions |
| A rule that needs HTTP / auth / DI / EF | **MSTest + `WebApplicationFactory<T>`** — in-process HTTP against the real middleware pipeline | End-to-end latency, middleware cost, per-request allocations, SQL count + text + shape (N+1 detector) |
| Real SQL Server behaviour (constraints, triggers, migrations) | **MSTest + `SqlLocalDB`** — `sqllocaldb create` + a connection string, no Docker | Query duration, logical reads, CPU time, actual plan, missing-index hints |
| A Razor / MVC page that renders mostly server-side | **MSTest + `WebApplicationFactory<T>` + `HttpClient`** — HTTP test, not a browser test | Same as integration-api |
| Genuine browser behaviour a server-side test can't express | **MSTest + Playwright** — keep the suite small, one or two happy-path tests per area | Navigation + resource timings, LCP/CLS/INP, long tasks, JS heap, network waterfall |
| A WPF / WinUI **view-model** rule | **MSTest** — instantiate the VM directly. Under MVVM this is 90% of desktop test coverage. | VM method CPU + allocations |
| A WPF / WinUI **launch / binding / wiring** check | **MSTest + `System.Windows.Automation`** — `Process.Start(exe)` + `AutomationElement.FromHandle` + `InvokePattern` / `ValuePattern` | Startup time, frame time, UI-thread stalls, managed allocs during interaction |
| A MAUI view-model rule | **MSTest** — direct VM instantiation | VM CPU + allocations |
| MAUI on the Windows target | **MSTest + `System.Windows.Automation`** — MAUI/Windows is a UIA tree | Same as WPF |
| MAUI on Android / iOS | Appium, isolated in `Tests/UI.Mobile/` — the single intentional exception | — (mobile perf is its own discipline) |
| Concurrency, throughput ceiling, saturation, soak, memory growth under load | **MSTest + `Microsoft.Crank`** scenario in `{Project}.Tests.Perf/` — the only place dedicated load/stress/soak lives. See §6a. | Thread-pool starvation, GC pressure under load, leak detection via bracketed `gcdump` |

**Default rule of thumb:** MSTest + `System.Windows.Automation` covers every .NET desktop scenario; MSTest + Playwright covers every web scenario. If you reach for a third tool, re-read §2.

## 4. Writing style — code-first, business-readable second

When the user says:
> Given a valid user, when they sign in, then they should see the dashboard

Write this:

```csharp
// @under-test: src/Foo.Web/Pages/SignIn.razor
// @area: auth   @layer: ui-web
[TestClass]
public class SignInTests : PageTest
{
    [TestMethod]
    [TestCategory("auth"), TestCategory("smoke")]
    [Description("Valid user signs in and lands on dashboard")]
    public async Task Valid_user_signs_in_and_lands_on_dashboard()
    {
        // Given: a valid user on the sign-in page
        await Page.GotoAsync("/sign-in");

        // When: they sign in with valid credentials
        await Page.GetByLabel("Email").FillAsync("valid.user@example.com");
        await Page.GetByLabel("Password").FillAsync(Environment.GetEnvironmentVariable("TEST_USER_PASSWORD")!);
        await Page.GetByRole(AriaRole.Button, new() { Name = "Sign in" }).ClickAsync();

        // Then: the dashboard is visible
        await Expect(Page).ToHaveURLAsync(new Regex("/dashboard$"));
        await Expect(Page.GetByRole(AriaRole.Heading, new() { Name = "Dashboard" })).ToBeVisibleAsync();
    }
}
```

The Given/When/Then phrasing lives in **test name + comments + `[TestCategory]` tags + `[Description]`**. No `.feature` file, no bindings, no regex maintenance, no indirection. A reporter that lifts `[Description]` + `[TestCategory]` into Markdown covers every "but stakeholders need to read it" objection without introducing BDD tooling.

## 5. Discoverability — finding tests from a code path (and vice versa)

> For Code ↔ UI mapping (web routes, desktop menu breadcrumbs), see the [`solution-patterns`](../solution-patterns/SKILL.md) skill. This section covers Code ↔ Test only.

This section is load-bearing. Renaming any convention here breaks every future locate-or-create query.

### 5.1 Test project naming

**Default: one test project per product project** — `{Project}.Tests`, sibling to `{Project}`. *Why:* a test project more complex than the app it tests is absurd; the whole point of §1.1 (minimum tool surface) applies to the test tree too. One csproj, one namespace root, one `dotnet test` command.

Split into multiple projects **only** when one of these is actually true:

- **Headless CI constraint.** UI tests need a graphical session; unit and integration tests must pass on a headless build server. Split into `{Project}.Tests` (headless-safe) and `{Project}.Tests.UI` (requires a desktop session). Tag the UI csproj so CI can skip it in headless runs, e.g. `<IsTestProject>true</IsTestProject>` plus a `[TestCategory("ui-interactive")]` filter.
- **Large codebase.** Hundreds of product files and thousands of tests where a single csproj's compile + test-discovery time noticeably slows the loop. This is rare in practice.
- **Fundamentally different runtime.** e.g. product targets `net8.0` but one test layer needs `net48` for COM interop.
- **Dedicated perf/load/soak suite.** `{Project}.Tests.Perf/` houses `Microsoft.Crank` scenarios and long-running soak tests. Its runtime constraints are genuinely different: long durations, non-parallel with the functional suite, its own CI job, statistical gating instead of pass/fail per run. See §6a.5. Do not put piggyback perf collectors here — those belong next to the functional tests whose coverage they inherit.

**Do not split** because "separation of concerns" or "unit vs integration is cleaner" — those are solved by folder structure and `[TestCategory]` tags, not by csproj boundaries. Extra csprojs bring: duplicated `[AssemblyInitialize]` code, duplicated `TestSandbox`/`TestHelpers`, multiple `InternalsVisibleTo` grants, separate `Directory.Packages.props` entries, and separate test hosts that all have to be kept in sync. **Pay that cost only when a real constraint forces it.**

Naming, whichever variant you pick: `{Project}.Tests` or `{Project}.Tests.UI`. One spelling forever. Never `{Project}Tests`, never `Test.{Project}`, never `{Project}.UnitTests`.

### 5.2 File-to-file mapping (deterministic)

Folders inside the test project mirror folders inside the product project **1:1**. Never flatten — reversibility is the whole point. The product sub-path becomes the test sub-path verbatim, with `Tests` appended to the class-file name.

**Default (single `{Project}.Tests` project):**

| Product file | Test file |
|---|---|
| `{Project}/{Sub}/{Name}.cs` | `{Project}.Tests/{Sub}/{Name}Tests.cs` |
| `{Project}/Controllers/{Name}Controller.cs` | `{Project}.Tests/Controllers/{Name}ControllerTests.cs` |
| `{Project}/ViewModels/{Name}ViewModel.cs` | `{Project}.Tests/ViewModels/{Name}ViewModelTests.cs` |
| `{Project}/Views/{Name}View.xaml` (WPF) | `{Project}.Tests/Views/{Name}ViewTests.cs` |
| `{Project}/Pages/{Name}.razor` (or `.cshtml`) | `{Project}.Tests/Pages/{Name}Tests.cs` |

**Split form (only when §5.1's split criteria apply):** the UI-requiring tests move to `{Project}.Tests.UI/` using the same sub-path mirror; everything else stays in `{Project}.Tests/`. No other splits.

**Namespace rule:** every test file uses the single root namespace `{Project}.Tests` (or `{Project}.Tests.UI`), regardless of which subfolder it lives in. *Why:* sub-namespacing per folder forces a cross-file `using` hunt every time a test helper moves, with no discoverability benefit — the folder is right there in the solution explorer. The `@under-test` header (§5.3) is the authoritative coverage link, not the namespace.

*Locating a test file:* given `{Project}/Foo/Bar/Baz.cs`, the test is at `{Project}.Tests/Foo/Bar/BazTests.cs`. No lookup, no search — pure string transform. That is the whole point of the mirror.

### 5.3 Mandatory test-file header

Every test file declares the product file it covers:

```csharp
// @under-test: src/Foo.Bar/Services/OrderService.cs
// @area: orders   @layer: unit   @ticket: JIRA-1234
```

Rules: `@under-test` is required, repo-relative, forward slashes, no globs. Multi-file tests list at most three paths comma-separated; more means the test is too broad — split it. `@layer` is one of `unit | integration-api | integration-db | ui-web | ui-wpf | ui-maui | perf`. Optional: `@perf-capture: always` forces piggyback collection even when `QA_PERF_CAPTURE` is unset — use only for known hot paths whose perf you always want a baseline for.

*Why this matters:* reverse coverage queries become one ripgrep (`rg "@under-test:\s*src/Foo.Bar/Services/OrderService.cs" Tests/`) instead of a semantic search.

### 5.4 Locate-or-create algorithm

Adding/modifying a test for product file `P`:

1. Compute expected path `T` from §5.2.
2. If `T` exists → edit it.
3. Else `rg "@under-test:.*P"` across `Tests/` — if a hit exists at a non-canonical path, edit it and leave `// TODO: relocate to {T}`.
4. Else search by symbol name (`{Name}Tests`). Same rule.
5. Else create `T` with the `@under-test` header.

### 5.5 Coverage verification + impact-scoped test selection

[`scripts/test_map.py`](scripts/test_map.py) automates the §5.2 mirror check and the §5.3 `@under-test` header lookup. Zero required arguments — auto-discovers the `{Project}` + `{Project}.Tests` pair from the current directory. Cross-platform (Windows, Linux, macOS — runs in containers, CI, Codex).

```bash
# Coverage gap report (default — run from repo root, no arguments needed)
python test_map.py
#   Output: table of OK / MISSING / ORPHAN / WRONG_HEADER per product file

# Impact analysis: which tests cover my recent changes?
python test_map.py --affected HEAD~1
#   Output: direct changes + transitive dependents (2-level type-name grep) + filter string

# JSON for AI consumption
python test_map.py --affected HEAD~3 --json
```

The `--affected` mode produces a `dotnet test --filter` string that includes every mirror-path test + every crosscutting test whose `@under-test` header mentions any affected file + `TestCategory=critical`. The AI supplements this list by using whatever reference-finding capability its IDE/platform provides — e.g. `find_references` in VS Code (Claude Code, GitHub Copilot), `find_usages` in JetBrains (Roo Code), or `Go to References` in Visual Studio — to chase shared interfaces/base classes where string-grep may miss semantic dependents. See [`references/test-selection.md`](references/test-selection.md) for the detailed workflow.

**Standard severity categories** for filtering (§7 naming convention applies):

| Category | Meaning | When to run |
|---|---|---|
| `critical` | Fast unit/service tests that catch the most important regressions. See criteria below. | Every build, every commit (~10 s) |
| *(no tag)* | Normal importance — the default. | PR check |
| `stress` | Concurrency, soak, memory growth. Slow (>10 s per test). | Pre-release, nightly |
| `ui-interactive` | Needs a desktop session (`System.Windows.Automation`). | Developer machine |
| `requires-elevation` | Triggers UAC / needs admin. Locked-down VMs cannot run these. | Developer machine with admin rights |
| `projfs` | Needs Client-ProjFS Windows feature. | Developer machine with ProjFS |

**What to tag `critical`** — a test earns this tag when ALL of these are true:

1. **Fast.** Runs in under 1 second. If it needs ProjFS, a database, a browser, an exe launch, or a network call, it is not critical — it belongs in a slower category. The whole point of `critical` is a 5–10 second feedback loop.
2. **Covers a code path where a bug causes data loss, crashes, or silent corruption.** Examples: config load/save (losing projections), manifest read/write (losing the file list), hash comparison (false "in sync"), single-instance mutex (app refuses to start), provider state machine (delete propagates to Source instead of just manifest).
3. **Is a unit or service test, not an integration or UI test.** `critical` tests must run on any machine — headless CI, a locked-down VM, a container, a developer laptop — with zero external dependencies. If it needs the Client-ProjFS feature, a desktop session, admin elevation, or a specific folder on disk, tag it with the appropriate category instead.

*Why this matters:* `dotnet test --filter "TestCategory=critical"` is the developer's 10-second sanity check between edits. If critical tests include slow ProjFS integration tests, the filter becomes useless and developers stop using it. If critical tests miss the config-persistence path, a developer ships a bug that loses every user's projection list. The tag is the contract between "this is cheap enough to run constantly" and "this catches the bugs that matter most."

```bash
dotnet test --filter "TestCategory=critical"                                                          # fast dev loop
dotnet test --filter "TestCategory!=stress&TestCategory!=ui-interactive&TestCategory!=requires-elevation"  # PR / CI (headless, no admin)
dotnet test --filter "TestCategory!=requires-elevation"                                               # developer machine (has desktop, no admin)
dotnet test                                                                                           # release gate (full, interactive, admin)
```

## 6. Examples

Four examples, one per major layer. Each is runnable; no pseudo-code.

### 6.1 Unit test

```csharp
// @under-test: src/Foo.Bar/Services/OrderTotals.cs
// @area: orders   @layer: unit
[TestClass]
public class OrderTotalsTests
{
    [TestMethod]
    public void Total_sums_line_items_with_tax()
    {
        var items = new[] { new LineItem(10m), new LineItem(20m) };
        Assert.AreEqual(33m, new OrderTotals(taxRate: 0.10m).Compute(items));
    }
}
```

### 6.2 API integration — replaces most "page renders" UI tests

`WebApplicationFactory<Program>` needs the product's `Program.cs` to expose `Program` as a type. In a top-level-statements project add this at the bottom of `Program.cs`:

```csharp
public partial class Program { }
```

Then the test (needs `using System.Net.Http.Headers;`, `using System.Text;`, `using Microsoft.AspNetCore.Mvc.Testing;`):

```csharp
// @under-test: src/Foo.Web/Controllers/OrdersController.cs
// @area: orders   @layer: integration-api
[TestClass]
public class OrdersApiTests
{
    private static WebApplicationFactory<Program> _factory = null!;
    private HttpClient _client = null!;

    [ClassInitialize]
    public static void Setup(TestContext _) => _factory = new WebApplicationFactory<Program>();

    [ClassCleanup]
    public static void Teardown() => _factory.Dispose();

    [TestInitialize]
    public void SetupClient() => _client = _factory.CreateClient();

    [TestMethod, TestCategory("orders"), TestCategory("smoke")]
    public async Task Get_orders_returns_empty_array_for_new_user()
    {
        var creds = Convert.ToBase64String(
            Encoding.UTF8.GetBytes("new.user@example.com:" + Environment.GetEnvironmentVariable("TEST_USER_PASSWORD")));
        _client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Basic", creds);

        var response = await _client.GetAsync("/api/orders");
        response.EnsureSuccessStatusCode();
        Assert.AreEqual("[]", await response.Content.ReadAsStringAsync());
    }
}
```

Any test that was reaching for Playwright just to assert "page loads, contains X" belongs here instead. 10× faster, no browser dependency.

### 6.3 Playwright web smoke — same MSTest runner

```csharp
// @under-test: src/Foo.Web/Pages/SignIn.razor
// @area: auth   @layer: ui-web
[TestClass]
public class SignInSmokeTests : PageTest
{
    [TestMethod, TestCategory("auth"), TestCategory("smoke")]
    public async Task Valid_user_signs_in_and_lands_on_dashboard()
    {
        await Page.GotoAsync("/sign-in");
        await Page.GetByLabel("Email").FillAsync("valid.user@example.com");
        await Page.GetByLabel("Password").FillAsync(Environment.GetEnvironmentVariable("TEST_USER_PASSWORD")!);
        await Page.GetByRole(AriaRole.Button, new() { Name = "Sign in" }).ClickAsync();
        await Expect(Page).ToHaveURLAsync(new Regex("/dashboard$"));
        await Expect(Page.GetByRole(AriaRole.Heading, new() { Name = "Dashboard" })).ToBeVisibleAsync();
    }
}
```

### 6.4 WPF / WinUI smoke via `System.Windows.Automation` (in-box)

Every interactive control gets `AutomationProperties.AutomationId` in the format `Screen.Element`. No AutomationId → fix the XAML first, don't write the test.

```xml
<Button      AutomationProperties.AutomationId="SignIn.Submit" Content="Sign in" />
<TextBox     AutomationProperties.AutomationId="SignIn.Email" />
<PasswordBox AutomationProperties.AutomationId="SignIn.Password" />
```

```csharp
// @under-test: src/Foo.Desktop/Views/SignInView.xaml
// @area: auth   @layer: ui-wpf
using System.Windows.Automation;

[TestClass]
public class SignInSmokeTests
{
    private Process _proc = null!;
    private AutomationElement _window = null!;

    [TestInitialize]
    public void Launch()
    {
        _proc = Process.Start(@"bin\Release\MyApp.exe")!;
        _proc.WaitForInputIdle();
        _window = WaitFor(() => AutomationElement.FromHandle(_proc.MainWindowHandle), TimeSpan.FromSeconds(5));
    }

    [TestCleanup] public void Close() { if (!_proc.HasExited) _proc.Kill(); _proc.Dispose(); }

    [TestMethod, TestCategory("desktop"), TestCategory("smoke")]
    public void Valid_user_signs_in()
    {
        ById("SignIn.Email").SetValue("valid.user@example.com");
        ById("SignIn.Password").SetValue("***");
        ById("SignIn.Submit").Invoke();

        var heading = WaitFor(() => ById("Dashboard.Title"), TimeSpan.FromSeconds(5));
        Assert.AreEqual("Dashboard", heading.Name);
    }

    // Minimal intent-level wrappers so test bodies don't see UIA pattern ceremony.
    private Ui ById(string id) => new(_window.FindFirst(TreeScope.Descendants,
        new PropertyCondition(AutomationElement.AutomationIdProperty, id))
        ?? throw new InvalidOperationException($"AutomationId not found: {id}"));

    private readonly record struct Ui(AutomationElement Element)
    {
        public string Name => (string)Element.GetCurrentPropertyValue(AutomationElement.NameProperty);
        public void Invoke()           => ((InvokePattern)Element.GetCurrentPattern(InvokePattern.Pattern)).Invoke();
        public void SetValue(string t) => ((ValuePattern)Element.GetCurrentPattern(ValuePattern.Pattern)).SetValue(t);
    }

    // The ONLY place polling lives. Test bodies never see a sleep.
    private static T WaitFor<T>(Func<T?> probe, TimeSpan timeout) where T : class
    {
        var deadline = DateTime.UtcNow + timeout;
        while (DateTime.UtcNow < deadline)
        {
            var r = probe();
            if (r != null) return r;
            Thread.Sleep(50);
        }
        throw new TimeoutException("UIA element not found within " + timeout);
    }
}
```

Zero NuGet beyond MSTest. Zero driver processes. Zero HTTP hops. `using System.Windows.Automation;` is the entire import. If the 50 ms poll ever proves insufficient, upgrade to `Automation.AddAutomationEventHandler(...)` (also in-box) for true event-based waits.

## 6a. Performance — piggyback by default, dedicated load suite only when needed

**The 2-in-1 rule.** Every functional test in §6 already exercises a code path end-to-end. When the env var `QA_PERF_CAPTURE=1` is set (default in the `perf` CI job, off locally), the same test run also emits a `perf/` folder of in-box telemetry. Functional coverage *becomes* performance coverage — if a path has a test, it has perf data. No parallel perf suite, no duplicated scenarios, no "we forgot to perf-test the refund flow" gaps.

**Piggyback records, load suite gates.** Per-test perf data is *never* asserted against absolute thresholds — that flakes on slow CI agents and encodes machine speed into your suite. Regressions are surfaced by **diffing perf artifacts across runs** (baseline vs. PR). Only the dedicated load suite (`{Project}.Tests.Perf/`) gates pass/fail, and it gates on statistical baselines across many samples — not single-run numbers.

### 6a.1 Per-layer collectors (all in-box)

| Layer | Collector started in `[AssemblyInitialize]` | Emits into `perf/` |
|---|---|---|
| `unit` | In-proc `EventPipe` session: `Microsoft-DotNETCore-SampleProfiler` + `Microsoft-Windows-DotNETRuntime` (GC + allocations + contention) | `trace.nettrace`, `counters.json` |
| `integration-api` | EventPipe (as above) + EF Core `DbCommandInterceptor` logging every SQL text + duration + row count + OpenTelemetry with **file exporter** for spans | `trace.nettrace`, `ef-queries.ndjson`, `otel.ndjson` |
| `integration-db` | SQL Server **Extended Events** session (`sql_statement_completed`, `query_post_execution_showplan`) started per `[TestInitialize]`, stopped per `[TestCleanup]` + Query Store delta snapshot | `sql.xel`, `query-store-delta.json` |
| `ui-web` | `context.Tracing.StartAsync(screenshots: true, snapshots: true)` + `page.evaluate("performance.getEntries()")` + CDP `Performance.getMetrics` + HAR export | `playwright-trace.zip`, `perf-entries.json`, `network.har` |
| `ui-wpf` / `ui-winui` / MAUI-Windows | `wpr.exe -start GeneralProfile -start CPU` around the test window + in-proc EventPipe for managed allocs | `wpr.etl`, `trace.nettrace` |
| `perf` (dedicated load) | `Microsoft.Crank` scenario + bracketed `dotnet-gcdump` (start + end) + `dotnet-counters` time series throughout the run | `crank.json`, `gcdump-start.gcdump`, `gcdump-end.gcdump`, `counters.json`, `trace.nettrace` |

`EventPipe` is the in-box .NET diagnostic pipe — `Microsoft.Diagnostics.NETCore.Client` drives it from test infrastructure so no external `dotnet-trace` process is required. ETW (`wpr.exe`) is the Windows equivalent for UI-thread and render work. None of this adds a NuGet dependency beyond `Microsoft.Diagnostics.NETCore.Client`.

### 6a.2 The artifact contract (identical across layers)

Every test — piggyback or dedicated — leaves behind the same folder shape so one parser in an AI agent handles all of them:

```
TestResults/{run}/{FullTestName}/perf/
├── manifest.json        # test name, @under-test, @layer, git sha, wall-clock start/stop, machine
├── trace.nettrace       # EventPipe: CPU samples + GC + allocs + contention
├── counters.json        # dotnet-counters delta across the test window
├── sql.xel              # integration-* only: XEvent capture for this test's window
├── ef-queries.ndjson    # integration-api only: one row per SQL, with duration + rows
├── otel.ndjson          # integration-api only: OTLP spans incl. EF Core spans
└── ui/                  # ui-* only
    ├── playwright-trace.zip
    ├── perf-entries.json
    └── network.har
```

The dedicated load suite (`{Project}.Tests.Perf/`) adds `load/crank.json` and the bracketing `gcdump-*.gcdump` files to the same shape. **Why identical shape:** "show me the regression" is the same query whether the data came from a 5 ms unit test or a 10-minute soak run — one diff algorithm, one code path in the AI agent.

### 6a.3 The piggyback hook (one file, reused by every test project)

```csharp
// TestInfrastructure/PerfCapture.cs — lives in {Project}.Tests/TestInfrastructure/
// Opt-in via env var so the local TDD loop stays fast.
[TestClass]
public static class PerfCapture
{
    private static EventPipeSession? _session;
    public static bool Enabled => Environment.GetEnvironmentVariable("QA_PERF_CAPTURE") == "1";

    [AssemblyInitialize]
    public static void Start(TestContext ctx)
    {
        if (!Enabled) return;
        var client = new DiagnosticsClient(Process.GetCurrentProcess().Id);
        var providers = new[]
        {
            new EventPipeProvider("Microsoft-DotNETCore-SampleProfiler", EventLevel.Informational),
            new EventPipeProvider("Microsoft-Windows-DotNETRuntime", EventLevel.Verbose, 0x1 | 0x80 | 0x4000080018),
        };
        _session = client.StartEventPipeSession(providers, requestRundown: true);
        _ = Task.Run(() => _session.EventStream.CopyTo(File.Create(PerfPaths.TraceFile)));
    }

    [AssemblyCleanup]
    public static void Stop() { _session?.Stop(); _session?.Dispose(); }
}
```

That's the whole piggyback machinery for `unit` and `integration-api`. Layer-specific collectors (XEvent session, Playwright tracing, `wpr`) live in small siblings (`SqlXEventCapture.cs`, `PlaywrightPerfCapture.cs`, `WprCapture.cs`) and are activated by the same env var.

### 6a.4 Example — N+1 detection from an integration-api test

```csharp
// @under-test: src/Foo.Web/Controllers/OrdersController.cs
// @area: orders   @layer: integration-api
[TestMethod, TestCategory("orders")]
public async Task Get_orders_returns_user_orders_with_customer_name()
{
    var response = await _client.GetAsync("/api/orders?userId=42");
    response.EnsureSuccessStatusCode();
    // Functional assertion — the only one that gates the test.
    Assert.IsTrue((await response.Content.ReadAsStringAsync()).Contains("Jane Doe"));
}
```

With `QA_PERF_CAPTURE=1`, this run also emits `perf/ef-queries.ndjson`. If the endpoint regressed from 1 SQL statement into a per-row `SELECT Customer WHERE Id = @p` loop, the file contains 51 rows instead of 1. The AI agent diffs the file against the baseline, spots the N+1 immediately, and maps it back via the `@under-test` header to `OrdersController.cs`. No perf assertion, no flake, no duplicated scenario.

### 6a.5 The dedicated `{Project}.Tests.Perf/` suite

This is the fourth legitimate §5.1 split. It houses **only** scenarios that functional tests cannot express:

- **Load:** target RPS against `WebApplicationFactory`-hosted app or a deployed env. Tool: `Microsoft.Crank` (github.com/dotnet/crank — the benchmarking infrastructure used by the .NET team itself for the TechEmpower runs). Emits `crank.json` with p50/p95/p99, RPS, errors.
- **Stress:** push past saturation until the first error; record the break point.
- **Soak:** sustained load for N hours with bracketed `dotnet-gcdump` before/after. Diffing the two gcdumps surfaces **retained types, counts, and GC roots** — the "undisposed objects pinned to root" detector, built from in-box tools only.
- **Micro-benchmarks** for `@perf-critical` methods: **BenchmarkDotNet** jobs, runnable under the same MSTest runner via an `[TestMethod]` that shells out to BDN and asserts against its statistical baseline.

The suite gates on statistical baselines across samples (e.g. p95 latency must not regress by >10% with p<0.05), never on single-run numbers.

### 6a.6 Which layer covers database performance

Explicitly, because the question comes up often:

- **Per-query perf** (duration, logical reads, plan, missing indexes, N+1) is covered by every `integration-api` and `integration-db` piggyback run via the EF interceptor + XEvent session. Regressions are attributed to a single test name, which maps to a single `@under-test` file. **This catches 95% of database perf issues.**
- **Contention, blocking, deadlocks, lock escalation** need concurrency — they live in the dedicated `{Project}.Tests.Perf/` load suite, which drives the same endpoints under Crank and captures wait stats from `sys.dm_os_wait_stats` deltas.

You do **not** need a separate "database performance test" layer. The piggyback collector on your integration tests already is one.

## 7. Standards

### Selectors

Web: role + accessible name → label → text → `data-testid` → CSS → XPath (last resort). Desktop: `AutomationProperties.AutomationId` is mandatory on every interactive control, format `Screen.Element`.

### Waits

Allowed: Playwright auto-waits (`Expect(...).ToBeVisibleAsync()`), Playwright `WaitForURL` / `WaitForLoadState`, a single named `WaitFor<T>` polling helper in test infrastructure, and `Automation.AddAutomationEventHandler`. Banned in test bodies: `Thread.Sleep`, `Task.Delay`, `page.waitForTimeout`. *Why:* sleeps hide race conditions and slow every run for everyone.

### Naming, tags, data

Test methods: `Subject_does_thing_under_condition`. Tags lowercase (`smoke`, `auth`, `critical`). Every test has an area tag plus a severity tag. Secrets via env vars, never committed. Generated per-test data or per-test fixtures — never hard-coded shared records that mutate.

### Fixtures / helpers / screens

Helper = function with intent (`SignInAs(user)`). Screen = small class for one window/widget, no inheritance. Create a screen only when 3+ tests share 5+ interactions on the same surface. Inline anything used once.

### Assertions

One logical assertion per test. Assert on user-visible state, not implementation details. Prefer Playwright web-first assertions (auto-retry).

### Retries

CI: `retries: 1` for UI suites. Local: `retries: 0` — force fixing flakes. A test needing >1 retry is a defect, not a setting to tune.

### CI-friendly

Runs from a clean checkout with one command: `dotnet test`. No machine-specific paths. No driver installs (UIA is in-box; Playwright installs its own browsers via `pwsh bin/Debug/net8.0/playwright.ps1 install` on first build). Parallel-safe by default.

### Perf data handling

Piggyback collection (§6a) is **off by default locally** (fast TDD loop), **on by default in the `perf` CI job** via `QA_PERF_CAPTURE=1`. Per-test perf data never fails a functional test — no `Assert.Less(elapsed, 100ms)`, no allocation-count assertions, no "expected <N SQL queries" guards inside functional test bodies. Regressions are detected by **diffing `perf/` artifacts against the baseline run of the same test** (same `@under-test`, same `@layer`) and raised as review comments or CI annotations. The only place statistical gating lives is the dedicated `{Project}.Tests.Perf/` load suite, which gates on p95/p99 deltas across many samples (e.g. `p95 must not regress by >10% with p<0.05`), never on single-run numbers. Retain the last N `perf/` folders plus anything flagged as a regression; everything else is disposable.

### Flaky-test triage

Open the trace. 90% of the time: missing/incorrect wait, unstable selector, or shared state. Fix the root cause. Never add `Sleep`. Never raise the retry count.

### Defect reproduction

Reproduce as the smallest possible test at the lowest possible layer (often API, not UI). Commit the failing test first, then the fix.

## 8. AI behaviour rules

1. **Detect project shape first** (web / WPF / WinUI / MAUI / API / mixed), then pick from §3.
2. **Default to code-first.** Convert any Given/When/Then into executable code; preserve phrasing in name/comments/`[TestCategory]`.
3. **Never introduce Appium or WinAppDriver to a new project.** Windows desktop uses `System.Windows.Automation`. Appium is allowed only for existing MAUI Android/iOS suites.
4. **Never add a second test runner** if MSTest is already present. Reject "just this once" arguments.
5. **Never add `Sleep` in a test body.** Polling lives inside one named `WaitFor` helper only.
6. **Prefer the lowest layer** that gives confidence: unit → API → UI. View-models before launching an exe.
7. **Inspect the product** for stable selectors / `AutomationId`s before writing the test.
8. **Keep examples runnable.** No pseudo-code.
9. **For perf investigations, read piggyback artifacts first.** Open `perf/ef-queries.ndjson`, `perf/trace.nettrace`, `perf/sql.xel`, or `perf/perf-entries.json` of the specific failing / regressed test before reaching for the dedicated load suite. The per-test folder already attributes the regression to one test name and one `@under-test` file — that is the cheapest possible diagnosis. Only escalate to the load suite for concurrency, saturation, or soak questions the functional tests cannot express.
10. **Never add a perf assertion that fails a functional test.** No `Assert.Less(elapsed, ...)`, no SQL-count asserts in functional bodies, no allocation-count asserts. Perf signals flow through diff-against-baseline, not pass/fail. Adding a perf assertion to a functional test is how perf suites become flaky and get disabled.
11. **Cite the artifact before proposing a perf fix.** Every perf recommendation must quote the specific `perf/` file and the row/stack/span/statement that proves the diagnosis — e.g. "`ef-queries.ndjson` shows 51 `SELECT Customer` rows where the baseline shows 1" or "`trace.nettrace` shows 83% of CPU in `JsonSerializer.Deserialize<T>` via `OrdersController.Get`". No artifact → no fix.

12. **Before running tests during development, scope the run.** Run `python test_map.py --affected HEAD~1 --json` (or the range matching your work). Read the JSON output. For shared types/interfaces/base classes, use your platform's reference-finding tool to identify transitive dependents the string-grep missed — `find_references` in VS Code, `find_usages` in JetBrains, `Go to References` in Visual Studio, or `grep` / `rg` as a fallback when no language server is available. Union the result with `TestCategory=critical`. Run only that subset. Run the full suite (`dotnet test` with no filter) only when the solution is complete.
13. **Tests that require admin elevation must be safe by default.** When writing a test that triggers UAC (e.g. `Verb = "runas"`, `Enable-WindowsOptionalFeature`, any admin PowerShell), apply all three of these — missing any one breaks the default run:
    - Tag it `[TestCategory("requires-elevation")]`.
    - Guard the test body with an env-var opt-in check that calls `Assert.Inconclusive` when the var is absent. Pattern:
      ```csharp
      private static void RequireElevationOptIn()
      {
          if (Environment.GetEnvironmentVariable("QA_ALLOW_ELEVATION") != "1")
              Assert.Inconclusive("Skipped: requires elevation. Set QA_ALLOW_ELEVATION=1 to opt in.");
      }
      ```
      Call `RequireElevationOptIn()` as the first line of every elevation test.
    - *Why both tag AND guard:* the tag lets `--filter "TestCategory!=requires-elevation"` exclude them at the runner level. The guard is the safety net — even if someone runs `dotnet test` with no filter, the test self-skips instead of popping a UAC dialog that hangs CI or surprises a developer. A test that blocks a default `dotnet test` run is worse than a missing test.

For inherited SpecFlow/Reqnroll projects or any migration (Appium → UIA, Selenium → Playwright, NUnit/xUnit → MSTest, page-objects → screens), load [`references/legacy-bdd.md`](references/legacy-bdd.md) or [`references/migrations.md`](references/migrations.md) — they exist so this file stays focused on the 95% case.

## 9. Anti-patterns (append-only)

- Installing WinAppDriver / Appium on CI when `System.Windows.Automation` covers the same tests with zero external processes.
- Mixing test runners in one repo (MSTest + xUnit + NUnit).
- Reaching for Playwright when `WebApplicationFactory<T>` + `HttpClient` would prove the same thing 10× faster.
- Adding new SpecFlow features (maintaining existing ones is fine).
- Duplicating intent across `.feature` files and step definitions.
- Brittle CSS / XPath when a role / label / `AutomationId` exists.
- `Thread.Sleep` / `waitForTimeout` / `Task.Delay` in test bodies.
- Shared mutable test state, ordered tests, test interdependence.
- Writing UI tests for things an API or view-model test would prove faster and more reliably.
- Testcontainers for SQL Server when `SqlLocalDB` already works.
- Splitting a small codebase into `.Tests.Unit` + `.Tests.Integration` + `.Tests.UI` sibling projects when one `{Project}.Tests` would cover everything. Split only when headless CI, scale, or a different target framework actually requires it.
- Sub-namespacing test files to match their folder (`Tests.Services.*`, `Tests.Provider.*`). The folder is visible in the explorer and the `@under-test` header is the authoritative link — sub-namespaces just make every test helper move into a cross-file `using` hunt.
- Writing a dedicated perf test for a scenario a functional test already covers — the piggyback collector (§6a) already measured it. Duplicating the sign-in flow in a perf suite just creates drift.
- Per-test perf assertions (`Assert.Less(elapsed, 100ms)`, `Assert.AreEqual(1, sqlCount)` inside a functional body). They encode machine speed, they flake on slow CI agents, and the standard fix — raising the threshold — hides real regressions. Use diff-against-baseline instead.
- Building a perf suite parallel to the functional suite with duplicated scenarios. The whole point of §6a is that functional tests *are* the perf scenarios; `{Project}.Tests.Perf/` exists only for concurrency, saturation, and soak.
- Using JMeter, k6, or Azure Load Testing (which wraps JMeter) for new projects when `Microsoft.Crank` is the Microsoft-owned, JSON-emitting, .NET-team-maintained alternative. JMeter remains supported only for inherited `bw-jmeter` suites.
- Tests that trigger UAC elevation (`Verb = "runas"`, `Enable-WindowsOptionalFeature`, admin PowerShell) without being tagged `requires-elevation`. A developer on a locked-down VM or a headless CI agent cannot approve a UAC prompt; the test hangs or crashes the run. Tag them and exclude from CI via `TestCategory!=requires-elevation`.
- Adding Application Insights / Datadog / New Relic as a *test* dependency for perf data collection. They're fine in production; in tests they require a backend service and emit closed artifacts an AI agent cannot parse offline. Use OpenTelemetry with the file exporter instead.

## 10. Trusted sources

- **System.Windows.Automation (in-box UIA):** https://learn.microsoft.com/dotnet/framework/ui-automation/
- **MSTest:** https://learn.microsoft.com/dotnet/core/testing/unit-testing-with-mstest
- **`WebApplicationFactory<T>`:** https://learn.microsoft.com/aspnet/core/test/integration-tests
- **Playwright for .NET:** https://playwright.dev/dotnet/
- **Playwright MSTest integration:** https://playwright.dev/dotnet/docs/test-runners#mstest
- **SqlLocalDB:** https://learn.microsoft.com/sql/database-engine/configure-windows/sql-server-express-localdb
- **EventPipe / `dotnet-trace`:** https://learn.microsoft.com/dotnet/core/diagnostics/dotnet-trace
- **`dotnet-gcdump`:** https://learn.microsoft.com/dotnet/core/diagnostics/dotnet-gcdump
- **`dotnet-counters`:** https://learn.microsoft.com/dotnet/core/diagnostics/dotnet-counters
- **`Microsoft.Diagnostics.NETCore.Client`:** https://learn.microsoft.com/dotnet/core/diagnostics/diagnostics-client-library
- **OpenTelemetry .NET:** https://opentelemetry.io/docs/languages/net/
- **SQL Server Extended Events:** https://learn.microsoft.com/sql/relational-databases/extended-events/extended-events
- **Windows Performance Recorder (`wpr.exe`):** https://learn.microsoft.com/windows-hardware/test/wpt/windows-performance-recorder
- **`Microsoft.Crank`:** https://github.com/dotnet/crank
- **BenchmarkDotNet:** https://benchmarkdotnet.org/

## 11. References

Load these only when the user's request is about that specific topic — each is relevant maybe 1 call in 20.

- **Onboarding / training wizard:** [`references/onboarding-qa.md`](references/onboarding-qa.md)
- **Environment / tool installation:** [`references/setup-environment.md`](references/setup-environment.md)
- **Inherited SpecFlow / Reqnroll projects:** [`references/legacy-bdd.md`](references/legacy-bdd.md)
- **Migrations (Appium→UIA, Selenium→Playwright, NUnit/xUnit→MSTest, page-objects→screens):** [`references/migrations.md`](references/migrations.md)
- **Performance deep dive (piggyback collectors, Crank scenarios, gcdump diffing, XEvent templates):** [`references/performance.md`](references/performance.md)
- **Prerequisite checks (cross-platform Python):** [`scripts/ensure_prereqs.py`](scripts/ensure_prereqs.py) — `python ensure_prereqs.py` (all), `python ensure_prereqs.py playwright`, `python ensure_prereqs.py jmeter`, `python ensure_prereqs.py perf`
- **Playwright demo scaffold:** [`scripts/restore_playwright_demo.py`](scripts/restore_playwright_demo.py)

## 12. Meta — rules for AIs editing this skill later

1. **Size budget.** Keep SKILL.md under ~560 lines. Push anything deeper into `references/`. *Why:* long skill files increase cognitive load for every single call.
2. **Every rule has a why-line.** A rule without a reason becomes dogma the next AI will misapply.
3. **Every example runnable.** No pseudo-code.
4. **No duplication.** Merge overlapping sections; cross-link instead.
5. **The two-tool rule (§2) is load-bearing.** Adding a third tool requires removing something.
6. **Discoverability invariants (§5) are load-bearing.** Don't change file mapping or the `@under-test` header without updating migration notes.
7. **§5.1 "single project by default" is load-bearing.** The three-criterion split list (headless CI, scale, different TFM) is the only reason to recommend multiple test projects. Do not soften this — a previous version of this skill pushed a three-project split as default and it produced test projects more complex than the app under test.
8. **Anti-patterns (§9) is append-only** unless an entry is provably wrong.
9. **Prefer subtraction.** If you can delete a paragraph and the skill is still complete, delete it. Token cost is real.
10. **Third-party skepticism.** Any proposed new dependency must survive: "does an in-box or Microsoft-owned alternative do this?" If yes, reject.
11. **Test against a real prompt** before committing: mentally run *"add a sign-in test for `src/Foo.Web/Pages/SignIn.razor`"* and confirm the path you produce matches §5.2.
12. **§6a piggyback-first is load-bearing.** The 2-in-1 rule (perf data as a byproduct of functional tests) is the whole reason §6a exists. Do not weaken it by recommending a parallel perf suite that duplicates functional scenarios, and do not move piggyback collectors into `{Project}.Tests.Perf/` — they belong next to the functional tests whose coverage they inherit. `{Project}.Tests.Perf/` is for concurrency, saturation, and soak only.

### How to know the skill is working

- New tests land at the path §5.2 predicts on the first try.
- `rg "@under-test:" {Project}.Tests/` returns a complete coverage map.
- The repo has exactly **one** test runner (MSTest) and **two** tools (MSTest, Playwright) — no WinAppDriver, no Appium (except `Tests/UI.Mobile/`), no new SpecFlow, no NUnit, no xUnit.
- **The test project is no more fractured than the product project.** One `{Project}.Tests` by default; a second `{Project}.Tests.UI` only if headless CI or another §5.1 constraint forces it.
- Flake fixes land as wait/selector changes, never `Sleep` or retry-count bumps.
- A reviewer reads any test top-to-bottom in under 30 seconds.
- Running the `perf` CI job (`QA_PERF_CAPTURE=1`) produces a `perf/` folder next to every functional test — unit, integration-api, integration-db, ui-web, ui-wpf — and the dedicated `{Project}.Tests.Perf/` suite exists only for concurrency, saturation, and soak. Perf regressions are reported as diff-against-baseline, never as failing functional assertions.

## 13. Related skills

- Performance testing (legacy / inherited JMeter suites only — new projects use §6a): [`bw-jmeter`](../bw-jmeter/SKILL.md)
