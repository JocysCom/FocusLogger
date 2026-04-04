# Coding Guidelines

- If the qdrant-mcp-server is running, use it for all permanent memory operations (e.g. storing user information).
- After making changes, ALWAYS start a new server for testing.
- Kill all existing related servers from previous testing before starting a new server.
- Prefer the simplest viable solution; avoid over-engineering.
- Do not add broad try/catch or wrapper layers unless required by a failing test or explicit requirement; if you catch, rethrow to preserve the stack.
- Before writing new code, actively look for existing utilities or functions that can be reused instead of duplicated.
- New helper methods or classes must be justified with a clear, documented need for functionality that is unavailable elsewhere in the codebase.
- Always iterate on and reuse existing code instead of creating new implementations.
- Avoid adding layers of abstraction that do not deliver clear value.
- Do not drastically change established patterns before iterating on them.
- No duplication / SSOT: update or move existing code instead of adding parallel implementations. If you introduce a replacement, remove the old one **in the same change**.
- Write code that accounts for different environments (dev, test, and prod).
- Only modify what is explicitly requested or clearly necessary; do **not** create new files or modules unless explicitly requested.
- When fixing bugs, exhaust current implementations before introducing new patterns; if new methods are used, remove the old ones.
- Keep the codebase clean and organized.
- Avoid one-off scripts unless absolutely necessary.
- Use mocks only for tests, not for dev or prod.
- Never add stubbing or fake data in dev or prod environments.
- Never overwrite the .env file without explicit confirmation.
- Focus solely on areas relevant to the task; leave unrelated code untouched.
- Write thorough tests for all major functionality.
- Avoid major changes to the existing architecture unless explicitly instructed.
- Always consider the impact on other methods and areas of the code.
- Prefer to wrap long lines for better readability.
- Preserve existing formatting; limit formatting to lines you changed and match surrounding style. Also remove any unused imports/usings or dead code **introduced by your edits**.
- Stability primitives (repeatability > cleverness): when the repo provides an established way to perform an operation (repo-owned script, documented command snippet, standard PS1 under .ai/Scripts), treat it as the single source of truth. Use it verbatim instead of synthesizing “equivalent” commands. Only deviate when explicitly asked or when the primitive is proven broken in this environment (and then fix the primitive, not invent a parallel path).
- No code file that you **create or modify** may exceed **6000 tokens (~24 KB)** once your changes are applied.
  - If your changes alone would push the file past this limit, either trim the change or ask for explicit permission to refactor; do **not** alter unrelated code solely to meet the limit.
  - Existing oversized files are left untouched unless the user explicitly requests a refactor.

Use the following guidelines:

1. Doc Comment Enhancement for IntelliSense

    - Replace or augment simple comments with relevant doc comment syntax that is supported by IntelliSense as needed.
    - Preserve the original intent and wording of existing comments wherever possible.

2. Code Layout for Clarity

    - Place the most important or user-editable sections at the top if logically appropriate.
    - Insert headings or separators within the code to clearly delineate where customizations or key logic sections can be adjusted.

3. No Extraneous Code Comments

    - Do not include "one-off" or user-directed commentary in the code.
    - Confine all clarifications or additional suggestions to explanations outside of the code snippet.

4. Avoid Outdated or Deprecated Methods

    - Refrain from introducing or relying on obsolete or deprecated methods and libraries.
    - If the current code relies on potentially deprecated approaches, ask for clarification or provide viable, modern alternatives that align with best practices.

5. Testing and Validation

    - Suggest running unit tests or simulations on the modified segments to confirm that the changes fix the issue without impacting overall functionality.
    - Ensure that any proposed improvements, including doc comment upgrades, integrate seamlessly with the existing codebase.
    - After all code modifications, navigate to the affected project directory and build C# then Angular to confirm the application compiles without errors:
		cd {PROJECT} && dotnet build {PROJECT}.csproj
		cd {PROJECT}/ClientApp && ng build
    - Run relevant unit tests if code changes affect core logic.
    - If the developer certificate is not trusted, then execute: dotnet dev-certs https --trust
    - To launch project use: dotnet watch run --project {PROJECT}/{PROJECT}.csproj --launch-profile "{PROJECT} (NG Build)"

6. Rationale and Explanation

    - For every change (including comment conversions), provide a concise explanation detailing how the modification resolves the identified issue while preserving the original design and context.
    - Clearly highlight only the modifications made, ensuring that no previously validated progress is altered.
    - NOTE: Summarize reasoning for the user, but do NOT expose full chain-of-thought. Keep internal deliberations internal; surface only the concise rationale needed to justify each change.

7. Contextual Analysis

    - Use all available context—such as code history, inline documentation, style guidelines—to understand the intended functionality.
    - When inspecting an existing file for understanding, prefer reading the whole file in a
      single `read_file` call when it comfortably fits in context; switch to targeted slices
      only when the file is too large, the tool truncates it, or a specific anchor line is
      already known.
    - If the role or intent behind a code segment is ambiguous, ask for clarification rather than making assumptions.

8. Targeted, Incremental Changes

    - Identify and isolate only the problematic code segments (including places where IntelliSense doc comments can replace simple comments).
    - Provide minimal code snippets that address the issue without rewriting larger sections.
    - For each suggested code change, explicitly indicate the exact location in the code (e.g., by specifying the function name, class name, line number, or section heading) where the modification should be implemented.

9. Preservation of Context

    - Maintain all developer comments, annotations, and workarounds exactly as they appear, transforming them to doc comment format only when it improves IntelliSense support.
    - Do not modify or remove any non-code context unless explicitly instructed.
    - Avoid introducing new, irrelevant comments in the code.

10. Launching {PROJECT} Correctly:
    - Navigate to the {PROJECT} project folder.
    - Run the following command to launch the project with live reload and proper debugging configuration:
      dotnet watch run --launch-profile "{PROJECT} (NG Build)" --project {PROJECT}/{PROJECT}.csproj
    - This command will start the {PROJECT} project on the designated debugging session URL.
    - Ensure that any previous {PROJECT} instances are terminated before running this command.
