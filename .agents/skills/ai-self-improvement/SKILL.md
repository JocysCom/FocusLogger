---
name: ai-self-improvement
description: Update, create, improve, and synchronise this repository's AI agent instructions and related assets (including skills). Use when the user asks to create or edit a skill/SKILL.md, modify the agent's own instructions/processes, restructure instruction governance, migrate instruction content into skills, or run/adjust the sync pipeline that publishes `.ai/` sources into agent-specific folders. Load this skill before writing any SKILL.md, .instructions.md, or touching any skills/ folder (.ai/, .claude/, .roo/, .github/). It tells you the correct location (.ai/) and the sync step, so files end up in the right place.
---

# AI Self-Improvement (Instructions + Skills)

## Critical: `.ai/` is the Primary Source for ALL Agents

The `.ai/` folder is the **single source of truth** for all AI agent configurations in this repository. This applies to:

- **CLINE / Roo Code** — synced to `.roo/rules/` and `.roo/skills/`
- **GitHub Copilot** — synced to `.github/copilot-instructions.md`
- **OpenAI Codex / AGENTS.md** — synced to `AGENTS.md` at repo root
- **Claude Code** — synced to `.claude/*.instructions.md` and `.claude/skills/`

**IMPORTANT:** When asked to modify skills, instructions, or perform any AI self-improvement task, you MUST:

1. Locate the source file under `.ai/` (not the agent-specific output)
2. Make changes to the `.ai/` source
3. Run the sync script to propagate changes to all agents

## Path Mapping Reference

When you encounter a path in an agent-specific folder, map it to `.ai/`:

| Agent-Specific Path | Source Path (Edit Here) |
|---------------------|------------------------|
| `.roo/rules/*.md` | `.ai/*.instructions.md` |
| `.roo/skills/<name>/SKILL.md` | `.ai/skills/<name>/SKILL.md` |
| `.github/copilot-instructions.md` | `.ai/instructions.md` (generated) |
| `AGENTS.md` | `.ai/instructions.md` (generated) |
| `.claude/*.instructions.md` | `.ai/*.instructions.md` |
| `.claude/skills/<name>/SKILL.md` | `.ai/skills/<name>/SKILL.md` |

**Example:** If asked to update `.roo/skills/ai-self-improvement/SKILL.md`, you must edit `.ai/skills/ai-self-improvement/SKILL.md` instead.

## Editable instruction files (sources of truth)

You can update your own instruction files under `.ai/`:

- `.ai/instructions.md` — the main system instructions file
- `.ai/*instructions.md` — additional instruction files (auto-included)
- `.ai/*instructions-detail.md` — detailed instruction files (read only when needed)
- `.ai/skills/<name>/SKILL.md` — skill definition files

## Workflow

1. Treat `.ai/` as the **single source of truth** for agent instructions **and skills**.
2. When creating or migrating a skill, create/update it under `.ai/skills/`.
3. Make instruction changes in `.ai/instructions.md` and related `*.instructions.md` / `*.instructions-detail.md` files.
4. Do **not** edit generated outputs directly (they are produced by the sync script):
   - `.roo/rules/`
   - `.roo/skills/`
   - `.github/copilot-instructions.md`
   - `AGENTS.md`
   - `.claude/`
5. **Test changes before syncing** — verify scripts execute correctly and changes work as expected.
6. After testing, run the sync script to apply to all agents.

## Testing Before Sync

Before running the sync script, always verify your changes work correctly:

- **For script changes**: Execute the modified script and verify output is correct
- **For instruction changes**: Review the markdown renders properly and instructions are clear
- **For skill changes**: Test any bundled tools or scripts included in the skill

**Example**: If you modify a PowerShell script in a skill, run it directly from `.ai/skills/<name>/scripts/` to confirm it works before syncing.

## Activation process

After editing instruction files (or master skills), run from repository root:

```powershell
.\.ai\skills\ai-self-improvement\scripts\Sync-AgentAssets.ps1 AUTO
```

This script synchronizes changes from `.ai/` to all agent-specific folders.

## Single source of truth

**Never embed template content in instructions — reference template files instead.**

Example:

- ✅ "Template maintained in `pr/checklist.template.md`"
- ❌ Pasting template content into instructions

## Bundled scripts

- Sync entrypoint (instructions + skills): `.ai/skills/ai-self-improvement/scripts/Sync-AgentAssets.ps1`
