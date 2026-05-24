# Network / Deployment Patterns

> Scope: deployment-time addressing artifacts — **server names, IP addresses, DNS hostnames, TCP/UDP ports, cluster identifiers, environment codes**. Same "predict before you read" principle as the rest of `solution-patterns`, applied to runtime addresses instead of source paths.
>
> The deterministic spine is the **fully-qualified server name**. Once it is known, IP, DNS, ports, cluster membership, and environment are all derivable string transforms — exactly like a code file path implies its route, breadcrumb, and test path.

## 1. Stack signal

[`detect_stack.py`](../scripts/detect_stack.py) flags this reference when ANY of these hold:

| Evidence | Why it fires |
| --- | --- |
| Folder `Architecture/` exists at solution root with `*.htm` / `*.md` containing `LIVE`, `UAT`, `DEV` *and* `LAN`, `HBN`, `WAN` (or the cluster codes `DAT`, `SVC`, `WEB`) | Project documents a multi-environment cluster topology and benefits from a deviation report against the declared pattern |
| Repo `.ai/solution-patterns.instructions.md` declares `## Network patterns` block | Per-project explicit opt-in |
| `hosts` file or `*.hosts` / `*.dns` artifact checked into the repo | Project owns network identity, not just code |
| IIS `applicationHost.config`, Bicep `*.bicep`, Terraform `*.tf`, or PowerShell DSC declares servers named with the `{Prefix}-{Env}-{Cluster}{Index}` shape | Infrastructure code already follows the pattern; deviations should be flagged |

If none of the above match, the project is purely code-side and this reference is not loaded.

## 2. The spine — server name is the primary key

Every deployment artifact (DNS A record, IIS binding, firewall rule, connection string, app-setting URL, monitoring target) traces back to a server name. **Treat the FQDN the same way the rest of this skill treats `CodePath`.** Anything else (IP, cluster VIP, bound port) is `Expected*` derived from the server name plus the patterns below; the `Actual*` value is read from DNS, the IIS config, or the firewall.

## 3. Server name pattern

```text
{Prefix}-[{Country}-{City}-]{Env}-{Cluster}{Index}[.{Domain}]
```

| Token | Meaning | Source |
| --- | --- | --- |
| `{Prefix}` | Company / org code, 3 letters | `.instructions.md` `## Network patterns / Prefix` |
| `{Country}` | ISO 3166-1 alpha-2 (e.g. `GB`, `US`) — optional | Optional; declare in `.instructions.md` only if multi-country |
| `{City}` | ISO 3166-2 alpha-3 (e.g. `LND`, `NYC`) — optional | Same as above |
| `{Env}` | `L` LIVE · `U` UAT · `D` DEV · `DM` DEMO · `DR` disaster recovery. Empty = LIVE. | Pattern is canonical; do not invent new codes |
| `{Cluster}` | Tier code: `DAT` databases · `SVC` services · `WEB` websites · `RDS` remote-desktop · `DC` domain controller · `DFS` file share · `WSUS` patch server · `EXCH` mail · `EPO` endpoint protection · custom (declared in `.instructions.md`) | |
| `{Index}` | Two-digit host index `01`–`32`. Empty = the cluster VIP / listener (not a node) | |
| `{Domain}` | AD or public domain. Optional in short form. | `.instructions.md` `## Network patterns / Domain` |

**Examples:**

```text
COM-DAT01.company.local       → COM company, LIVE, DAT cluster host 01
COM-U-WEB02.company.local     → COM, UAT, WEB host 02
COM-GB-LND-L-DC01.company.local → COM, GB London, LIVE, DC host 01
COM-DAT.company.local         → cluster VIP / SQL listener (no index)
```

A name that does not parse against this grammar produces deviation `name-mismatch` (§11).

## 4. IP address pattern

```text
{Range}.{System}{Env}.{Group}.{NIC}{Index}
```

