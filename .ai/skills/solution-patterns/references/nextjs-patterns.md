# Next.js patterns

> Scope: Next.js 13+ App Router (`app/` directory) and legacy Pages Router (`pages/` directory). Folder = URL is enforced by the framework — the mapping is deterministic by design.

## 1. Stack signal

[`detect_stack.py`](../scripts/detect_stack.py) flags this stack when **any** of these is true:

- `next.config.js` or `next.config.ts` or `next.config.mjs` exists at the repo root.
- `package.json` contains `"next"` in `dependencies` or `devDependencies`.

## 2. Role inference (extension + filename → CSV `Role` column)

App Router (`app/`):

| File pattern | `Role` |
|---|---|
| `**/page.tsx` / `**/page.jsx` / `**/page.js` | `ui-view` (the page for this route) |
| `**/layout.tsx` | `layout` |
| `**/loading.tsx` | `loading-ui` |
| `**/error.tsx` / `**/global-error.tsx` | `error-boundary` |
| `**/not-found.tsx` | `not-found-ui` |
| `**/route.ts` / `**/route.js` | `endpoint` (HTTP handler) |
| `**/template.tsx` | `template` |
| `**/default.tsx` | `parallel-fallback` |
| `**/middleware.ts` (at root) | `middleware` |

Pages Router (`pages/`):

| File pattern | `Role` |
|---|---|
| `pages/**/*.tsx` excluding `_app`, `_document`, `_error` | `ui-view` |
| `pages/_app.tsx` | `layout` |
| `pages/_document.tsx` | `document` |
| `pages/api/**/*.ts` | `endpoint` |

Tests are collocated by convention: `*.test.ts(x)` / `*.spec.ts(x)` → `Role = test`.

## 3. Code → UI path rule

App Router:

```text
app/about/page.tsx                     → /about
app/dashboard/[id]/page.tsx            → /dashboard/:id
app/(marketing)/pricing/page.tsx       → /pricing               (route group: parens stripped)
app/shop/@cart/page.tsx                → /shop (parallel slot, does not add a segment)
app/blog/[...slug]/page.tsx            → /blog/:slug*           (catch-all)
app/blog/[[...slug]]/page.tsx          → /blog/:slug?           (optional catch-all)
```

Pages Router:

```text
pages/about.tsx                        → /about
pages/dashboard/[id].tsx               → /dashboard/:id
pages/api/users/[id].ts                → /api/users/:id
```

**Transform rules:**

- `(folder)` → stripped (route group, organisational only).
- `@slot` → stripped (parallel route slot).
- `[param]` → `:param`.
- `[...param]` → `:param*` (catch-all).
- `[[...param]]` → `:param?` (optional catch-all).
- `_folder` (underscore prefix) → private folder, **not a route**; mark `ui-missing` unless inside `api/` (Pages Router allows `pages/api/_private` as a shared helper).

## 4. Actual UI path discovery

Unlike Angular, Next.js enforces folder=route. The `ActualUiPath` is computed the same way as `ExpectedUiPath` — they match by construction. The only divergence sources are:

- Typos or accidental renames that the framework would reject at build time (the `pattern_map.py` scanner catches these before the build does).
- Rewrites / redirects declared in `next.config.{js,ts}` — these add alternate URLs that don't correspond to a file. Record them as `Notes` on the target page's row (`rewrite: /shop ← /store`), not as separate rows.

## 5. Stack-specific anti-patterns

- **Duplicating the routing tree in a custom config.** Next.js derives routing from folders; a parallel hand-maintained route list defeats the framework and the skill. If rewrites are needed, use `next.config.js` `rewrites()` — nothing else.
- **Mixing App Router and Pages Router in the same feature.** Next.js allows both to coexist during migration, but a single feature split across both is a deviation. Pick one per feature; flag the stragglers.
- **Components rendering at `/` that live outside `app/` or `pages/`.** A component imported into a page file is a component, not a route — it belongs under a folder like `components/` or `ui/` with `Role = ui-view` only if actually rendered as a route entry point. The scanner treats non-`page.tsx` / non-`pages/*.tsx` files as components (no `ExpectedUiPath`).

## 6. Test path inference

Next.js test convention is collocation — same folder, `.test` or `.spec` infix:

- `ExpectedTestPath = <same folder>/<stem>.test.tsx` (or `.spec.tsx`, depending on project choice — declare in `.instructions.md`).
- Qa-tester `@under-test` headers don't apply (TypeScript/JavaScript, not C#).
- Report `test-missing` when no sibling test file exists.

Some teams use a separate top-level `__tests__/` mirroring the app tree. If so, declare the mirror path in `.instructions.md` and the scanner will honour it.

## 7. References

- App Router project structure: <https://nextjs.org/docs/app/getting-started/project-structure>
- File-system conventions: <https://nextjs.org/docs/app/api-reference/file-conventions>
- Routing overview: <https://nextjs.org/docs/app/building-your-application/routing>
