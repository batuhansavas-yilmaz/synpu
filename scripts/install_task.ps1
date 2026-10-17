$RepoRoot = Split-Path -Parent $PSScriptRoot
$pythonw = Join-Path $RepoRoot ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $pythonw)) {
    Write-Host "pythonw.exe bulunamadi - once setup.ps1 calistirin." -ForegroundColor Red
    exit 1
}
$action = New-ScheduledTaskAction -Execute $pythonw -Argument "-m synpu" -WorkingDirectory $RepoRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
Register-ScheduledTask -TaskName "Synpu" -Action $action -Trigger $trigger -RunLevel Highest -Force | Out-Null
Start-ScheduledTask -TaskName "Synpu"
Write-Host "Zamanlanmis gorev hazir ve baslatildi: Synpu"
