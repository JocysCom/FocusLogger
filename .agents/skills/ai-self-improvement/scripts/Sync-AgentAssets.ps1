# Script: Sync-AgentAssets.ps1
# Location: .ai/skills/ai-self-improvement/scripts/Sync-AgentAssets.ps1
# Description:
#   Synchronises AI agent instruction files and skills from master sources under `.ai/`.
#   - Instructions: copies `*.instructions.md` from `.ai/` into agent-specific outputs.
#   - Skills: mirrors `.ai/skills/*` into agent skill folders (e.g. `.roo/skills/*`).
#
# Options for Mode:
#   ALL  - update all known agent outputs
#   AUTO - update only agents that exist in this repository (default usage)
#   Or a specific agent name: CLINE, ROO CODE, GitHub CoPilot, OpenAI Codex, Claude Code

param(
    [Parameter(Position = 0)]
    [string]$Mode,

    [switch]$NoClear
)

# Combine remaining args so Windows PowerShell (-File) invocations like:
#   Sync-AgentAssets.ps1 GitHub CoPilot
# work the same as:
#   Sync-AgentAssets.ps1 "GitHub CoPilot"
if ($args.Count -gt 0) {
    $ModeFromArgs = ($args -join ' ')
    if (-not $Mode -or $Mode -eq '') {
        $Mode = $ModeFromArgs
    }
}

# Allow calling via the old filename (if invoked through a copied/renamed script).
# This only affects displayed script name in prompts/logs.
$scriptName = [System.IO.Path]::GetFileName($MyInvocation.MyCommand.Path)

# Strict mode
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Ensure-Directory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -Path $Path -PathType Container)) {
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
    }
}

# Function to check if instruction files exist in a directory
function Test-HasInstructionFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [string]$Filter = '*instructions.md'
    )

    if (Test-Path $Path -PathType Container) {
        $files = @(Get-ChildItem $Path -Filter $Filter -File -ErrorAction SilentlyContinue)
        return ($files.Length -gt 0)
    }

    return $false
}

# Function to pause at the end (unless -NoWait is specified)
function Invoke-Pause {
    Write-Host "Pausing for 2 seconds..."
    Start-Sleep -Seconds 2
}

function Copy-FileIfDifferent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourcePath,
        [Parameter(Mandatory = $true)]
        [string]$TargetPath
    )

    $targetDir = Split-Path -Path $TargetPath -Parent
    Ensure-Directory -Path $targetDir

    if (-not (Test-Path -Path $TargetPath -PathType Leaf)) {
        Copy-Item -LiteralPath $SourcePath -Destination $TargetPath -Force
        $relative = $TargetPath.Substring($repoRoot.Length + 1)
        Write-Host "Created: $relative"
        return
    }

    $srcBytes = [System.IO.File]::ReadAllBytes($SourcePath)
    $dstBytes = [System.IO.File]::ReadAllBytes($TargetPath)

    if ($srcBytes.Length -eq $dstBytes.Length) {
        $same = $true
        for ($i = 0; $i -lt $srcBytes.Length; $i++) {
            if ($srcBytes[$i] -ne $dstBytes[$i]) { $same = $false; break }
        }

        if ($same) {
            $relative = $TargetPath.Substring($repoRoot.Length + 1)
            Write-Host "Up-to-date: $relative"
            return
        }
    }

    Copy-Item -LiteralPath $SourcePath -Destination $TargetPath -Force
    $relative = $TargetPath.Substring($repoRoot.Length + 1)
    Write-Host "Updated: $relative"
}

