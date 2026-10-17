$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$identity = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $identity.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Bu betik yonetici olarak calistirilmalidir." -ForegroundColor Red
    exit 1
}

$SourceRoot = Split-Path -Parent $PSScriptRoot
$InstallRoot = Join-Path $env:LOCALAPPDATA "Synpu\app"

if ($SourceRoot.TrimEnd("\") -ne $InstallRoot.TrimEnd("\")) {
    Write-Host "Dosyalar kurulum klasorune kopyalaniyor: $InstallRoot"
    New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
    $exclude = @(".venv", "third_party", ".git", ".superpowers", "__pycache__", ".pytest_cache", "dist")
    robocopy $SourceRoot $InstallRoot /E /NFL /NDL /NJH /NJS /XD $exclude /XF *.pyc | Out-Null
    if ($LASTEXITCODE -ge 8) {
        Write-Host "Dosya kopyalama basarisiz (robocopy $LASTEXITCODE)." -ForegroundColor Red
        exit 1
    }
    $LASTEXITCODE = 0
    $licenseDir = Join-Path $InstallRoot "third_party"
    New-Item -ItemType Directory -Force -Path $licenseDir | Out-Null
    Get-ChildItem (Join-Path $SourceRoot "third_party") -Filter *.txt -ErrorAction SilentlyContinue | Copy-Item -Destination $licenseDir -Force
}
Set-Location $InstallRoot

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

# 3) PawnIO (LibreHardwareMonitor sensor surucusu)
$pawnio = Get-Service -Name "PawnIO" -ErrorAction SilentlyContinue
$pawnioLib = Join-Path $env:ProgramFiles "PawnIO\PawnIOLib.dll"
if ($pawnio -and -not (Test-Path $pawnioLib)) {
    Write-Host "PawnIO servisi eksik/bozuk, temizleniyor..."
    Stop-Service -Name "PawnIO" -Force -ErrorAction SilentlyContinue
    & sc.exe delete PawnIO | Out-Null
    Start-Sleep -Seconds 1
    $pawnio = $null
}
if (-not $pawnio) {
    Write-Host "PawnIO surucusu indiriliyor..."
    try {
        $pawnExe = Join-Path $env:TEMP "PawnIO_setup.exe"
        Invoke-WebRequest -Uri "https://github.com/namazso/PawnIO.Setup/releases/download/2.2.0/PawnIO_setup.exe" -OutFile $pawnExe
        $hash = (Get-FileHash -Path $pawnExe -Algorithm SHA256).Hash.ToLower()
        if ($hash -ne "1f519a22e47187f70a1379a48ca604981c4fcf694f4e65b734aaa74a9fba3032") {
            throw "SHA256 dogrulamasi basarisiz"
        }
        $proc = Start-Process -FilePath $pawnExe -ArgumentList "-install", "-silent" -Wait -PassThru
        Remove-Item $pawnExe -ErrorAction SilentlyContinue
        if ($proc.ExitCode -ne 0 -and $proc.ExitCode -ne 3010) {
            throw "Kurulum exit kodu: $($proc.ExitCode)"
        }
        Start-Sleep -Seconds 2
        if (-not (Get-Service -Name "PawnIO" -ErrorAction SilentlyContinue)) {
            throw "PawnIO servisi olusmadi"
        }
        if (-not (Test-Path $pawnioLib)) {
            throw "PawnIO kutuphanesi olusmadi"
        }
    } catch {
        Write-Host "PawnIO kurulamadi: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "PawnIO surucusu zaten kurulu."
}

# 4) PresentMon
$pmExe = Join-Path $InstallRoot "third_party\presentmon\PresentMon.exe"
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

# 5) LibreHardwareMonitor
$lhmDll = Join-Path $InstallRoot "third_party\lhm\LibreHardwareMonitorLib.dll"
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

# 6) Guvenlik duvari kurali
& (Join-Path $PSScriptRoot "firewall.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Host "Guvenlik duvari adimi basarisiz oldu." -ForegroundColor Red
    exit 1
}

# 7) Zamanlanmis gorev + kisayollar
& (Join-Path $PSScriptRoot "install_task.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Host "Zamanlanmis gorev adimi basarisiz oldu." -ForegroundColor Red
    exit 1
}

# 8) Erisim kontrolu
$port = if ($env:SYNPU_PORT) { [int]$env:SYNPU_PORT } else { 8787 }
$ok = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:$port/api/snapshot" -UseBasicParsing -TimeoutSec 2 | Out-Null
        $ok = $true
        break
    } catch {
        Start-Sleep -Milliseconds 500
    }
}
if (-not $ok) {
    Write-Host "UYARI: Sunucuya erisilemedi (port $port)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Kurulum tamamlandi. Synpu baslatildi." -ForegroundColor Green
Write-Host "Masaustundeki Synpu simgesine tiklayarak QR penceresini acabilirsin."
exit 0
