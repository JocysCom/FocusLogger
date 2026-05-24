# Angular patterns

> Scope: Angular 17+ standalone components with lazy routes, and older NgModule-based projects. Follows the [official Angular style guide](https://angular.dev/style-guide).

## 1. Stack signal

[`detect_stack.py`](../scripts/detect_stack.py) flags this stack when **any** of these are true at the repo root or under a `ClientApp/`-style subdirectory:

- A file named `angular.json` exists.
- `package.json` contains `"@angular/core"` in `dependencies` or `devDependencies`.

## 2. Role inference (extension + suffix → CSV `Role` column)

| File pattern | `Role` |
|---|---|
| `*.component.ts` | `ui-view` |
| `*.component.html` | `template` |
| `*.component.scss` / `*.component.css` | `style` |
| `*.service.ts` | `service` |
| `*.module.ts` | `module` |
| `*.pipe.ts` | `pipe` |
| `*.directive.ts` | `directive` |
| `*.guard.ts` / `*-guard.ts` | `guard` |
| `*.resolver.ts` / `*-resolver.ts` | `resolver` |
| `*.interceptor.ts` / `*-interceptor.ts` | `interceptor` |
| `*.model.ts` / `*.interface.ts` | `model` |
| `*.spec.ts` | `test` |
| `*.stories.ts` | `story` (Storybook; UI-adjacent, no route) |

Angular's evolving convention is **hyphen-separated**: `auth-guard.ts` (new) or `auth.guard.ts` (older). Accept both.

## 3. Default Code → UI path rule

Angular projects vary more than any other stack. The **default** rule — folder-based inference — is a guess, always subordinate to the actual `Routes` declaration. The skill reads the routes; it doesn't guess from folders alone.

**Folder convention (feature folders):**

```text
src/app/{feature}/{name}-page/{name}-page.component.ts
src/app/{feature}/{name}-page/{name}-page.component.html
src/app/{feature}/{name}-page/{name}-page.component.scss
```

**Default inferred route:** `/{feature}/{name}`.

**Actual route discovery (authoritative):**

1. Find all files matching `**/*.routes.ts`, `**/app.routes.ts`, `**/app-routing.module.ts`.
2. Parse `Routes` array literals (or `RouterModule.forRoot` / `forChild`) for `{ path, component, loadComponent, loadChildren }` entries.
3. For each entry, resolve the component file path and record the full route (concatenating parent `path` segments through lazy-loaded chains).
4. `ActualUiPath = /parent/child/...` for the matched component.

Components that appear in a folder but are never referenced by any route are flagged `ui-missing`.

## 4. Common project shapes

Two legitimate top-level layouts — both are "on convention":

```text
# Style A: by-feature (preferred for apps with clear bounded contexts)
src/app/
├── core/               # singleton services, interceptors, guards
├── shared/             # reusable, stateless components and pipes
├── features/
│   ├── dashboard/
│   │   ├── dashboard-page/
│   │   └── dashboard.routes.ts
│   └── orders/
└── app.routes.ts

# Style B: by-type (older or smaller apps)
src/app/
├── components/
├── services/
├── pages/
└── app-routing.module.ts
```

The repo's `.ai/solution-patterns.instructions.md` declares which style applies. Mixing them is the most common `off-convention` deviation.

## 5. Stack-specific anti-patterns

- **Forcing folder = route mirroring.** The Angular style guide explicitly separates the two concerns (folder for dev convenience, routes for user convenience). Enforce the *declared* feature-folder structure, not a fabricated folder-to-URL rule.
- **Files outside a `{name}-page/` set.** An orphan `.component.ts` without its `.html` / `.scss` siblings is almost always a deviation — usually a file someone moved halfway and didn't finish.
- **Mixing `ng generate` output styles.** Some files use `auth.guard.ts` (dot-suffix), others `auth-guard.ts` (hyphen-suffix). Pick one in the `.instructions.md` override; the deviation report flags the stragglers.
- **Lazy-loaded module with no `loadChildren` import path that matches a folder.** A route string says one thing, the loader points at a folder that doesn't exist — always a broken refactor.

## 6. Test path inference (delegates to qa-tester)

Angular uses **collocated** tests by convention: `foo.component.ts` → `foo.component.spec.ts` in the **same folder**. This differs from the qa-tester §5.2 C# mirror (where tests live in a sibling `.Tests` project).

For Angular files:

- `ExpectedTestPath = <same folder>/<stem>.spec.ts`
- The qa-tester `@under-test` header convention does not apply (TypeScript, not C#).
- Report `test-missing` when the `.spec.ts` sibling is absent.

## 7. References

- Angular style guide: <https://angular.dev/style-guide>
- Routing guide: <https://angular.dev/guide/routing>