| Token | Meaning | Values |
| --- | --- | --- |
| `{Range}` | RFC1918 supernet | `10` (Enterprise), `172.16-31` (Business), `192.168` (Home) |
| `{System}` | Solution number | `1` first solution, `2` second … (per `.instructions.md`) |
| `{Env}` | Environment digit | `0` LIVE · `1` UAT · `2` DEV · `3` DEMO · `4` DR |
| `{Group}` | Per-feature offset (DAT, SVC, WEB, …) | declared in `.instructions.md`, default `0` until features split |
| `{NIC}` | Network interface | `1` LAN (production east-west) · `2` HBN (cluster heartbeat). NIC 1 = odd, NIC 2 = even — already encoded by the `1`/`2` digit |
| `{Index}` | `0` cluster VIP, `1`–`9` host within the cluster | matches the host suffix in §3 |

**Worked examples (from the architecture spec):**

```text
10.10.0.10  → COM, LIVE, SQL cluster VIP,  LAN
10.10.0.11  → COM, LIVE, SQL host 01,      LAN
10.10.0.21  → COM, LIVE, SQL host 01,      HBN
10.11.1.30  → COM, UAT,  APP cluster VIP,  LAN
10.12.2.10  → COM, DEV,  DMZ cluster VIP,  LAN
```

A node whose IP does not match its server name's tier/environment produces deviation `ip-mismatch`.

## 5. Standard host-offset table (per /24 subnet)

Within a single environment subnet, every tier owns a fixed offset. Hand this table to the AI when generating a hosts file, NSG rules, or DNS zone:

| Tier | Cluster VIP | Host 01 | Host 02 | Notes |
| --- | --- | --- | --- | --- |
| `DAT` | `.10` | `.11` (LAN) / `.21` (HBN) | `.12` / `.22` | Database failover cluster |
| `SVC` | `.30` | `.31` / `.41` | `.32` / `.42` | Service failover cluster |
| `WEB` | `.50` | `.51` | `.52` | Load-balanced web farm |
| `RDS` | `.70` | `.71` | `.72` | Remote-desktop gateway |
| `RDSH` | — | `.91` | `.92` | Remote-desktop session hosts |
| `DC01/02` | — | `.201` | `.202` | Domain controllers |
| `WSUS` | — | `.210` | — | Patch server |
| `EXCH` | — | `.220` | — | Mail (or M365) |
| `EPO` | — | `.230` | — | Endpoint protection |
| `DFS` | — | `.240` | — | Distributed file share |

A host in the wrong offset for its tier triggers `ip-mismatch`. Adding a new tier requires declaring its offset in the per-repo `.instructions.md` first.

## 6. Network segments

| Segment | Purpose | Reachable by |
| --- | --- | --- |
| **LAN** | Production east-west traffic between WEB ↔ SVC ↔ DAT and admin tools | Internal nodes + admin jump-host |
| **HBN** | Cluster heartbeat between cluster nodes (low-latency, dedicated NIC) | Cluster nodes only |
| **WAN / DMZ** | Public-facing endpoints, edge load balancer, reverse proxy | Internet → firewall → WAN |

Cluster nodes (`DAT`, `SVC`) need **two NICs** (LAN + HBN). Web/RDS need one (LAN). DMZ-fronted web nodes need a third interface or sit in a separate WAN subnet.

A LIVE service connecting to a UAT database (or any cross-environment binding read from a connection string) triggers `env-cross-contamination` — the highest-severity deviation in this reference.

## 7. Port number pattern

```text
Port = {Solution}{Feature}{Project}{Mode}        (5 digits, IANA user-port range)
```

| Token | Width | Meaning |
| --- | --- | --- |
| `{Solution}` | 1 | `1` first solution, `2` second … |
| `{Feature}` | 2 | Reserved feature code (declared in `.instructions.md`) — e.g. `87` = Messenger, `80` = Reports, `92` = SQL Mirroring |
| `{Project}` | 1 | `0` server · `1` client · `2` SQL witness · `3` SQL principal · `4` SQL mirror |
| `{Mode}` | 1 | `0` LIVE · `1` UAT · `2` DEV · `3` DEMO · `4` DR |

**Why this pattern? Self-describing ports.** A 5-digit port becomes its own annotation — a developer, network admin, or AI looking at `18700` decodes it instantly as *solution 1 · Messenger · server · LIVE* without consulting a registry. Firewall rules, SIEM alerts, `netstat` output, and packet captures all gain free identification, and the AI's `port-mismatch` check is just a parse against the feature-code map declared in `.instructions.md`.

