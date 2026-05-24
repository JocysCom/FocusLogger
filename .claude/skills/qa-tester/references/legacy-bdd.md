# Inherited SpecFlow / Reqnroll projects

Load this reference only when the user's repo already has SpecFlow or Reqnroll and you need to maintain, extend minimally, or migrate it. For greenfield work always use the code-first approach in `SKILL.md` §4.

## Position

| Framework | Status | What to do |
|---|---|---|
| **SpecFlow** | Abandoned upstream. | Inherited tests keep working. Never add *new* SpecFlow features. When touching an existing feature, first option is to upgrade the whole project to Reqnroll; second option is to migrate that one scenario to code-first MSTest. |
| **Reqnroll** | Active successor to SpecFlow. | Supported for inherited projects. Keep bindings thin — one or two lines — with all logic in plain C# helpers. Do not expand Gherkin coverage. Do not introduce Reqnroll to a greenfield project. |

*Why this stance:* BDD tooling forces a second file, step bindings, regex maintenance, and a fragile indirection layer, for zero clarity win over a well-named `[TestMethod]`. The only legitimate reason to keep it running is that the project already has hundreds of scenarios and rewriting them all at once has no business value.

## Thin-binding pattern (Reqnroll)

Bindings should be one or two lines that delegate to a plain C# class. The C# class — here `SignInScreen` — is also usable from normal MSTest tests with no Reqnroll involvement, which is the migration bridge.

```csharp
[Binding]
public class SignInSteps
{
    private readonly SignInScreen _screen;
    public SignInSteps(SignInScreen screen) => _screen = screen;

    [When(@"the user signs in as ""(.*)""")]
    public Task WhenTheUserSignsInAs(string email) => _screen.SignInAsync(email);

    [Then(@"the dashboard is visible")]
    public Task ThenDashboardVisible() => _screen.AssertDashboardVisibleAsync();
}
```

## Project layout (compatibility mode)

```
Tests/UI/{Project}.Tests.UI.Reqnroll/   # do not grow this
  Features/
  Steps/                                # thin bindings only
  # real logic lives in Tests/UI/{Project}.Tests.UI/Screens/*
```

Bindings that aren't thin are a code smell — push the logic into a screen class in the sibling `{Project}.Tests.UI` project so it's reusable from plain MSTest tests during migration.

## Migration: SpecFlow → Reqnroll

Use this when you've inherited SpecFlow and need to get it building on modern .NET. Goal is survival, not growth.

1. Replace every `SpecFlow.*` NuGet package with the `Reqnroll.*` equivalent.
2. Update namespaces: `TechTalk.SpecFlow` → `Reqnroll`.
3. Rebuild; fix binding signatures wherever the compiler points.
4. Run the full suite; fix anything that broke on a behavioural difference between SpecFlow and Reqnroll.
5. **Do not add new features during this migration.** Lock the scope to "build + test pass" so the rollback is clean.

## Migration: Reqnroll → code-first MSTest

Use this when the user wants to retire the feature-file layer over time. One scenario at a time, no big bang.

1. Pick one feature file. For each scenario, create one `[TestMethod]` whose name is the scenario title in snake case.
2. Move binding bodies into the corresponding screen/helper class (they're already thin if §"Thin-binding pattern" was followed).
3. Tag the new test with the feature name as `[TestCategory]`.
4. Delete the scenario from the `.feature` file once the new test passes in CI.
5. When the `.feature` file is empty, delete it. Repeat for the next file.

The screen classes make this a pure cut-and-paste job: the production behaviour is already in plain C#, only the Gherkin wrapper goes away.

## "But stakeholders need to read it"

This is the only serious reason anyone keeps BDD. Replace it with a **generated English-summary report** lifted from `[Description]` + `[TestCategory]` on each `[TestMethod]`, or from Playwright's `test.step()` calls. A ~100-line post-processor over the MSTest TRX or Playwright JSON produces:

```
### Customer can place an order   [orders, critical]
- Given a signed-in customer with an empty cart
- When they add a product and check out
- Then an order confirmation is shown
Result: PASS (3.2s)
```

…which is what stakeholders actually want — and it avoids every file-indirection cost of Gherkin.
