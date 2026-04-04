<#
.SYNOPSIS
    Thin wrapper that calls the original MakeLinks.ps1 from the Core library.
    Place this file in external JocysCom folders instead of duplicating the full script.
#>
$paths = @(
    "d:\Projects\Jocys.com\ClassLibrary\Core\_Resources\MakeLinks.ps1",
    "c:\Projects\Jocys.com\ClassLibrary\Core\_Resources\MakeLinks.ps1"
);
foreach ($p in $paths) {
    if (Test-Path $p) { & $p; return; }
}
Write-Host "ERROR: MakeLinks.ps1 not found in any known location." -ForegroundColor Red;