**Why a `{Mode}` digit?** When environments share a host (a developer workstation running all four modes, or any multi-tenant box), the `{Mode}` digit prevents cross-environment chatter — UAT cannot reach LIVE because they listen on different ports.

**When `{Mode}` can be uniform across environments.** If every environment has its **own dedicated, network-isolated infrastructure mirrored from a single specification** (LIVE / UAT / DEV each have their own DAT/SVC/WEB clusters and firewall rules block cross-env traffic at L3/L4), the network boundary already prevents cross-env chatter. In that case `{Mode}` can be `0` on every environment, and the same port number (`18700`) means *LIVE-on-the-LIVE-net*, *UAT-on-the-UAT-net*, etc. Declare `## Network patterns / Mode-uniform: true` in `.instructions.md` to opt in — the IP `{Env}` digit and the server-name `{Env}` token remain the authoritative environment markers, so the pattern is still self-describing on inspection (you read the host, then the port).

**Examples:**

```text
18700  Solution 1, Messenger, Server, LIVE
18701  Solution 1, Messenger, Server, UAT       (varying {Mode}; default)
18710  Solution 1, Messenger, Client, LIVE
18700  Solution 1, Messenger, Server, ANY-env   (Mode-uniform: true; env read from host)
```

A port that does not parse triggers `port-mismatch`. A LIVE process listening on a UAT-coded port triggers `env-cross-contamination` — **except in `Mode-uniform: true` mode**, where the port-vs-server-env cross-check is suppressed (the IP-vs-server-name cross-check still runs and remains the canonical env-correctness signal).

## 8. Cloud / Azure CAF alignment (dual-form support)

The legacy short form in §3–§7 was designed for on-prem AD-joined hosts (NetBIOS-friendly, 15-char-safe) and remains the default for existing infrastructure — **never rename a working AD-joined server just to look more Azure-y; the migration cost outweighs the cosmetic win**. For *new* cloud resources, the **Azure Cloud Adoption Framework (CAF)** convention is the de-facto standard and most internal/external tooling assumes it. This skill supports both forms; pick one per resource scope and declare it in `.instructions.md`.

### 8.1 Azure CAF server / resource name pattern

```text
{resource-type}-{workload}-{env}-{region}-{instance}
```

Examples:

```text
vm-com-prod-uks-001         generic VM, COM workload, LIVE/prod, UK South, instance 001
sql-com-prod-uks-001        SQL Server (logical) — same workload
app-com-uat-uks-001         App Service in UAT
func-com-dev-weu-002        Function App in DEV, West Europe
```

Lowercase, dash-separated, no dots in the resource portion (DNS suffix still appended for the FQDN). Instances are 3-digit (`001`–`999`).

### 8.2 Tier code aliases (legacy ↔ Azure CAF)

| Legacy tier | Azure CAF resource type(s) | Notes |
| --- | --- | --- |
| `DAT` | `sql` (Azure SQL / SQL MI), `mysql`, `psql`, `cosmos` | Choose by engine; `sql` is the default for SQL Server workloads |
| `SVC` | `vm` (IaaS), `app` (App Service), `func` (Functions), `aks` (Kubernetes) | Hosting model decides |
| `WEB` | `app` (App Service web), `agw` (Application Gateway), `afd` (Front Door) | `app` is default; LB layer adds `agw`/`afd` |
| `RDS` | `avd` (Azure Virtual Desktop), `bas` (Bastion) | `avd` replaces RDS in Azure |
| `RDSH` | `avd-shp` (AVD session-host pool) | |
| `DC` | `aadds` (AD Domain Services), `entra` (Microsoft Entra ID) | Or `vm-dc-…` if running classic AD on IaaS |
| `WSUS` | Azure Update Manager (no resource of its own) | Replaces WSUS on cloud-managed fleets |
| `EXCH` | `m365` / `o365` (hosted) | Self-hosted Exchange in cloud is rare |
| `EPO` | `defender`, `sentinel` | Microsoft Defender for Cloud + Sentinel SIEM |
| `DFS` | `st` (Storage Account), `afs` (Azure Files) | Storage Account with file share |