function Get-TextAuto {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    # .NET StreamReader detects BOM for UTF-8/UTF-16/UTF-32 automatically.
    $sr = New-Object System.IO.StreamReader($Path, $true)
    try {
        return $sr.ReadToEnd()
    }
    finally {
        $sr.Dispose()
    }
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $dir = Split-Path -Path $Path -Parent
    Ensure-Directory -Path $dir

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function Assert-InstructionSync {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourceDirectory,
        [Parameter(Mandatory = $true)]
        [string]$TargetDirectory,
        [Parameter(Mandatory = $true)]
        [System.IO.FileSystemInfo[]]$SourceFiles
    )

    $srcDir = Join-Path $repoRoot $SourceDirectory
    $dstDir = Join-Path $repoRoot $TargetDirectory

    foreach ($sourceFile in $SourceFiles) {
        $srcPath = Join-Path $srcDir $sourceFile.Name
        $dstPath = Join-Path $dstDir $sourceFile.Name

        if (-not (Test-Path $dstPath -PathType Leaf)) {
            throw "Binary comparison failed. Destination file missing: $dstPath"
        }

        $srcBytes = [System.IO.File]::ReadAllBytes($srcPath)
        $dstBytes = [System.IO.File]::ReadAllBytes($dstPath)

        if ($srcBytes.Length -ne $dstBytes.Length) {
            throw "Binary comparison failed. Source and target size mismatch in binary: Source: $srcPath Target: $dstPath"
        }

        for ($i = 0; $i -lt $srcBytes.Length; $i++) {
            if ($srcBytes[$i] -ne $dstBytes[$i]) {
                throw "Binary comparison failed. Source and target content mismatch in binary: Source: $srcPath Target: $dstPath"
            }
        }
    }
}

# Function to update agents that use multiple separate instruction files
function Update-MultipleFileAgent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$AgentName,
        [Parameter(Mandatory = $true)]
        [string]$TargetDirectory,
        [Parameter(Mandatory = $true)]
        [System.IO.FileSystemInfo[]]$SourceFiles,
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    Write-Host "`r`n--- Updating $AgentName Instructions ---"
    $targetDir = Join-Path $RepoRoot $TargetDirectory

    foreach ($sourceFile in $SourceFiles) {
        $targetFile = Join-Path $targetDir $sourceFile.Name
        Copy-FileIfDifferent -SourcePath $sourceFile.FullName -TargetPath $targetFile
    }

    Assert-InstructionSync -SourceDirectory ".ai" -TargetDirectory $TargetDirectory -SourceFiles $SourceFiles
}

