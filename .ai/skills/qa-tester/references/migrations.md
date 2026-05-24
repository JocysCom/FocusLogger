# Migration playbooks

Load this reference only when the user is consolidating an existing test suite toward the two-tool stack described in `SKILL.md` §2. Each playbook is a minimal, one-file-at-a-time sequence — never a big-bang rewrite.

## Appium / WinAppDriver → `System.Windows.Automation`

**Goal:** remove the driver binary, the Selenium wire protocol, and the extra install step. UIA is in-box, so there's nothing to install.

1. Add `using System.Windows.Automation;` — no NuGet, it ships with .NET.
2. Replace `WindowsDriver<T>` setup with `Process.Start(exe)` + `AutomationElement.FromHandle(proc.MainWindowHandle)`.
3. Replace `FindElementByAccessibilityId("X")` with `root.FindFirst(TreeScope.Descendants, new PropertyCondition(AutomationElement.AutomationIdProperty, "X"))`.
4. Replace `.Click()` with `((InvokePattern)el.GetCurrentPattern(InvokePattern.Pattern)).Invoke()`.
5. Replace `.SendKeys(...)` with `((ValuePattern)el.GetCurrentPattern(ValuePattern.Pattern)).SetValue(...)`.
6. Replace `.Selected` / `.Displayed` checks with `el.GetCurrentPropertyValue(AutomationElement.IsEnabledProperty)` etc.
7. Delete `WinAppDriver.exe` install steps from CI and remove the `Appium.WebDriver` / `Selenium.*` NuGet packages.
8. Move any polling into a single `WaitFor<T>` helper in test infrastructure (see `SKILL.md` §6.4 for the canonical form).
9. Delete retry-count bumps that existed because Appium was flaky — UIA is in-process and deterministic.

## Selenium → Playwright

**Goal:** get auto-waiting and role-based locators for free, drop the driver-download ceremony.

1. Replace the WebDriver fixture with the Playwright `PageTest` base class.
2. Replace `By.CssSelector` / `By.XPath` with role/label/test-id locators (`GetByRole`, `GetByLabel`, `GetByTestId`).
3. Delete every `Thread.Sleep` and `WebDriverWait` ceremony — Playwright assertions auto-retry.
4. Replace page-object inheritance trees with small `*Screen` helper classes (see `SKILL.md` §7).
5. Delete the `Selenium.*` NuGet packages and any driver-download scripts.

## NUnit / xUnit → MSTest (Microsoft alignment)

**Goal:** one runner per repo. Only do this when the surrounding codebase is Microsoft-aligned and a dual-runner setup is creating friction.

1. Add the MSTest packages alongside the old runner so both work during migration.
2. Convert one test class at a time:
   - `[Test]` / `[Fact]` → `[TestMethod]`
   - `[SetUp]` / `[TestInitialize]` / constructor → `[TestInitialize]`
   - `[TearDown]` / `IDisposable.Dispose` → `[TestCleanup]`
   - `[TestCase]` / `[InlineData]` → `[DataTestMethod]` + `[DataRow]`
   - `[Category]` / `[Trait]` → `[TestCategory]`
3. Verify TRX parity between the old and new runs before removing the old runner.
4. Remove the old runner's NuGet packages once the last class migrates.

## Over-engineered page objects → lean screens

**Goal:** get back under the 30-second-readability bar.

1. Identify the 5–10 interactions actually used per page. Delete the rest.
2. Extract them as intent-named methods on a small `*Screen` class (e.g. `SignInScreen.SignInAsync(user)`).
3. Delete inheritance, base classes, generic wrappers, reflection-based element caches.
4. Inline anything used only once.

The rule of thumb: a screen only exists if 3+ tests share 5+ interactions on the same surface. Anything below that threshold belongs inline in the test.

## Fragile desktop selectors → `AutomationId`-based

**Goal:** make the tests stop breaking whenever a designer edits the XAML.

1. Audit the XAML. Add `AutomationProperties.AutomationId` to every interactive control, format `Screen.Element` (e.g. `SignIn.Submit`, `Dashboard.Title`).
2. Replace name / XPath lookups in tests with `PropertyCondition(AutomationElement.AutomationIdProperty, ...)`.
3. Delete retry loops that existed only to work around selector flakiness.
4. If a control legitimately can't have an `AutomationId` (usually it can), raise it as a product-side fix — don't paper over it in the test.

## Testcontainers (SQL Server) → `SqlLocalDB`

**Goal:** remove the Docker dependency from CI.

1. `sqllocaldb create TestDb` in your test `[AssemblyInitialize]`.
2. Connection string: `Server=(localdb)\\MSSQLLocalDB;Database=TestDb;Integrated Security=true`.
3. Reset strategy: run your migration scripts in `[TestInitialize]` against a fresh `DROP DATABASE` / `CREATE DATABASE`, or wrap each test in a transaction you roll back in `[TestCleanup]`.
4. Remove the `Testcontainers.*` NuGet packages and the Docker install step from CI.

Testcontainers still makes sense for non-SQL-Server engines (Postgres, Redis, RabbitMQ) where no in-box alternative exists — keep it for those, drop it for SQL Server.