When auditing a hybrid repo, the AI should treat the **workload identity** (`com` here) as the join column — `COM-DAT01` on-prem and `sql-com-prod-uks-001` in Azure are the *same logical tier in two locations*.

### 8.3 Environment code aliases

| Legacy (single letter) | IP digit | Azure CAF | Display | Use in |
| --- | --- | --- | --- | --- |
| (empty) / `L` | `0` | `prod` (or `prd`) | LIVE | server names, IP, ports |
| `U` | `1` | `uat` | UAT | enterprise convention; Azure docs sometimes use `test` |
| `D` | `2` | `dev` | DEV | |
| `DM` | `3` | `dem` (or `demo`) | DEMO | |
| `DR` | `4` | `dr` | DR | |
| (none in legacy) | — | `tst` / `test` | TEST | cloud-only addition |
| (none in legacy) | — | `stg` / `staging` | STAGING | cloud-only addition |
| (none in legacy) | — | `qa` | QA | cloud-only addition |

The single-letter form survives because it fits the 15-char NetBIOS server-name budget. Three-letter forms are unambiguous and recommended for any new naming. **Do not mix `L` and `prod` for the same artifact** — pick one per scope.

### 8.4 Region abbreviations (Azure paired-region list, common subset)

| Region | Short | Region | Short |
| --- | --- | --- | --- |
| UK South | `uks` | East US | `eus` |
| UK West | `ukw` | East US 2 | `eus2` |
| West Europe | `weu` | West US | `wus` |
| North Europe | `neu` | West US 2 | `wus2` |
| France Central | `frc` | Central US | `cus` |
| Germany West Central | `gwc` | South Central US | `scus` |
| Switzerland North | `chn` | Southeast Asia | `sea` |
| Sweden Central | `sec` | East Asia | `ea` |

For other regions, use the lowercase Azure CLI region name (e.g. `australiaeast` → `aue`). Declare the chosen abbreviation in `.instructions.md` so deviation reports do not flag it.

### 8.5 Picking a form per repo

Set `## Network patterns / Naming form` in `.instructions.md` to one of:

- `legacy` — only the §3 short form is valid (default for existing on-prem-only infrastructure).
- `cloud-caf` — only the §8.1 Azure form is valid (default for new Azure-only deployments).
- `dual` — both forms are valid; the per-host inventory declares which form each host follows. Cross-references must use the **alias tables in §8.2 / §8.3** so the AI can compute one form from the other.

A host that uses one form when the repo declares another is `name-mismatch`. A host whose form is `dual`-allowed but whose tier code is not aliased in §8.2 is `off-convention` until the alias is added to `.instructions.md`.

## 9. Project / namespace / folder companion

This file owned the project-naming pattern in earlier revisions. It is now in [`project_patterns.md`](project_patterns.md), which keeps the spine "what is the binary called" separate from "where does the binary run". When auditing, load both — `network_patterns.md` populates the runtime address columns, `project_patterns.md` populates the build/install columns.

The bridge between the two is the **project-type → server-suffix mapping** (`project_patterns.md` §5): a `Server`-suffixed Console / Windows Service deploys to `SVC` (or `vm`/`app`/`func` in Azure), a `Client` deploys to `RDS` (or `avd`), a `WEB`/`API` deploys to `WEB` (or `app`). A binary on the wrong tier is `tier-mismatch`.

## 10. ActualValue discovery (where to read the truth)

| Artifact | Authoritative source |
| --- | --- |
| `ActualIp` | DNS A record / `hosts` file / `ipconfig` on the box / Azure NIC config |
| `ActualDnsName` | DNS / AD `Get-ADComputer` / Azure NIC DNS |
| `ActualPorts` | `netstat -ano` on the box, IIS `applicationHost.config` `<bindings>`, NSG / firewall rules, `appsettings*.json` connection strings |
| `ActualCluster` | `Get-ClusterNode` / Failover Cluster Manager / Azure SQL listener config |
| `ActualEnvironment` | Server name `{Env}` token + IP `{Env}` digit must agree; mismatch is the symptom of a misclassified node |
| `ActualInstallPath` | Setup project / MSI manifest / `C:\Program Files\...` scan (see `project_patterns.md` §4) |

