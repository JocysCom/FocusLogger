Import-Module "d:\_Backup\Configuration\SSL\Tools\app_signModule.ps1" -Force

[string[]]$appFiles = @(
    "..\bin\Release\publish\JocysCom.FocusLogger.exe",
)
[string]$appName = "Jocys.com Focus Logger"
[string]$appLink = "https://www.jocys.com"

ProcessFiles $appName $appLink $appFiles
pause