# Setup Testing Environment (Windows) - QA Tester

Use this only when the user asks to:
- install prerequisites
- create the standard [`Tests/`](Tests/:1) structure
- bootstrap Playwright/JMeter tooling

## Create folder structure

Create the standard layout:

```text
Tests/
  UI.Playwright/
    Shared/
    Sites/
  Performance.JMeter/
    Shared/
    Sites/
  Unit.DotNet/
```

Notes:
- Only create folders when the user requests it.
- Keep existing test roots until a deliberate migration is planned.

## Install prerequisites (trusted sources)

### Check prerequisites (recommended)

Run the prerequisite checker(s) first to see what is already installed:

- Playwright prerequisites:
  - [`.ai/skills/qa-tester/scripts/Ensure-PlaywrightPrerequisites.ps1`](.ai/skills/qa-tester/scripts/Ensure-PlaywrightPrerequisites.ps1:1)
- JMeter prerequisites:
  - [`.ai/skills/qa-tester/scripts/Ensure-JMeterPrerequisites.ps1`](.ai/skills/qa-tester/scripts/Ensure-JMeterPrerequisites.ps1:1)

### Vendor installs (trusted sources)

- Microsoft Edge (Chromium): https://www.microsoft.com/edge
- .NET SDK (8.x): https://dotnet.microsoft.com/download
- Node.js (LTS): https://nodejs.org/

### Optional (recommended): Playwright VS Code extension

If the user is running VS Code, recommend installing the official Playwright extension for a smoother authoring/debugging loop (run tests, view trace, inspect output inside the editor):

- https://github.com/microsoft/playwright-vscode

## Install Playwright (UI tests)

Note: Playwright itself is **project-local** (installed under the repo’s `Tests/UI.Playwright` folder). Machine prerequisites are checked by:

- [`.ai/skills/qa-tester/scripts/Ensure-PlaywrightPrerequisites.ps1`](.ai/skills/qa-tester/scripts/Ensure-PlaywrightPrerequisites.ps1:1)

Playwright Test UI is part of Playwright Test (`@playwright/test`).

- Install dependencies (example folder; adjust to your chosen test root):

```bash
cd Tests/UI.Playwright
npm install
```

- Install browsers:

```bash
cd Tests/UI.Playwright
npx playwright install
```

- Ensure Edge channel is available:

```bash
cd Tests/UI.Playwright
npx playwright install msedge
```

- Run with Playwright Test UI:

```bash
cd Tests/UI.Playwright
npx playwright test --ui --project=chromium
```

## Install Apache JMeter (performance tests)

Use the dedicated skill for details:

- [`bw-jmeter`](.ai/skills/bw-jmeter/SKILL.md:1)

Key points:
- JMeter official download: https://jmeter.apache.org/download_jmeter.cgi
- Java runtime: prefer Microsoft Build of OpenJDK: https://learn.microsoft.com/java/openjdk/
