## Files

- `developer-info.md` - Developer information about the solution, which will be used when creating the repository-analysis.instructions.md file.
- `instructions.md` - Main AI Agent System Message instructions used by AI Agents, like CLINE or CoPilot.
- `repository-analysis.instructions.md` - Autogenerated Repository Analysis file that is supplied to the AI Agent as a System message after instructions.md.
- `repository-analysis.prompt.md` - User Message prompt that instructs AI to create repository-analysis.instructions.md.
- `Update-AgentInstructions.ps1` - Sets all `*instruction.md` files as AI agent system message instruction files. Used by AI agents, like CLINE or Copilot.

## Custom instructions: GitHub Copilot

With GitHub Copilot, you can receive chat responses tailored to your team'ss workflow, preferred tools, and project specifics.
Instead of adding this contextual detail to each chat query, you can create a file that supplies this information automatically.
While this additional context won't appear in the chat, it is available to GitHub Copilot, allowing it to generate more accurate and relevant responses.

**How to Enable Custom Instructions**

Enable the feature via Tools > Options > GitHub > Copilot > and check (Preview) Enable custom instructions to be loaded from .github/copilot-instructions.md files and added to requests.
Add copilot-instruction.md in the root of your respository inside the .github file, create the file if it doesn't already exist.
GitHub Copilot Enable Custom Instructions

Learn more about creating custom instructions:
https://docs.github.com/en/enterprise-cloud@latest/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot

## Custom instructions: CLINE

All CLINE instructions are stored inside the .clinerules\ folder.
All \*.md files will be loaded as system messages.

## Custom instructions: OpenAI Codex

Instructions are stored in `%USERPROFILE%\.codex\instructions.md` file.


## User Instructions to create `repository-analysis.md`

Note: Switch AI agent to `Plan` mode before submitting this message. This will yield better results.


### LLM Selection Guideline

If your deployment environment allows, prefer a newer, higher-capacity model—such as Anthropic Claude Sonnet 4 or Google Gemini 2.5 Pro - instead of the current OpenAI GPT 4 lineup.  These frontier models typically deliver stronger reasoning, broader context windows, and more consistent output quality on complex tasks.

### Install the Mermaid preview plug-in

	1. Open Extensions (Ctrl + Shift + X).
	2. Search: Markdown Preview Mermaid Support (publisher: Matt Bierner).
	3. Click Install – or hit Ctrl + P.
	
### Open Preview

	1. Open the menu on the tab header of the file.
	2. Click "Open Preview" – or hit Ctrl + Shift + V.
	
### Re Open Preview

	1. Open the menu on the tab header of the file.
	2. Click "Reopen Editor With..."
	3. Click "Markdown Preview (Built-In)"
