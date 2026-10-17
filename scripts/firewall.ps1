$ruleName = "Synpu (TCP 8787)"
if (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue) {
    Write-Host "Guvenlik duvari kurali zaten var: $ruleName"
} else {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8787 -Profile Private | Out-Null
    Write-Host "Guvenlik duvari kurali eklendi: $ruleName"
}
