# Project / Namespace / Folder / Install Patterns

> Scope: build-time and install-time naming — **project name, project file, .NET namespace, on-disk solution folder, install paths under `%ProgramFiles%` and `%ProgramData%`, web roots, and the project-type → server-suffix mapping that decides which network tier hosts the binary**. Companion to [`network_patterns.md`](network_patterns.md), which owns the runtime addresses (server name, IP, DNS, port) those binaries get installed onto.
>
> **The spine here is the project's full name** (`{Company}.{Solution}.{Feature}.{Project}`). From it, every other artifact (project filename, namespace, folder, install path, server suffix) is a deterministic transform.

## 1. Stack signal

[`detect_stack.py`](../scripts/detect_stack.py) flags this reference when ANY of these hold:

| Evidence | Why it fires |
| --- | --- |
| `.sln` / `.slnx` / `.slnf` whose project files follow the `{Company}.{Solution}.{Feature}.{Project}.{ext}` shape | Project naming convention is in active use |
| Folder layout matches `{Company}\{Solution}\{Feature}\{Project}\` | On-disk spine is in use |
| Repo `.ai/solution-patterns.instructions.md` declares a `## Project patterns` block | Per-project explicit opt-in |
| Existing setup project / MSI / `Inno Setup` / `WiX` script writes to `%ProgramFiles%\{Company}\` | Install-path convention is in use |

Loaded **in addition** to the code-side stack references (Razor, WPF, etc.) — they answer "what is the file's role?", this file answers "what should the file be called and where does the binary land?".

## 2. The project naming spine

```text
{Company} {Solution} {Feature} {Project}        ← Project name (display)
{Company}.{Solution}.{Feature}.{Project}        ← Namespace + project file stem
{Company}\{Solution}\{Feature}\{Project}        ← Folder path
```

| Token | Meaning | Source |
| --- | --- | --- |
| `{Company}` | Org / company short code (3+ letters, PascalCase) | `.instructions.md` `## Project patterns / Company` |
| `{Solution}` | Top-level solution name | declared once per repo |
| `{Feature}` | Functional grouping inside the solution (e.g. `Messenger`, `Reports`, `Payments`). Empty if the solution has no feature tier | `.instructions.md` |
| `{Project}` | The artifact's role suffix (see §6) | one of the canonical suffixes |

Where `{Product}` (used in install paths, §4) is shorthand for `{Solution}\{Feature}\{Project}`.

## 3. Project file / namespace / folder pattern

| Object | Pattern | Example |
| --- | --- | --- |
| Project name (display) | `{Company} {Solution} {Feature} {Project}` | `Acme Order Messenger Server` |
| Project file | `{Company}.{Solution}.{Feature}.{Project}.{ext}` | `Acme.Order.Messenger.Server.csproj` |
| Default namespace | `{Company}.{Solution}.{Feature}.{Project}` | `Acme.Order.Messenger.Server` |
| Solution folder (source) | `{RepoRoot}\{Company}\{Solution}\{Feature}\{Project}\` | `C:\Projects\Acme\Order\Messenger\Server\` |
| Assembly name | matches namespace | `Acme.Order.Messenger.Server.dll` |

A project whose `AssemblyName` / `RootNamespace` / file name do not all agree triggers `name-mismatch` (§7). A project nested in a folder that does not mirror its namespace triggers `folder-mismatch`.

## 4. Install paths (per project type)

The same `{Product} = {Solution}\{Feature}\{Project}` token feeds the deployment locations:

| Resource | Pattern | Notes |
| --- | --- | --- |
| Program path | `%ProgramFiles%\{Company}\{Product}` | Console / Windows Service / library |
| Per-user app | `%ProgramFiles%\{Company}\{Product}\{Version}` | WinApp (RDS-hosted) — version-suffixed to allow side-by-side |
| Program data | `%ProgramData%\{Company}\{Product}` | Writable runtime data |
| Program logs | `%ProgramData%\{Company}\{Product}\Logs` | Always under ProgramData, never ProgramFiles |
| Web root | `C:\inetpub\www.{Company}.{Tld}\{Product}` | IIS sites; `{Tld}` from `## Network patterns / Domain` |
| Cloud (Azure App Service) | `D:\home\site\wwwroot\{Product}` (read-only) + `D:\home\data\{Product}` (writable) | When deployed to App Service |
| Cloud (container) | `/app` and `/var/lib/{company-lower}/{product-lower}` | Linux containers |

