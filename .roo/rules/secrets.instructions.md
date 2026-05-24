# Secret Handling Rules

## Never Read `.env` Files

Do NOT read, open, cat, or display `.env`, `.env.local`, `.env.keys`, or any dotenv file.
These files may contain plaintext secrets. Use `envManage.py` for all management operations.

## Never Execute Commands to Retrieve or Inspect Secret Values

Do NOT run terminal commands to read, print, or inspect secret values — not even masked ones.
This includes commands like `$env:OPENAI_API_KEY`, `echo $env:VAR`, `[Environment]::GetEnvironmentVariable(...)`, or any expression that would output a secret value into the terminal or a file.

## How Scripts and Code Must Reference Secrets

After `python envManage.py load`, secrets live in User/Process scope (Windows).
When **writing scripts or code**, reference secrets via `$env:VAR_NAME` / `[System.Environment]::GetEnvironmentVariable('VAR_NAME')` (PowerShell) or `os.environ['VAR_NAME']` (Python) — these expressions belong in code that passes secrets to APIs or tools, not in commands the AI runs itself.

## Never Log or Write Secret Values

Never include secret values in: log files, scripts, configs, docs, or git commits.

## Checking Whether a Variable Is Set (in Scripts)

```powershell
# Correct — test presence only, never log or compare the value itself
if (-not [string]::IsNullOrEmpty($env:OPENAI_API_KEY)) { ... }
```

To report back to the user whether a variable is set, say: "`OPENAI_API_KEY` is set (length: N)" — obtain the length via `$env:OPENAI_API_KEY.Length`, do not print the value.

## Script Pattern for Masked Display

Scripts (not the AI) may display a masked value to confirm a secret was loaded correctly.
Use the last few characters only — never the full value:

- Long secrets (name contains `KEY`, `TOKEN`, `PASS`, `CODE`, or `SECRET`, and value length > 32): **last 4 chars**
- All others: **last 2 chars**
- Empty values: show nothing

```powershell
function Get-MaskedValue([string]$Name, [string]$Value) {
    if ([string]::IsNullOrEmpty($Value)) { return '' }
    $isLongSecret = ($Name -match '(KEY|TOKEN|PASS|CODE|SECRET)') -and ($Value.Length -gt 32)
    $tailLen = if ($isLongSecret) { 4 } else { 2 }
    if ($Value.Length -le $tailLen) { return '****' }
    return '****' + $Value.Substring($Value.Length - $tailLen)
}

# Used inside scripts (e.g. Import-EnvFileVariables), not run by the AI directly:
Write-Host "OPENAI_API_KEY=$(Get-MaskedValue 'OPENAI_API_KEY' $env:OPENAI_API_KEY)"
# Output: OPENAI_API_KEY=****a3f9
```

## File Reference

| File | Purpose | Commit? |
|------|---------|---------|
| `.env` | Encrypted secrets (dotenvx) | Yes (encrypted only) |
| `.env.example` | Template with empty values | Yes |
| `.env.keys` | Decryption private key | **Never** |

## Managing Secrets

```
python envManage.py install      # install dotenvx
python envManage.py encrypt      # encrypt before committing
python envManage.py decrypt      # decrypt for local editing
python envManage.py load         # load into User + Process scope (Windows)
python envManage.py unload       # remove from User + Process scope (Windows)
python envManage.py list         # list variable names grouped by section
python envManage.py set-key -Group OpenAI -Key OPENAI_API_KEY
                                 # prompts for value via masked terminal input
python envManage.py remove-key -Key OPENAI_API_KEY
```

`set-key` and `remove-key` automatically refresh `.env.example` via `dotenvx ext genexample`.
