$ErrorActionPreference = "Stop"
$port = if ($env:SYNPU_PORT) { [int]$env:SYNPU_PORT } else { 8787 }
$ruleName = "Synpu (TCP $port)"
try {
    if (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue) {
        Write-Host "Guvenlik duvari kurali zaten var: $ruleName"
    } else {
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $port -Profile Private | Out-Null
        Write-Host "Guvenlik duvari kurali eklendi: $ruleName"
    }
    if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
        throw "Kural dogrulanamadi"
    }
} catch {
    Write-Host "Guvenlik duvari kurali eklenemedi: $_" -ForegroundColor Red
    exit 1
}
exit 0
