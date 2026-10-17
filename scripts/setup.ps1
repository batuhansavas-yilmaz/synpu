$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$identity = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $identity.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Bu betik yonetici olarak calistirilmalidir. setup.bat dosyasini cift tiklayin." -ForegroundColor Red
    exit 1
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "== Synpu kurulumu ==" -ForegroundColor Cyan

# 1) uv
$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) { $uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe" }
if (-not (Test-Path $uv)) {
    Write-Host "uv indirilip kuruluyor..."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
}
if (-not (Test-Path $uv)) {
    Write-Host "uv kurulamadi." -ForegroundColor Red
    exit 1
}
Write-Host "uv: $uv"

# 2) Python 3.12 + bagimliliklar
Write-Host "Python 3.12 denetleniyor..."
& $uv python install 3.12
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python kurulumu basarisiz (uv exit $LASTEXITCODE)." -ForegroundColor Red
    exit 1
}
Write-Host "Bagimliliklar kuruluyor..."
& $uv sync
if ($LASTEXITCODE -ne 0) {
    Write-Host "Bagimlilik kurulumu basarisiz (uv exit $LASTEXITCODE)." -ForegroundColor Red
    exit 1
}

# 3) PresentMon
$pmExe = Join-Path $RepoRoot "third_party\presentmon\PresentMon.exe"
if (-not (Test-Path $pmExe)) {
    Write-Host "PresentMon indiriliyor..."
    New-Item -ItemType Directory -Force -Path (Split-Path $pmExe) | Out-Null
    try {
        $tmp = Join-Path $env:TEMP "PresentMon-2.6.0-x64.exe"
        Invoke-WebRequest -Uri "https://github.com/GameTechDev/PresentMon/releases/download/v2.6.0/PresentMon-2.6.0-x64.exe" -OutFile $tmp
        Move-Item -Force $tmp $pmExe
    } catch {
        Write-Host "PresentMon indirilemedi: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "PresentMon zaten var."
}

# 4) LibreHardwareMonitor
$lhmDll = Join-Path $RepoRoot "third_party\lhm\LibreHardwareMonitorLib.dll"
if (-not (Test-Path $lhmDll)) {
    Write-Host "LibreHardwareMonitor indiriliyor..."
    New-Item -ItemType Directory -Force -Path (Split-Path $lhmDll) | Out-Null
    try {
        $zip = Join-Path $env:TEMP "LibreHardwareMonitor.zip"
        Invoke-WebRequest -Uri "https://github.com/LibreHardwareMonitor/LibreHardwareMonitor/releases/download/v0.9.6/LibreHardwareMonitor.zip" -OutFile $zip
        Expand-Archive -Path $zip -DestinationPath (Split-Path $lhmDll) -Force
        Remove-Item $zip -ErrorAction SilentlyContinue
    } catch {
        Write-Host "LibreHardwareMonitor indirilemedi: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "LibreHardwareMonitor zaten var."
}

# 5) Guvenlik duvari kurali
& (Join-Path $PSScriptRoot "firewall.ps1")

# 6) Zamanlanmis gorev
& (Join-Path $PSScriptRoot "install_task.ps1")

Write-Host ""
Write-Host "Kurulum tamamlandi. Synpu baslatildi." -ForegroundColor Green
Write-Host "Telefonla baglanmak icin PC'de acilan penceredeki QR kodu okutun."
exit 0
