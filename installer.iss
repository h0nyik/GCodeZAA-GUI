[Setup]
AppName=GCodeZAA
AppVersion={#AppVersion}
AppPublisher=h0nyik
AppPublisherURL=https://github.com/h0nyik/GCodeZAA
AppSupportURL=https://github.com/h0nyik/GCodeZAA/issues
AppUpdatesURL=https://github.com/h0nyik/GCodeZAA/releases
DefaultDirName={autopf}\GCodeZAA
DefaultGroupName=GCodeZAA
AllowNoIcons=yes
OutputDir=installer_out
OutputBaseFilename=GCodeZAA-Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\GCodeZAA.exe
LicenseFile=LICENSE
SetupIconFile=

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\GCodeZAA\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\GCodeZAA"; Filename: "{app}\GCodeZAA.exe"
Name: "{group}\{cm:UninstallProgram,GCodeZAA}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\GCodeZAA"; Filename: "{app}\GCodeZAA.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\GCodeZAA.exe"; Description: "{cm:LaunchProgram,GCodeZAA}"; Flags: nowait postinstall skipifsilent
