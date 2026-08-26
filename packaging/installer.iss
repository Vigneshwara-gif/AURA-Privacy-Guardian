; Inno Setup 6 Script for AURA Privacy Guardian (Per-User Installation)
#define MyAppName "AURA Privacy Guardian"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "AURA Security Team"
#define MyAppExeName "aura-agent.exe"
#define MyCliExeName "aura.exe"

[Setup]
AppId={{C8E1F350-4E8B-4A92-80D7-4B2E5C9A1A10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\AURA
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist_installer
OutputBaseFilename=AURA_Setup_v{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\bin\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Dirs]
Name: "{app}\bin"
Name: "{localappdata}\AURA\data"; Permissions: users-full
Name: "{localappdata}\AURA\logs"; Permissions: users-full
Name: "{localappdata}\AURA\models"; Permissions: users-full
Name: "{localappdata}\AURA\config"; Permissions: users-full

[Files]
Source: "dist\aura-agent\*"; DestDir: "{app}\bin"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\aura-cli\aura.exe"; DestDir: "{app}\bin"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\bin\{#MyAppExeName}"
Name: "{group}\AURA CLI"; Filename: "{app}\bin\{#MyCliExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
; 1. Register Task Scheduler primary startup
Filename: "schtasks.exe"; Parameters: "/Create /TN ""AURA\AURA_Privacy_Guardian_Agent"" /TR ""\""{app}\bin\{#MyAppExeName}\"""" /SC ONLOGON /DELAY 0000:05 /RL LIMITED /F"; Flags: runhidden
; 2. Launch background agent daemon
Filename: "{app}\bin\{#MyAppExeName}"; Description: "Start AURA Background Agent"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; 1. Stop agent daemon
Filename: "{app}\bin\{#MyCliExeName}"; Parameters: "agent stop"; Flags: runhidden
; 2. Delete scheduled task
Filename: "schtasks.exe"; Parameters: "/Delete /TN ""AURA\AURA_Privacy_Guardian_Agent"" /F"; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
; Preserves {localappdata}\AURA\data by default unless user purges
