#define MyAppName "Synpu"
#define MyAppVersion "0.2.14"
#define MyAppPublisher "Batuhan Savas Yilmaz"
#define MyAppURL "https://github.com/batuhansavas-yilmaz/synpu"

[Setup]
AppId={{8F3C1A52-3B7E-4D2A-9C41-6E0B7D5A2C11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={localappdata}\Synpu\app
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputDir=..\dist
OutputBaseFilename=SynpuSetup
SetupIconFile=..\static\icon.ico
UninstallDisplayIcon={app}\static\icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Files]
Source: "..\src\*"; DestDir: "{app}\src"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\static\*"; DestDir: "{app}\static"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\scripts\setup.ps1"; DestDir: "{app}\scripts"
Source: "..\scripts\firewall.ps1"; DestDir: "{app}\scripts"
Source: "..\scripts\install_task.ps1"; DestDir: "{app}\scripts"
Source: "..\scripts\launch.vbs"; DestDir: "{app}\scripts"
Source: "..\pyproject.toml"; DestDir: "{app}"
Source: "..\uv.lock"; DestDir: "{app}"
Source: "..\README.md"; DestDir: "{app}"
Source: "..\assets\*"; DestDir: "{app}\assets"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"
Source: "..\third_party\*.txt"; DestDir: "{app}\third_party"

[Icons]
Name: "{userdesktop}\Synpu"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\scripts\launch.vbs"" show"; WorkingDir: "{app}"; IconFilename: "{app}\static\icon.ico"; Comment: "Synpu - Telefonla Baglan"
Name: "{userstartup}\Synpu"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\scripts\launch.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\static\icon.ico"; Comment: "Synpu"

[Run]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\scripts\setup.ps1"""; StatusMsg: "Synpu bilesenleri kuruluyor (birkac dakika surebilir)..."; Flags: runhidden waituntilterminated

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -Command ""Unregister-ScheduledTask -TaskName Synpu -Confirm:$false -ErrorAction SilentlyContinue; Remove-NetFirewallRule -DisplayName 'Synpu (TCP 8787)' -ErrorAction SilentlyContinue; Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'Synpu' -ErrorAction SilentlyContinue; Remove-Item (Join-Path ([Environment]::GetFolderPath('Startup')) 'Synpu.lnk') -ErrorAction SilentlyContinue"""; Flags: runhidden; RunOnceId: "RemoveSynpuTask"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
