# ASP.NET Core patterns (Razor Pages, MVC, Minimal APIs)

> Scope: ASP.NET Core projects using any of Razor Pages (`Pages/`), MVC (`Controllers/` + `Views/`), or Minimal API (`MapGet`/`MapPost` in `Program.cs`). A single project may mix all three.

## 1. Stack signal

[`detect_stack.py`](../scripts/detect_stack.py) flags this stack when a `.csproj` file in the repo uses `<Project Sdk="Microsoft.NET.Sdk.Web">`. Sub-mode detection:

| Evidence | Sub-mode |
|---|---|
| `Pages/` folder exists and contains `.cshtml` files | `razor-pages` |
| `Controllers/` folder exists and contains `*Controller.cs` | `mvc` |
| `Program.cs` contains `app.Map(Get|Post|Put|Delete|Patch)` | `minimal-api` |
| None of the above (flat web project) | `minimal-flat` |

Report **all** sub-modes found — a single project can be all of them at once. Every CSV row captures the sub-mode it belongs to via its `Role` value.

## 2. Role inference (path + filename → CSV `Role` column)

| File pattern | `Role` |
|---|---|
| `Pages/**/*.cshtml` (excluding `_ViewImports`, `_ViewStart`, `_Layout`) | `page` |
| `Pages/**/*.cshtml.cs` | `page-model` |
| `Pages/Shared/_*.cshtml` | `layout` |
| `Controllers/*Controller.cs` | `controller` |
| `Views/{Controller}/*.cshtml` | `view` (the render template for an MVC action) |
| `Areas/{Area}/Controllers/*Controller.cs` | `controller` |
| `Areas/{Area}/Pages/**/*.cshtml` | `page` |
| `Areas/{Area}/Views/{Controller}/*.cshtml` | `view` |
| `Program.cs` (when it contains `app.MapXxx` calls) | each `MapXxx` call becomes a row with `Role = endpoint` |
| `wwwroot/**` | not scanned (static assets) |
| `*.cs` not matching above | `service`, `model`, `middleware`, etc. (see name suffix) |
| `*Tests.cs` in a sibling `{Project}.Tests` | `test` (qa-tester §5.2) |

## 3. Code → UI path rules

**Razor Pages** (folder-based):

```text
Pages/Index.cshtml                     → /
Pages/About.cshtml                     → /About
Pages/Orders/Index.cshtml              → /Orders
Pages/Orders/Details.cshtml            → /Orders/Details
Pages/Orders/Edit.cshtml  + @page "{id:int}"   → /Orders/Edit/{id:int}
Areas/Admin/Pages/Users.cshtml         → /Admin/Users
```

A file's first line often declares a route override via `@page "..."` — always parse it; it supersedes the folder-derived path.

**MVC controllers** (attribute routing first, convention second):

```text
# Attribute routing (preferred):
[Route("api/[controller]")] on OrdersController → /api/orders
[HttpGet("{id:int}")] on OrdersController.Get(int id) → /api/orders/{id:int}

# Convention routing (fallback, from app.MapControllerRoute("default", "{controller=Home}/{action=Index}/{id?}")):
HomeController.Index() → /
HomeController.About() → /Home/About
OrdersController.Details(int id) → /Orders/Details/{id?}
```

Each public action method on a controller is one row with `Role = controller` and its own `ExpectedUiPath`. The controller file itself gets one aggregate row only if none of its actions matched — otherwise the actions are the rows that matter.

**Minimal API** (declared in `Program.cs`):

```text
app.MapGet("/health", () => ...)           → /health       (Role=endpoint)
app.MapPost("/api/orders", handler)        → /api/orders
app.MapGroup("/api/v1").MapGet("/status")  → /api/v1/status
```

Each `Map*` call is a row. `CodePath = Program.cs`; add a `line` field to `Notes` so rows remain unique (`line:42`, `line:57`, …).

## 4. Actual UI path discovery

- **Razor Pages**: the path *is* the folder tree + `@page` directive. `ActualUiPath` is computed the same way as `ExpectedUiPath`. Divergence is only possible via `app.MapRazorPages()` being omitted or custom conventions — flag `ui-missing` if Razor Pages middleware isn't wired up in `Program.cs`.
- **MVC**: parse `[Route]`, `[HttpGet("...")]`, `[HttpPost("...")]` etc. on the controller class and each action. Fall back to convention routing (parse `app.MapControllerRoute` call in `Program.cs`) when no attribute is present.
- **Minimal API**: `ActualUiPath` = first argument to the `Map*` call; compose with parent `MapGroup("...")` when nested.

## 5. Default test path (reuses qa-tester §5.2)

| Code path | `ExpectedTestPath` |
|---|---|
| `{Project}/Controllers/FooController.cs` | `{Project}.Tests/Controllers/FooControllerTests.cs` |
| `{Project}/Pages/Foo.cshtml.cs` | `{Project}.Tests/Pages/FooTests.cs` |
| `{Project}/Pages/Foo.cshtml` | *(no test; the `.cs` file is what carries logic)* |
| `{Project}/Program.cs` | `{Project}.Tests/ProgramTests.cs` (integration tests against the whole pipeline) |

`@under-test` headers on the test files are the authoritative link. Report `test-relocated` when a test references this code file from a non-canonical path.

## 6. Stack-specific anti-patterns

- **Mixing Razor Pages and MVC for the same feature.** They're both first-class but duplicating "orders" as both `/Orders/Index.cshtml` and `OrdersController.Index()` guarantees one of them is a zombie. Pick per-feature and flag crossings.
- **Routes declared in three places at once.** Attribute routing on the controller + `MapControllerRoute` convention + `UseEndpoints` callback — when all three are wired up, divergence is inevitable. Choose one primary style per project and declare it in `.instructions.md`.
- **A `Pages/` folder with no `app.MapRazorPages()` in `Program.cs`.** The pages exist on disk but never reach the router. Every row in the scan would be `ui-missing`.
- **Minimal-API handlers piling up in `Program.cs`.** Past ~15–20 endpoints, split into `Endpoints/{Area}.cs` extension-method files. The skill doesn't enforce this but notes it in the deviation report via `Notes`.

## 7. References

- Razor Pages intro: <https://learn.microsoft.com/aspnet/core/razor-pages/>
- MVC routing: <https://learn.microsoft.com/aspnet/core/mvc/controllers/routing>
- Minimal APIs overview: <https://learn.microsoft.com/aspnet/core/fundamentals/minimal-apis/overview>