Hand-edits to `%ProgramFiles%` paths trigger `install-path-mismatch`. Logs anywhere other than `%ProgramData%\{Company}\{Product}\Logs` trigger the same — keep diagnostics on the writable side.

## 5. Project-type → Server-suffix mapping (the bridge to network_patterns.md)

This table decides which network tier (and therefore which server prefix) hosts each project type. It is the join column between this reference and [`network_patterns.md`](network_patterns.md).

| Project type | Examples | Server tier (legacy) | Azure CAF equivalent |
| --- | --- | --- | --- |
| Database / SQL | `*.sqlproj`, `*.dacpac` | `DAT` (cluster) | `sql`, `mysql`, `psql`, `cosmos` |
| Console / Windows Service / `LibService` | `Server`, `Service` projects | `SVC` (cluster) | `vm`, `app`, `func`, `aks` |
| WinApp / WPF / WinForms / WinUI | `Client`, `Manager` projects | `RDS` (session host) | `avd` (Virtual Desktop), `vm` |
| WebApp / WebService / WebSite | `Web`, `API` projects | `WEB` (load-balanced) | `app` (App Service), `func`, `agw`+`afd` |
| Library (no host) | `Engine`, `Controls` | n/a (consumed by other projects) | n/a |
| Tester / smoke harness | `Tester` | dev workstation only | n/a |

A project whose suffix says `Server` (Windows-Service-hosted) but is deployed to a `WEB` machine triggers `tier-mismatch` — the binary belongs on the SVC tier or the suffix is wrong.

## 6. Project-suffix vocabulary (canonical — append-only)

Keep the suffix set small and predictable. Each suffix has a fixed semantic so a reader can predict the project's role from its name alone — the same expectation invariant that drives the rest of `solution-patterns`.

