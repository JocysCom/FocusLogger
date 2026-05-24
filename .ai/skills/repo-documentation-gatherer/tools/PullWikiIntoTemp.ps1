#Requires -Version 5.1

<###############################################
PullWikiIntoTemp.ps1

Clones (or updates) the repository wiki into a temp folder inside the current code repo.

- Uses HTTPS and the developer's existing Git Credential Manager auth.
- Derives the wiki repo URL from the current repo remote URL.
- Targets: .ai/Temp/wiki

Provider notes:
- Azure DevOps wikis are typically project-level repos named: {ProjectName}.wiki
- GitHub wikis are typically repos named: {RepoName}.wiki

Notes:
- The script always deletes the target folder first to keep a clean snapshot.
###############################################>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$TargetDirectory = ".ai/Temp/wiki"
# For reliability, always start from a clean snapshot.
if (Test-Path -LiteralPath $TargetDirectory) {
    Write-Host "Removing existing wiki snapshot: $TargetDirectory"
    Remove-Item -LiteralPath $TargetDirectory -Recurse -Force
}

function Get-CodeRepoRemoteUrl {
    $remote = (& git remote get-url origin 2>$null)
    if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($remote)) {
        return $remote.Trim()
    }

    # Fallback (rare): parse .git/config
    $configPath = Join-Path -Path ".git" -ChildPath "config"
    if (Test-Path -LiteralPath $configPath) {
        $content = Get-Content -LiteralPath $configPath -Raw

        # Prefer the 'origin' remote if present.
        $originBlock = [regex]::Match(
            $content,
            '(?ims)^\s*\[remote\s+"origin"\]\s*(?<body>.*?)(?=^\s*\[|\z)'
        )

        if ($originBlock.Success) {
            $originUrl = [regex]::Match($originBlock.Groups['body'].Value, "(?im)^\s*url\s*=\s*(?<url>.+?)\s*$")
            if ($originUrl.Success) {
                return $originUrl.Groups['url'].Value.Trim()
            }
        }

        # Fallback: first URL found.
        $anyUrl = [regex]::Match($content, "(?im)^\s*url\s*=\s*(?<url>.+?)\s*$")
        if ($anyUrl.Success) {
            return $anyUrl.Groups['url'].Value.Trim()
        }
    }

    throw "Unable to determine repo remote URL. Ensure git is available and origin remote is configured."
}

function Get-AzureDevOpsWikiRemoteUrl {
    param(
        [Parameter(Mandatory = $true)]
        [string] $CodeRemoteUrl
    )

    # Match: https://{org}@dev.azure.com/{org}/{project}/_git/{RepoName}
    if ($CodeRemoteUrl -match "(?i)^https?://(?:[^@/]+@)?dev\.azure\.com/(?<org>[^/]+)/(?<project>[^/]+)/_git/(?<repo>[^/?#]+)$") {
        $org = $Matches['org']
        $project = $Matches['project']
        $repo = $Matches['repo']

        # If user already pointed origin at a *.wiki repo, use it.
        if ($repo -match "(?i)\.wiki$") {
            return "https://dev.azure.com/$org/$project/_git/$repo"
        }

        # Azure DevOps wiki is project-level: {ProjectName}.wiki
        return "https://dev.azure.com/$org/$project/_git/$project.wiki"
    }

    return $null
}

function Get-GitHubWikiRemoteUrl {
    param(
        [Parameter(Mandatory = $true)]
        [string] $CodeRemoteUrl
    )

    # Typical: https://github.com/{owner}/{repo}.git
    if ($CodeRemoteUrl -match "(?i)^https?://[^/]+/(?<owner>[^/]+)/(?<repo>[^/?#]+?)(?:\.git)?$") {
        $owner = $Matches['owner']
        $repo = $Matches['repo']

        if ($repo -match "(?i)\.wiki$") {
            return $CodeRemoteUrl
        }

        # Keep host and owner, convert repo -> repo.wiki.git
        $hostAndOwner = ($CodeRemoteUrl -replace "(?i)/[^/?#]+(?:\.git)?$", "/$owner")
        return "$hostAndOwner/$repo.wiki.git"
    }

    return $null
}

function Get-WikiRemoteUrl {
    param(
        [Parameter(Mandatory = $true)]
        [string] $CodeRemoteUrl
    )

    $ado = Get-AzureDevOpsWikiRemoteUrl -CodeRemoteUrl $CodeRemoteUrl
    if (-not [string]::IsNullOrWhiteSpace($ado)) {
        return $ado
    }

    $gh = Get-GitHubWikiRemoteUrl -CodeRemoteUrl $CodeRemoteUrl
    if (-not [string]::IsNullOrWhiteSpace($gh)) {
        return $gh
    }

    throw "Unable to derive wiki remote URL from: '$CodeRemoteUrl'"
}

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $Args,

        [Parameter(Mandatory = $false)]
        [string] $WorkingDirectory
    )

    if ([string]::IsNullOrWhiteSpace($WorkingDirectory)) {
        & git @Args
    }
    else {
        & git -C $WorkingDirectory @Args
    }

    if ($LASTEXITCODE -ne 0) {
        throw "git command failed: git $($Args -join ' ')"
    }
}

$codeRemote = Get-CodeRepoRemoteUrl
$wikiRemote = Get-WikiRemoteUrl -CodeRemoteUrl $codeRemote

Write-Host "Code remote: $codeRemote"
Write-Host "Wiki remote: $wikiRemote"

if (-not (Test-Path -LiteralPath $TargetDirectory)) {
    $parent = Split-Path -Parent $TargetDirectory
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    Write-Host "Cloning wiki into: $TargetDirectory"
    Invoke-Git -Args @('clone', '--depth', '1', $wikiRemote, $TargetDirectory)
}
else {
    Write-Host "Updating existing wiki clone in: $TargetDirectory"
    Invoke-Git -Args @('fetch', '--prune') -WorkingDirectory $TargetDirectory
    Invoke-Git -Args @('pull') -WorkingDirectory $TargetDirectory
}

# Intentionally do not force a branch checkout.
# Wiki repositories may have different default branch names.

Write-Host "Wiki is available at: $TargetDirectory"
