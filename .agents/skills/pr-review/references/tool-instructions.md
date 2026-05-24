## Tools

## Environment

Scripts are Python 3.9+ and run cross-platform (Windows, macOS, Linux). Always invoke scripts from the repository root using `python`.

### Script Invocation Rules

Scripts must be invoked directly with `python` (or `python3` on systems where that is the default). Do not use shell-specific wrappers or indirect execution.

Examples:

```bash
# VALID (direct invocation)
python .ai/skills/pr-review/scripts/s01_reset_workspace.py
python .ai/skills/pr-review/scripts/s06_export_diff_artifacts.py --detect-renames

# VALID (with arguments)
python .ai/skills/pr-review/scripts/s02_get_azure_devops_info.py --pat "$AZDO_PAT"

# WRONG (do not use shell wrappers)
bash -c "python .ai/skills/pr-review/scripts/s01_reset_workspace.py"
```

### Dependencies

Install required Python packages before first use:

```bash
pip install -r .ai/skills/pr-review/scripts/requirements.txt
```

### Platform-Specific Notes

- **Windows**: The `Setup_Util_TrustedRootCertificates_Save.ps1` script is kept for corporate proxy/certificate environments. API scripts (s02, s03, s09, s10, s11) will automatically invoke it when running on Windows if present.
- **Linux/macOS**: Certificate trust is managed by the OS. No additional steps needed.
