$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$pythonw = Join-Path $RepoRoot ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $pythonw)) {
    Write-Host "pythonw.exe bulunamadi - once setup.ps1 calistirin." -ForegroundColor Red
    exit 1
}
try {
    Stop-ScheduledTask -TaskName "Synpu" -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    $action = New-ScheduledTaskAction -Execute $pythonw -Argument "-m synpu" -WorkingDirectory $RepoRoot
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName "Synpu" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force | Out-Null
    Start-ScheduledTask -TaskName "Synpu"
    Start-Sleep -Seconds 2
    $task = Get-ScheduledTask -TaskName "Synpu" -ErrorAction Stop
    if (-not $task) { throw "Gorev kaydi bulunamadi" }
    Write-Host "Zamanlanmis gorev hazir ve baslatildi: Synpu"
} catch {
    Write-Host "Zamanlanmis gorev kurulamadi: $_" -ForegroundColor Red
    exit 1
}
exit 0
