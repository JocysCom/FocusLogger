# QA Onboarding Guide (with AI) — QA Tester

Use this document when a user asks for training/onboarding on how to use the **qa-tester** skill in this repository.

## Single source of truth

This guide is intentionally lightweight.

- For the canonical test layout standard, see [`SKILL.md`](.ai/skills/qa-tester/SKILL.md:1).
- For machine setup/prerequisites, see [`setup-environment.md`](.ai/skills/qa-tester/references/setup-environment.md:1).

## Goals

- Explain how testing is organised in this repo.
- Show how to run tests with minimal friction.
- Teach the user how to collaborate with the AI (what they should ask for, what the AI will do).

Keep sentences short. Prefer numbered steps.

---

## 0) What you need open (UI)

1) Open this repository in **VS Code**.
2) Open the built-in **Terminal**.
3) Open the AI chat panel (the “console” where you chat with the AI).

When the AI runs commands, you should see them in the terminal.

---

## 1) Where things are

### Test folders

The standard layout and folder conventions are defined in:

- [`SKILL.md`](.ai/skills/qa-tester/SKILL.md:1)

### “Sites/apps” in this repo

The AI should discover site/app names by reading:

- [`.ai/repository-analysis.instructions.md`](.ai/repository-analysis.instructions.md:1)

Then the AI must present:

- a short list of site/app names
- where each app lives in the repo

---

## 2) Built-in guidance to use (in order)

When onboarding, the AI should:

1) Read [`SKILL.md`](.ai/skills/qa-tester/SKILL.md:1)
2) Read [`bw-jmeter SKILL.md`](.ai/skills/bw-jmeter/SKILL.md:1) (only if performance testing is in scope)
3) Read [`.ai/repository-analysis.instructions.md`](.ai/repository-analysis.instructions.md:1) to list sites/apps
4) Only if setup is needed, read [`setup-environment.md`](.ai/skills/qa-tester/references/setup-environment.md:1)

---

## 3) Start-here checklist (first 15 minutes)

### Step A — Run a UI test in Playwright Test UI

If the `Tests/` folder does not exist yet, restore the demo Playwright scaffold first:

- [`Restore-PlaywrightDemo.ps1`](.ai/skills/qa-tester/scripts/Restore-PlaywrightDemo.ps1:1)

Then continue.

1) In the terminal, go to:

```powershell
cd Tests/UI.Playwright
```

2) Install dependencies (first time only):

```powershell
npm install
```

3) Install browsers (first time only):

```powershell
npx playwright install
```

4) Open Playwright Test UI:

```powershell
npx playwright test --ui --project=chromium
```

If you want to run the demo test (it is excluded by default), run:

```powershell
npx playwright test --grep @demo
```

What you should see:

- A Playwright UI window.
- A list of tests on the left.
- Test output/steps/trace links in the UI.

### Step B — View the HTML report

Run:

```powershell
cd Tests/UI.Playwright
npx playwright test --reporter=html
npx playwright show-report
```

### Step C — Create one small new test

Create a minimal “smoke” test first. Keep it tiny.

Suggested starter target:

- `https://example.com/` (safe demo domain)

A demo test may already exist at:

- [`Tests/UI.Playwright/Sites/Demo/example.spec.ts`](Tests/UI.Playwright/Sites/Demo/example.spec.ts:1)

The AI should:

- tell you the exact file path it will create/edit
- explain what the test will assert (in plain English)
- run the test in UI mode so you can watch

---

## 4) How to ask the AI for a new test (only 3 questions)

When the user asks for a new UI test, the AI should ask only:

1) Which site/app?
2) Which environment URL (CI / test / prod)?
3) What page and what action should the test verify?

If the user cannot answer, offer 2–3 common options (short).

---

## 5) Collaboration rules (AI + user)

### When proposing changes, the AI must always say:

- The exact file path it will edit
- The assertions it will add (what is being verified)
- Copy/paste commands only (no long alternatives)

### How the user can participate

The user can:

- watch tests run in **Playwright UI mode**
- re-run a single test quickly
- report what they see (screenshots/logs) if something fails

The AI can:

- edit tests under `Tests/`
- run commands in the terminal
- guide you step-by-step

---

## 6) When to use Playwright UI vs CLI (simple)

Use **UI mode** when:

- writing a new test
- debugging a failure
- you want to watch the browser

Command:

```powershell
cd Tests/UI.Playwright
npx playwright test --ui --project=chromium
```

Use **CLI** when:

- running a quick batch
- running in CI

Command:

```powershell
cd Tests/UI.Playwright
npx playwright test --project=chromium
```

---

## 7) Beginner-friendly videos (2–3)

- Playwright: UI mode and debugging: https://playwright.dev/docs/test-ui-mode
- Playwright: getting started with tests: https://playwright.dev/docs/intro
- Testing concepts (E2E vs unit): https://martinfowler.com/bliki/TestPyramid.html

---

## 8) Onboarding script (AI prompt template)

Use this prompt when the user asks for onboarding:

> How to act as QA onboarding guide for this repository.
> 
> User is new to the repo and new to working with AI.
> Please explain everything in simple steps and short sentences.
> 
> 1) First, tell me “Where things are”:
>   - Which websites/apps exist in this repo (site names).
>   - Where UI tests and performance tests should live.
>   - Which commands I use to run tests.
> 
> 2) Use the repo’s built-in guidance:
>   - Read `.ai/skills/qa-tester/SKILL.md` and `.ai/skills/bw-jmeter/SKILL.md`.
>   - Use `.ai/repository-analysis.instructions.md` to list the available sites/apps.
>   - Only if setup is needed, read `.ai/skills/qa-tester/references/setup-environment.md`.
> 
> 3) Then give me a “Start here” checklist:
>   - Step A: open Playwright Test UI and run an existing test (show the exact command).
>   - Step B: view the HTML report.
>   - Step C: create one small new test.
> 
> 4) When I ask for a new test, ask me only these questions:
>   - Which site/app?
>   - Which environment URL (CI / test / prod)?
>   - What page and what action should the test verify?
> 
> 5) When you propose changes:
>   - Tell me the exact file path you will edit.
>   - Tell me what the test will assert.
>   - Give copy/paste commands only.
> 
> Start now by listing the sites/apps you found and the exact command to open Playwright Test UI.
