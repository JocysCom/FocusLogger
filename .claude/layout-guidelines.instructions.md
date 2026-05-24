# Layout Guidelines

> For the general bidirectional-simplification principle (markup ↔ CSS is one of several structural pairs it covers — alongside file ↔ folder, route ↔ controller, model ↔ schema), see the `solution-patterns` skill (§2 #2). The rules below are the markup ↔ CSS-specific tactics.

Use intrinsic, fluid, constraint-based layout design.

Prefer layouts that adapt naturally to available space, content, scaling, localization, and platform behavior.

Avoid fixed dimensions, absolute positioning, and pixel-perfect assumptions unless they are clearly necessary.

Use the platform or framework’s best layout primitives instead of manually positioning UI elements.

Prefer:
- natural sizing
- relative sizing
- minimum and maximum constraints
- wrapping and reflow
- shared spacing and sizing tokens
- adaptive layout features

Layouts must remain usable when windows, containers, text, scaling, DPI, or content change.

Use fixed values only for true constants, such as borders, icons, minimum hit targets, or platform-required measurements.

When choosing between a rigid layout and a flexible layout, choose the flexible layout unless there is a strong reason not to.

## Information density in tabular lists

Pack narrow columns on the left so a reader's eye can follow each row without crossing wide empty gutters. Wide free-text columns (descriptions, comments, multi-line notes) belong **at the right**, where they absorb the slack of the surrounding viewport. Narrow columns interleaved with a wide one in the middle of a row break visual continuity.

A reasonable default order:

1. Identifier (key or short code).
2. Inline state controls (toggles, badges).
3. Row action icons (edit, delete) at single-icon width.
4. Narrow data columns (codes, counts, statuses, dates).
5. One greedy / trailing column for the longest content, or an empty filler cell when nothing fits the role.

Never place a free-text column in the middle of a row.

## Simplicity is the goal — fix at the source

Every visual problem has a root cause. Find it before adding anything.

1. **Search for the rule that caused the visible defect** before writing CSS to mask it. A `width: 100%` somewhere upstream is fixed by deleting that rule, not by adding `width: auto !important` downstream. A `margin-bottom` on `[type=submit]` from the framework is fixed by overriding the same selector with the same specificity, not by wrapping the button in `<div style="margin-bottom: -10px">`.
2. **Reuse before invent.** If a list, panel, button, header, or row pattern already exists, every new instance uses the same class names — no `chat-session-list`, `link-picker-list`, `nav-item`, `help-doc-list` parallel implementations of the same concept. They share `.list-item`, `.surface`, `.panel-head`, `.icon-btn`, `.pill-toggle` primitives.
3. **Remove before add.** Refactoring CSS means *fewer* rules, not more. If a new component requires a new class, first ask whether the existing primitives + a small markup change cover it. They almost always do.
4. **Refactor BOTH layout and CSS together.** When a page demands a new visual, treat that as evidence the page is wrong, not the system. Adapt the page to the canonical pattern; reserve new CSS only for genuinely novel mechanics that no existing page would also benefit from.
5. **Match Pico's selector specificity** when overriding framework rules. A plain `button { ... }` rule (specificity 0,0,1) loses to Pico's `[type=submit] { ... }` (0,1,0). Override with the same selectors so the cascade naturally wins on file order.
6. **Auto-size before forcing a size.** A button with content + padding + border auto-sizes correctly in most cases. `width`, `height`, `min-height`, `min-width` are reserved for cases where content cannot drive the size (icon-only buttons that must be square, fixed-grid layouts).
7. **Drop framework anti-patterns at the source.** Pico's `[role=group]` triggers a connected-input-group visual (full-width children, cut adjoining corners). On any UI that wants individually rounded buttons, omit `role="group"` from the markup; an `aria-label` on the wrapper provides the screen-reader grouping without the visual cost.