When two sources disagree (e.g. server name says `-U-` but its IP digit is `0` for LIVE), surface as `env-cross-contamination` — never silently pick one as truth.

## 11. Deviation codes (network-specific, additive to §5 of SKILL.md)

| Code | Meaning | Action |
| --- | --- | --- |
| `name-mismatch` | Server name does not parse against §3 grammar (or the §8.1 Azure CAF grammar when the repo is in `cloud-caf` / `dual` mode) | Recommend rename only if no override is declared in `.instructions.md` |
| `ip-mismatch` | IP does not match the §4 pattern given the server's tier and environment | Re-IP or correct the inventory; cross-reference firewall rules before recommending |
| `port-mismatch` | Port does not match §7 pattern | If the port is owned by a third-party service, declare it in `.instructions.md` as an override; otherwise renumber |
| `env-cross-contamination` | Two artifacts that should agree on environment disagree (server name says LIVE, IP says UAT; LIVE service points at UAT DB; UAT process listens on a LIVE port). The port-vs-host portion of this check is suppressed when `Mode-uniform: true` is declared (§7); the IP-vs-host portion always runs | **Highest severity.** Block deploy / open incident. Never auto-fix — connection strings cross environments only by deliberate, declared exception |

The general SKILL.md `off-convention` and `none` codes also apply. Install-path deviations are owned by [`project_patterns.md`](project_patterns.md) §8 (`install-path-mismatch`).

## 12. Anti-patterns

- **Hard-coding IPs in app config** — bypasses §4. Use the cluster VIP / listener name from §5 so failover is transparent.
- **Reusing one port across environments** — defeats the §7 design. Two services from different envs running on the same host now collide.
- **Treating `LIVE` as the empty string in some places and `L` in others** — pick one per artifact (server names use `L` token; IPs use the `0` digit; folder/namespace tokens use the empty form). Mixing produces mismatches that look like real defects.
- **Adding a new tier without declaring its `{Group}` offset** — every node in the new tier will look like an `ip-mismatch` until the offset table is updated in `.instructions.md`.
- **Using NIC 2 as a second LAN path** — `HBN` is reserved for cluster heartbeat. Co-tenanting it with general traffic breaks heartbeat-loss detection and produces split-brain risk. Get a third NIC if a second LAN path is needed.
- **Documenting the network plan in code comments instead of `Architecture/`** — the plan must live alongside the deviation report so the AI can compare them. Comments rot; an `Architecture/*.htm` or `*.md` is grep-able.
- **Mixing legacy and Azure CAF forms in a single host inventory** — pick `legacy` / `cloud-caf` / `dual` per repo (§8.5). In `dual` mode, every host still declares which form it uses; ad-hoc mixing produces noisy `name-mismatch` rows that mask real defects.

## 13. Interaction with the per-repo `.instructions.md`

Add a `## Network patterns` block:

```markdown
## Network patterns

- **Prefix:** `COM`
- **Naming form:** `legacy` | `cloud-caf` | `dual`
- **Domain (LAN):** `company.local`
- **Domain (WAN):** `company.com`
- **Country / City:** omitted (single-site)
- **Solution number:** `1`
- **Default Azure region (for cloud-caf / dual):** `uks`
- **Mode-uniform:** `false` (default — vary `{Mode}` per environment) | `true` (each env has its own isolated, mirrored network; `{Mode}` is fixed to `0` everywhere — see §7)
- **Custom feature offsets:** `MSG=87`, `RPT=80` (used in §7 port composition)
- **Custom tiers:** none (default DAT/SVC/WEB/RDS apply)
- **Architecture spec:** `Architecture/default.htm`

### Overrides
- LIVE port suffix is `0` (default); the `9` suffix is reserved for shared infra and must not be assigned to a feature.
```

Drift between this block and the `Architecture/` document is itself a defect — keep them in sync, treat the `.instructions.md` block as canonical for AI use, and the human-readable `Architecture/` doc as the diagram view of the same facts.