# Function to update agents that use a single combined instruction file
function Update-SingleFileAgent {
    param(
        [Parameter(Mandatory = $true)]
        [string]$AgentName,
        [Parameter(Mandatory = $true)]
        [string]$TargetFilePath,
        [Parameter(Mandatory = $true)]
        [System.IO.FileSystemInfo[]]$SourceFiles,
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    Write-Host "`r`n--- Updating $AgentName Instructions ---"
    $targetFile = Join-Path $RepoRoot $TargetFilePath
    $relativeTarget = $targetFile.Substring($repoRoot.Length + 1)

    $allInstructionsContent = New-Object System.Text.StringBuilder
    $firstFile = $true

    foreach ($sourceFile in $SourceFiles) {
        $sourceContent = Get-TextAuto -Path $sourceFile.FullName

        if ([string]::IsNullOrWhiteSpace($sourceContent)) {
            Write-Warning "Skipping empty file: $($sourceFile.Name)"
            continue
        }

        if (-not $firstFile) {
            [void]$allInstructionsContent.AppendLine("")
        }

        [void]$allInstructionsContent.AppendLine("==== START OF INSTRUCTIONS FROM: $($sourceFile.Name) ====")
        [void]$allInstructionsContent.AppendLine("")

        [void]$allInstructionsContent.AppendLine("# Instructions from: $($sourceFile.Name)")
        [void]$allInstructionsContent.AppendLine("")

        [void]$allInstructionsContent.AppendLine($sourceContent.Trim())

        [void]$allInstructionsContent.AppendLine("")
        [void]$allInstructionsContent.AppendLine("==== END OF INSTRUCTIONS FROM: $($sourceFile.Name) ====")

        $firstFile = $false
    }

    $finalContent = $allInstructionsContent.ToString()

    $existing = if (Test-Path -Path $targetFile -PathType Leaf) { Get-TextAuto -Path $targetFile } else { $null }
    if ($null -ne $existing -and $existing -eq $finalContent) {
        Write-Host "Up-to-date: $relativeTarget"
        return
    }

    Write-Utf8NoBom -Path $targetFile -Content $finalContent
    Write-Host "Updated: $relativeTarget"
}

function Invoke-RoboCopyMirror {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourceDirectory,
        [Parameter(Mandatory = $true)]
        [string]$DestinationDirectory,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    if (-not (Test-Path $SourceDirectory -PathType Container)) {
        Write-Host "No skills folder found at: $SourceDirectory"
        return
    }

    Ensure-Directory -Path $DestinationDirectory

    Write-Host "`r`n--- Mirroring skills to $Label ---"
    Write-Host "Source:      $SourceDirectory"
    Write-Host "Destination: $DestinationDirectory"

    # /MIR      = mirror (copy + delete removed)
    # /FFT      = tolerate 2s timestamp granularity
    # /R:1 /W:1 = retry quickly
    # /NFL/NDL  = no file/dir listing (keep output compact)
    # /NJH/NJS  = no job header/summary
    # /NP       = no progress
    # /XD       = exclude version control/build dirs
    $excludedDirs = @('.git', '.vs', 'bin', 'obj')

    $args = @(
        $SourceDirectory,
        $DestinationDirectory,
        '/MIR',
        '/FFT',
        '/R:1',
        '/W:1',
        '/NFL',
        '/NDL',
        '/NJH',
        '/NJS',
        '/NP'
    )

    foreach ($d in $excludedDirs) {
        $args += '/XD'
        $args += $d
    }

    $exe = 'robocopy'
    # Do not echo the full robocopy command; it is noisy and can wrap in some terminals.
    Write-Host "robocopy <source> <destination> /MIR /NFL /NDL /NJH /NJS /NP ..."

    & $exe @args | Out-Null
    $exitCode = $LASTEXITCODE

    # Robocopy uses bitmask exit codes.
    # 0-7 are success with various flags; >= 8 indicates failure.
    if ($exitCode -ge 8) {
        throw "Robocopy failed with exit code $exitCode. Command: $cmd"
    }

    # IMPORTANT: robocopy returns 1+ for successful copies.
    # Ensure PowerShell script does not propagate a non-zero exit code for success cases.
    $global:LASTEXITCODE = 0

    Write-Host "Mirrored skills to $Label (robocopy exit code $exitCode)."
}

function Sync-SkillsToRoo {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $srcSkillsRoot = Join-Path $RepoRoot ".ai\skills"
    $rooSkillsRoot = Join-Path $RepoRoot ".roo\skills"

    Invoke-RoboCopyMirror -SourceDirectory $srcSkillsRoot -DestinationDirectory $rooSkillsRoot -Label "Roo (.roo\\skills)"
}

function Sync-SkillsToGitHub {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $srcSkillsRoot = Join-Path $RepoRoot ".ai\skills"
    $githubSkillsRoot = Join-Path $RepoRoot ".github\skills"

    Invoke-RoboCopyMirror -SourceDirectory $srcSkillsRoot -DestinationDirectory $githubSkillsRoot -Label "GitHub (.github\\skills)"
}

function Sync-SkillsToClaude {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $srcSkillsRoot = Join-Path $RepoRoot ".ai\skills"
    $claudeSkillsRoot = Join-Path $RepoRoot ".claude\skills"

    Invoke-RoboCopyMirror -SourceDirectory $srcSkillsRoot -DestinationDirectory $claudeSkillsRoot -Label "Claude Code (.claude\\skills)"
}

# --- Main Script ---
if (-not $NoClear) {
    Clear-Host
}

# We are located under `.ai/skills/<skill>/tools`. Find repo root by going up 4 levels.
$scriptDir = $PSScriptRoot
$repoRoot = (Join-Path -Path $scriptDir -ChildPath "..\..\..\.." | Resolve-Path).Path

# `.ai` folder path
$aiDir = Join-Path $repoRoot ".ai"

# Discover source files matching *instructions.md in the .ai folder
[System.IO.FileSystemInfo[]]$sourceInstructionFiles = Get-ChildItem -Path $aiDir -Filter "*instructions.md" -File | Sort-Object Name

if ($null -eq $sourceInstructionFiles -or $sourceInstructionFiles.Length -eq 0) {
    Write-Warning "No '*instructions.md' files found in '$aiDir'. Nothing to process."
    exit 0
}

Write-Host "Found the following source instruction files in '$aiDir':"
$sourceInstructionFiles | ForEach-Object { Write-Host "- $($_.Name)" }

# Mode parameter handling: if 'ALL' or 'AUTO', skip interactive prompt
if ($Mode -eq 'ALL') {
    Write-Host "Selected: ALL (parameter mode)"
    $updateCline = $true
    $updateCopilot = $true
    $updateRooCode = $true
    $updateCodex = $true
    $updateClaude = $true
}
elseif ($Mode -eq 'AUTO') {
    Write-Host "Selected: AUTO (parameter mode)"
    # Determine available agents based on instruction files
    $updateCline = Test-HasInstructionFiles -Path (Join-Path $repoRoot '.clinerules')
    $updateRooCode = Test-HasInstructionFiles -Path (Join-Path $repoRoot '.roo\rules')
    $updateCopilot = Test-Path (Join-Path $repoRoot '.github\copilot-instructions.md') -PathType Leaf
    $updateCodex = Test-Path (Join-Path $repoRoot 'AGENTS.md') -PathType Leaf
    $updateClaude = Test-HasInstructionFiles -Path (Join-Path $repoRoot '.claude')
    Write-Host "Agents to update based on available instruction files:"
    if ($updateCline) { Write-Host "- CLINE" }
    if ($updateRooCode) { Write-Host "- ROO CODE" }
    if ($updateCopilot) { Write-Host "- GitHub CoPilot" }
    if ($updateCodex) { Write-Host "- OpenAI Codex" }
    if ($updateClaude) { Write-Host "- Claude Code" }
}
elseif ($Mode -and $Mode -ne '') {
    # Specific agent mode (e.g., CLINE, "ROO CODE", etc.)
    $updateCline = ($Mode -eq 'CLINE')
    $updateCopilot = ($Mode -eq 'GitHub CoPilot')
    $updateRooCode = ($Mode -eq 'ROO CODE')
    $updateCodex = ($Mode -eq 'OpenAI Codex')
    $updateClaude = ($Mode -eq 'Claude Code')
    Write-Host "Selected: $Mode (parameter mode)"
}
else {
    # User prompt for agent selection
    # Detect available agents for interactive menu
    $hasCline = Test-HasInstructionFiles -Path (Join-Path $repoRoot '.clinerules')
    $hasRooCode = Test-HasInstructionFiles -Path (Join-Path $repoRoot '.roo\rules')
    $hasCopilot = Test-Path (Join-Path $repoRoot '.github\copilot-instructions.md') -PathType Leaf
    $hasCodex = Test-Path (Join-Path $repoRoot 'AGENTS.md') -PathType Leaf
    $hasClaude = Test-HasInstructionFiles -Path (Join-Path $repoRoot '.claude')

    Write-Host "`r`nDetected AI agents with instruction files:"
    if ($hasCline) { Write-Host "- CLINE" }
    if ($hasRooCode) { Write-Host "- ROO CODE" }
    if ($hasCopilot) { Write-Host "- GitHub CoPilot" }
    if ($hasCodex) { Write-Host "- OpenAI Codex" }
    if ($hasClaude) { Write-Host "- Claude Code" }

    Write-Host ""
    Write-Host "=============================================================="
    Write-Host "Select Agent Instruction Set to Update"
    Write-Host "--------------------------------------------------------------"
    Write-Host "1. AUTO           - Update only agents with instruction files (default)"
    Write-Host "2. ALL            - Update instructions for all AI agents"
    Write-Host "3. CLINE          - Update instructions for CLINE"
    Write-Host "4. ROO CODE       - Update instructions for ROO CODE"
    Write-Host "5. GitHub CoPilot - Update instructions for GitHub CoPilot"
    Write-Host "6. OpenAI Codex   - Update instructions for OpenAI Codex"
    Write-Host "7. Claude Code    - Update instructions for Claude Code"
    Write-Host "0. Exit"
    Write-Host "=============================================================="
    $selection = Read-Host "Enter the number of your choice (0-7)"

    # Initialize flags
    $updateCline = $false
    $updateCopilot = $false
    $updateRooCode = $false
    $updateCodex = $false
    $updateClaude = $false

    switch ($selection) {
        '1' {
            $updateCline = Test-HasInstructionFiles -Path (Join-Path $repoRoot '.clinerules')
            $updateRooCode = Test-HasInstructionFiles -Path (Join-Path $repoRoot '.roo\rules')
            $updateCopilot = Test-Path (Join-Path $repoRoot '.github\copilot-instructions.md') -PathType Leaf
            $updateCodex = Test-Path (Join-Path $repoRoot 'AGENTS.md') -PathType Leaf
            $updateClaude = Test-HasInstructionFiles -Path (Join-Path $repoRoot '.claude')
            Write-Host "Selected: AUTO"
        }
        '2' {
            $updateCline = $true
            $updateCopilot = $true
            $updateRooCode = $true
            $updateCodex = $true
            $updateClaude = $true
            Write-Host "Selected: ALL"
        }
        '3' { $updateCline = $true; Write-Host "Selected: CLINE" }
        '4' { $updateRooCode = $true; Write-Host "Selected: ROO CODE" }
        '5' { $updateCopilot = $true; Write-Host "Selected: GitHub CoPilot" }
        '6' { $updateCodex = $true; Write-Host "Selected: OpenAI Codex" }
        '7' { $updateClaude = $true; Write-Host "Selected: Claude Code" }
        '0' { Write-Host "Operation cancelled by user."; exit 0 }
        default { throw "Invalid selection. Exiting." }
    }
}

# --- Multiple-File Agent Updates ---
if ($updateCline) {
    Update-MultipleFileAgent -AgentName "CLINE" -TargetDirectory ".clinerules" -SourceFiles $sourceInstructionFiles -RepoRoot $repoRoot
}

if ($updateRooCode) {
    Update-MultipleFileAgent -AgentName "ROO CODE" -TargetDirectory ".roo\rules" -SourceFiles $sourceInstructionFiles -RepoRoot $repoRoot
}

# --- Single-File Agent Updates ---
if ($updateCopilot) {
    $copilotTarget = ".github\copilot-instructions.md"
    $githubInstructionsDir = Join-Path $repoRoot ".github\instructions"

    if (Test-Path $githubInstructionsDir -PathType Container) {
        Write-Host "`r`n--- Updating GitHub CoPilot Instructions (folder-based) ---"

        $mainName = "instructions.md"
        $mainSource = $sourceInstructionFiles | Where-Object { $_.Name -ieq $mainName } | Select-Object -First 1
        if ($null -eq $mainSource) {
            throw "Expected source '$mainName' under .ai but none found."
        }

        Copy-FileIfDifferent -SourcePath $mainSource.FullName -TargetPath (Join-Path $repoRoot $copilotTarget)

        foreach ($sf in $sourceInstructionFiles) {
            if ($sf.Name -ieq $mainName) {
                continue
            }

            $destination = Join-Path $githubInstructionsDir $sf.Name
            Copy-FileIfDifferent -SourcePath $sf.FullName -TargetPath $destination
        }
    }
    else {
        Update-SingleFileAgent -AgentName "GitHub CoPilot" -TargetFilePath $copilotTarget -SourceFiles $sourceInstructionFiles -RepoRoot $repoRoot
    }
}

if ($updateCodex) {
    Update-SingleFileAgent -AgentName "OpenAI Codex" -TargetFilePath "AGENTS.md" -SourceFiles $sourceInstructionFiles -RepoRoot $repoRoot
}

# --- Claude Code (multiple-file agent) ---
if ($updateClaude) {
    Update-MultipleFileAgent -AgentName "Claude Code" -TargetDirectory ".claude" -SourceFiles $sourceInstructionFiles -RepoRoot $repoRoot
}

# --- Skills mirroring ---
if ($updateRooCode -or $Mode -eq 'ALL' -or $Mode -eq 'AUTO') {
    Sync-SkillsToRoo -RepoRoot $repoRoot
}

# GitHub Copilot: mirror skills to `.github/skills` (Copilot tries to load from there).
if ($updateCopilot -or $Mode -eq 'ALL' -or $Mode -eq 'AUTO') {
    Sync-SkillsToGitHub -RepoRoot $repoRoot
}

# Claude Code: mirror skills to `.claude/skills`.
if ($updateClaude -or $Mode -eq 'ALL' -or $Mode -eq 'AUTO') {
    Sync-SkillsToClaude -RepoRoot $repoRoot
}

Write-Host "`r`nAll selected operations completed successfully."

# Only pause when launched by double-click (Explorer). In CI / terminal usage, do not pause.
if ($Host.Name -and $Host.Name -notlike '*ConsoleHost*') {
    Invoke-Pause
}
