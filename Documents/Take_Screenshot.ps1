# Take_Screenshot.ps1
# Launches FocusLogger, Notepad, and Explorer, switches between them
# to generate focus log entries, then captures a screenshot using PrintWindow.
#
# Usage: Right-click > Run with PowerShell, or run from terminal:
#   powershell -ExecutionPolicy Bypass -File Take_Screenshot.ps1

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Load C# helper class (supports re-running in the same session).
$csFilePath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "Take_Screenshot.ps1.cs"
$csFileContent = Get-Content -Path $csFilePath -Raw
$fileHash = Get-FileHash -InputStream ([System.IO.MemoryStream]::new([System.Text.Encoding]::UTF8.GetBytes($csFileContent))) -Algorithm SHA256
$className = "TakeScreenshot"
if (-not $script:loadedClasses) { $script:loadedClasses = @{} }
if (-not $script:loadedClasses.ContainsKey($fileHash.Hash)) {
    $className += (Get-Date -Format "yyyyMMddHHmmss")
    $csCode = $csFileContent -replace "TakeScreenshot", $className
    Add-Type -TypeDefinition $csCode -ReferencedAssemblies System.Windows.Forms, System.Drawing
    $script:loadedClasses[$fileHash.Hash] = $className
} else {
    $className = $script:loadedClasses[$fileHash.Hash]
}
$helper = [Type]$className

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$screenshotPath = Join-Path $scriptDir "Images\JocysCom.FocusLogger.png"
$tempFile = Join-Path $env:TEMP "My Document.txt"

# Find FocusLogger executable.
$appPath = Join-Path $scriptDir "..\FocusLogger\bin\Debug\net8.0-windows\JocysCom.FocusLogger.exe"
if (-not (Test-Path $appPath)) {
    $appPath = Join-Path $scriptDir "..\FocusLogger\bin\Release\net8.0-windows\JocysCom.FocusLogger.exe"
}
if (-not (Test-Path $appPath)) {
    Write-Error "FocusLogger not found. Build the project first."
    exit 1
}
$appPath = Resolve-Path $appPath

$focusLogger = $null
$notepad = $null
$explorerProc = $null

try {
    # 1. Start FocusLogger (centered).
    Write-Host "1. Starting FocusLogger..."
    $focusLogger = Start-Process -FilePath $appPath -PassThru
    Start-Sleep -Seconds 2
    $focusLogger.Refresh()
    $flHwnd = $focusLogger.MainWindowHandle
    $helper::CenterAndResize($flHwnd, 920, 480)
    Start-Sleep -Milliseconds 500

    # 2. Start Notepad with a document.
    Write-Host "2. Starting Notepad..."
    "Sample document for Focus Logger screenshot." | Out-File -FilePath $tempFile -Encoding UTF8
    $notepadPidsBefore = @(Get-Process -Name "Notepad" -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    Start-Process -FilePath "notepad.exe" -ArgumentList "`"$tempFile`""
    Start-Sleep -Seconds 2
    $notepad = Get-Process -Name "Notepad" -ErrorAction SilentlyContinue |
        Where-Object { $notepadPidsBefore -notcontains $_.Id -and $_.MainWindowHandle -ne [IntPtr]::Zero } |
        Select-Object -First 1
    if (-not $notepad) {
        $notepad = Get-Process -Name "Notepad" -ErrorAction SilentlyContinue |
            Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero } |
            Select-Object -First 1
    }
    $npHwnd = if ($notepad) { $notepad.MainWindowHandle } else { [IntPtr]::Zero }
    if ($npHwnd -ne [IntPtr]::Zero) {
        $helper::CenterAndResize($npHwnd, 1040, 680, -50)
        $helper::SetForegroundWindow($npHwnd) | Out-Null
        Start-Sleep -Milliseconds 500
    }

    # 3. Start Explorer.
    Write-Host "3. Starting Explorer..."
    $explorerHwndsBefore = @(Get-Process explorer -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero } |
        ForEach-Object { $_.MainWindowHandle })
    Start-Process "explorer.exe" -ArgumentList "C:\Windows"
    Start-Sleep -Seconds 2
    $explorerProc = Get-Process explorer -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero -and $explorerHwndsBefore -notcontains $_.MainWindowHandle } |
        Select-Object -First 1
    if (-not $explorerProc) {
        $explorerProc = Get-Process explorer -ErrorAction SilentlyContinue |
            Where-Object { $_.MainWindowTitle -match "Windows" -and $_.MainWindowHandle -ne [IntPtr]::Zero } |
            Select-Object -First 1
    }
    $exHwnd = if ($explorerProc) { $explorerProc.MainWindowHandle } else { [IntPtr]::Zero }
    if ($exHwnd -ne [IntPtr]::Zero) {
        $helper::CenterAndResize($exHwnd, 700, 400)
        $helper::SetForegroundWindow($exHwnd) | Out-Null
        Start-Sleep -Milliseconds 500
    }

    # 4. Switch focus between windows to generate log entries.
    Write-Host "4. Switching focus..."
    if ($npHwnd -ne [IntPtr]::Zero) { $helper::SetForegroundWindow($npHwnd) | Out-Null; Start-Sleep -Milliseconds 800 }
    if ($exHwnd -ne [IntPtr]::Zero) { $helper::SetForegroundWindow($exHwnd) | Out-Null; Start-Sleep -Milliseconds 800 }
    if ($npHwnd -ne [IntPtr]::Zero) { $helper::SetForegroundWindow($npHwnd) | Out-Null; Start-Sleep -Milliseconds 800 }
    if ($exHwnd -ne [IntPtr]::Zero) { $helper::SetForegroundWindow($exHwnd) | Out-Null; Start-Sleep -Milliseconds 800 }
    if ($npHwnd -ne [IntPtr]::Zero) { $helper::SetForegroundWindow($npHwnd) | Out-Null; Start-Sleep -Milliseconds 800 }

    # 5. Move Notepad behind FocusLogger as white background, then capture.
    Write-Host "5. Taking screenshot..."
    if ($npHwnd -ne [IntPtr]::Zero) {
        $helper::CenterAndResize($npHwnd, 1040, 680, -50)
        $helper::SetForegroundWindow($npHwnd) | Out-Null
        Start-Sleep -Milliseconds 300
    }
    $helper::SetForegroundWindow($flHwnd) | Out-Null
    Start-Sleep -Seconds 1
    $helper::CaptureWindow($flHwnd, $screenshotPath)
    Write-Host "   Screenshot saved to: $screenshotPath"

} finally {
    Write-Host "6. Cleaning up..."
    if ($notepad -and -not $notepad.HasExited) { $notepad.Kill(); $notepad.WaitForExit(3000) | Out-Null }
    if ($focusLogger -and -not $focusLogger.HasExited) { $focusLogger.Kill(); $focusLogger.WaitForExit(3000) | Out-Null }
    if ($explorerProc -and -not $explorerProc.HasExited) { $explorerProc.CloseMainWindow() | Out-Null }
    Start-Sleep -Milliseconds 500
    Remove-Item $tempFile -ErrorAction SilentlyContinue
    Write-Host "Done."
}
