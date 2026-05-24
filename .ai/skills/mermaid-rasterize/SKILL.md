---
name: mermaid-rasterize
description: "Rasterize specific mermaid blocks inside a markdown file into PNG images. Use when mermaid diagrams don't render in the target viewer (GitHub, Notion, PDF, etc.). Triggers on: rasterize diagrams, mermaid isn't rendering, convert mermaid to images, replace mermaid blocks with images."
---

# Mermaid Rasterize

Converts user-selected mermaid blocks into a PNG + `.mmd` source file, then rewrites only those blocks in the markdown with image references.

## 0. Resolve inputs from context — avoid redundant reads

Before reading any file, check what is already available in the conversation:

| What to resolve | Check first | Fallback |
|-----------------|-------------|----------|
| Mermaid block content | Already in conversation? Use it directly | Read the markdown file |
| Which blocks to convert | User specified them? Proceed | List found blocks and ask |
| Markdown file path | Mentioned in conversation? Use it | Ask the user |
| Output/asset folder | Mentioned in conversation? Use it | Run detection (Step 2) |

Only perform file reads for information that is genuinely missing. Never re-read content already visible in context.

## 1. Install mmdc

```bash
which mmdc || npm install -g @mermaid-js/mermaid-cli
```

On sandbox errors (Linux/CI), create once and reuse:
```bash
echo '{"args":["--no-sandbox","--disable-setuid-sandbox"]}' > /tmp/puppeteer.json
```
Append `--puppeteerConfigFile /tmp/puppeteer.json` to every `mmdc` call.

## 2. Detect asset folder (only if not already known)

```bash
ls $(dirname <file>) && ls $(dirname <file>)/..
```

Pick the first match:
1. `assets/` exists → use it
2. `images/` or `img/` or `static/` exists → use it
3. Other images already alongside the `.md` → use same folder
4. Nothing found → ask the user before continuing

## 3. Name each diagram

- **contextname**: markdown filename without extension, slugified (e.g. `sistema-auth`)
- **diagramname**: infer from diagram type or first node label; fallback to `diagram-1`, `diagram-2`

Output files per block:
```
<asset-folder>/diagram-{contextname}-{diagramname}.mmd   ← source
<asset-folder>/image-{contextname}-{diagramname}.png     ← rendered
```

## 4. Extract, save, and convert

For each confirmed block:

```bash
cat > <asset-folder>/diagram-{contextname}-{diagramname}.mmd << 'EOF'
<mermaid content>
EOF

mmdc \
  -i <asset-folder>/diagram-{contextname}-{diagramname}.mmd \
  -o <asset-folder>/image-{contextname}-{diagramname}.png \
  --scale 2 --backgroundColor white
```

## 5. Rewrite the markdown

Replace only the converted blocks with a relative image reference. Leave all other blocks untouched.

```markdown
![{diagramname}]({asset-folder}/image-{contextname}-{diagramname}.png)
```

Save updated `.md` and generated files to `/mnt/user-data/outputs/` mirroring the folder structure.

## 6. Present outputs

Call `present_files` with the updated `.md` first, then each `.png`. Tell the user which diagrams were converted and which were skipped.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Sandbox crash | Add `--puppeteerConfigFile /tmp/puppeteer.json` |
| `mmdc` not found | `export PATH="$PATH:$(npm root -g)/.bin"` |
| Blank PNG | Validate syntax at https://mermaid.live |
| Broken image links | Verify relative path from `.md` to asset folder |
