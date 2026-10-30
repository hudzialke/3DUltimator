; Inno Setup 6.3+ / 7. Compile through build.ps1, or open in the Inno Setup IDE.
#define MyAppName "3D Ultimator"
#ifndef MyAppVersion
  #define MyAppVersion "1.1.2"
#endif
#ifndef AppSource
  #define AppSource "..\dist\3DUltimator"
#endif

[Setup]
AppId={{0E4782EB-D225-47F1-94DF-BB3DF97B785A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=hudzialke
AppPublisherURL=https://github.com/hudzialke/3DUltimator
AppSupportURL=https://github.com/hudzialke/3DUltimator/issues
AppUpdatesURL=https://github.com/hudzialke/3DUltimator/releases
DefaultDirName={localappdata}\Programs\3DUltimator
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
UninstallDisplayIcon={app}\3DUltimator.exe
WizardStyle=modern
Compression=lzma2/fast
SolidCompression=yes
OutputDir=..\artifacts
OutputBaseFilename=3DUltimator-Setup-{#MyAppVersion}-windows-x64
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#AppSource}\3DUltimator.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#AppSource}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\AUTHORS.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\examples\eight-packages.json"; DestDir: "{app}\examples"; Flags: ignoreversion

[InstallDelete]
; The runtime directory contains only shipped libraries. Replace it completely
; so DLLs from an older build cannot shadow Windows/Qt dependencies.
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\3DUltimator.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\3DUltimator.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\3DUltimator.exe"; Parameters: "--language={code:InitialLanguage}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitialLanguage(Param: String): String;
begin
  if ActiveLanguage = 'polish' then
    Result := 'pl'
  else
    Result := 'en';
end;