| Suffix | Type | Description |
| --- | --- | --- |
| `Engine` | Library | Shared core / domain types — the kernel that other projects consume |
| `Controls` | Library | Shared UI controls (WPF/WinUI/WinForms) |
| `Service` | Library | Hostable service implementation — separate from the hosting executable |
| `Server` | Console / WinService | The hosting executable for one or more `Service` libraries |
| `Client` | WinApp / WebApp | End-user UI |
| `Manager` | WinApp / WebApp | Admin / management UI for the Server + Clients |
| `Tester` | WinApp / Console | Developer-facing harness for exercising other projects (not the test project — that's `{Project}.Tests`, see qa-tester) |
| `API` | WebService | IIS-hosted REST/SOAP service |
| `Tests` | Test project | qa-tester §5.2 mirror — `{Project}.Tests` |

A project that needs a role outside this set must declare a new suffix in `.instructions.md` with a one-line definition. Inventing suffixes ad-hoc triggers `off-convention`.

## 7. Cloud-friendly alternative form (Azure CAF aligned)

For projects that target Azure (or whose binaries are installed into containers / App Service / Functions), a lowercase dash-separated form is preferred because it matches Azure resource-type abbreviations and the conventions Azure CLI tooling already enforces.

```text
{resource-type}-{workload}-{env}-{region}-{instance}
```

This applies to cloud **resource names** (App Service, Function App, Storage Account); the **project file name** and **namespace** stay in the PascalCase dotted form (§3) because .NET tooling expects that. Treat the cloud form as an additional output, not a replacement.

| Concept | Legacy | Azure CAF | Notes |
| --- | --- | --- | --- |
| Solution code | `Acme.Order` (PascalCase, dotted) | `acme-order` (lowercase, dashed) | Both are derivations of `{Company}.{Solution}` |
| Feature code | `Messenger` | `msg` (3-letter abbreviation) | Declare per-feature short codes in `.instructions.md` |
| Project role | `Server` / `Client` / `API` | `vm` / `app` / `func` / `web` | See §5 mapping |
| Environment | `LIVE` (display) / `L` (server name) | `prod` (or `prd`) | Aliases listed in [`network_patterns.md`](network_patterns.md) §8.3 |

**Example** — the on-prem and Azure forms of the same artifact:

```text
Project file:    Acme.Order.Messenger.Server.csproj
Namespace:       Acme.Order.Messenger.Server
Legacy host:     COM-L-SVC01 (Windows Service running on the SVC cluster, LIVE)
Azure host:      app-acme-order-msg-prod-uks-001 (App Service in UK South)
```

Pick one cloud-naming convention per repo (or mode) and declare it; mixing styles across resource groups produces `name-mismatch` rows that mask real defects.

## 8. Deviation codes (project-side, additive to SKILL.md §5)

| Code | Meaning | Action |
| --- | --- | --- |
| `name-mismatch` | Project file name, `AssemblyName`, `RootNamespace`, or display name disagree with `{Company}.{Solution}.{Feature}.{Project}` | Pick the canonical form (per `.instructions.md`) and align the rest. The smaller-diff side usually wins |
| `folder-mismatch` | Project lives in a folder that does not mirror its namespace | Move the project, not the namespace — keeping namespace stable preserves callers |
| `install-path-mismatch` | Installed binary lands outside `%ProgramFiles%\{Company}\{Product}\…` (or its writable counterpart for data/logs) | Amend the setup project / MSI; declare a per-repo override only if forced by a third-party installer |
| `tier-mismatch` | Project's role suffix implies one tier (per §5) but it is deployed to another | Move the deployment OR rename the project — whichever is the smaller, less-disruptive change |
| `suffix-undeclared` | Project uses a role suffix not in §6 and not declared in `.instructions.md` | Add the suffix to `.instructions.md` with a one-line definition, or rename the project to a canonical suffix |

The general SKILL.md `off-convention` and `none` codes also apply.

## 9. Anti-patterns

- **Renaming `RootNamespace` away from the project file name** — they must agree. Drift produces compile-time pain when types are referenced by FQN in another project.
- **Putting logs under `%ProgramFiles%`** — that path is read-only on locked-down machines and roams oddly with versioned installs. Logs always under `%ProgramData%\{Company}\{Product}\Logs`.
- **Inventing one-off suffixes** (`Stuff`, `Helpers`, `Utils`, `Common`) — these tell the reader nothing about role. Use `Engine` for shared core, `Controls` for shared UI, or split by concern.
- **Encoding the environment in the project name** (`Acme.Messenger.Server.UAT.csproj`) — environment is a deployment-time concern, not a build-time one. The same artifact gets deployed to LIVE, UAT, DEV by config, never by separate projects.
- **Encoding the version in the namespace** (`Acme.Messenger.V2`) — namespaces are forever; versions belong in `AssemblyVersion` / package version. Side-by-side deployment goes in the install path (§4), not in the type identity.
- **Mixing dotted and dashed forms in cross-references** — within one repo, the Azure CAF dashed form appears only in cloud-resource names; .NET artifacts stay dotted. Mixing in the same line of config is the surest way to confuse both humans and `name-mismatch` detection.

## 10. `.instructions.md` integration

Add a `## Project patterns` block:

```markdown
## Project patterns

- **Company:** `Acme`
- **Solution:** `Order`
- **Has feature tier:** yes (e.g. `Messenger`, `Reports`, `Payments`)
- **Repo root:** `C:\Projects\Acme\Order\` (mirrors the namespace)
- **Tld for web roots:** `co.uk`
- **Cloud-naming form:** `dual` — legacy on-prem hosts AND Azure CAF resource names, both declared
- **Cloud feature codes:** `messenger=msg`, `reports=rpt`, `payments=pay`
- **Custom project suffixes:** none (default §6 vocabulary applies)

### Overrides
- The historical `Common` library is grandfathered as `Acme.Order.Common` instead of being split into `Engine`/`Controls`. New shared libraries follow §6.
```

The block is the contract the deviation report compares against — drift between this block and the actual project layout is a defect, not a tolerable variation.
