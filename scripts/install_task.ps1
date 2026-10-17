$ErrorActionPreference = "Stop"
$InstallRoot = Split-Path -Parent $PSScriptRoot
$pythonw = Join-Path $InstallRoot ".venv\Scripts\pythonw.exe"
$vbs = Join-Path $InstallRoot "scripts\launch.vbs"
$icon = Join-Path $InstallRoot "static\icon.ico"
if (-not (Test-Path $pythonw)) {
    Write-Host "pythonw.exe bulunamadi - once setup.ps1 calistirin." -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $vbs)) {
    Write-Host "launch.vbs bulunamadi." -ForegroundColor Red
    exit 1
}
try {
    Stop-ScheduledTask -TaskName "Synpu" -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    $action = New-ScheduledTaskAction -Execute $pythonw -Argument "-m synpu" -WorkingDirectory $InstallRoot
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName "Synpu" -Action $action -Settings $settings -RunLevel Highest -Force | Out-Null

    $shell = New-Object -ComObject WScript.Shell
    $desktop = [Environment]::GetFolderPath("Desktop")
    $desktopShortcut = $shell.CreateShortcut((Join-Path $desktop "Synpu.lnk"))
    $desktopShortcut.TargetPath = Join-Path $env:SystemRoot "System32\wscript.exe"
    $desktopShortcut.Arguments = "`"$vbs`" show"
    $desktopShortcut.WorkingDirectory = $InstallRoot
    $desktopShortcut.IconLocation = $icon
    $desktopShortcut.Description = "Synpu - Telefonla Baglan"
    $desktopShortcut.Save()

    $startup = [Environment]::GetFolderPath("Startup")
    $startupShortcut = $shell.CreateShortcut((Join-Path $startup "Synpu.lnk"))
    $startupShortcut.TargetPath = Join-Path $env:SystemRoot "System32\wscript.exe"
    $startupShortcut.Arguments = "`"$vbs`""
    $startupShortcut.WorkingDirectory = $InstallRoot
    $startupShortcut.IconLocation = $icon
    $startupShortcut.Description = "Synpu"
    $startupShortcut.Save()

    Start-ScheduledTask -TaskName "Synpu"
    Start-Sleep -Seconds 2
    $task = Get-ScheduledTask -TaskName "Synpu" -ErrorAction Stop
    if (-not $task) { throw "Gorev kaydi bulunamadi" }
    Write-Host "Gorev, masaustu ve baslangic kisayollari hazir: Synpu"
} catch {
    Write-Host "Gorev kurulamadi: $_" -ForegroundColor Red
    exit 1
}
exit 0
