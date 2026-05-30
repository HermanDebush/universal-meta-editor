[Setup]
AppName=Universal Meta Editor
AppVersion=1.2
AppPublisher=SNN PROJECT
AppPublisherURL=https://projectsnn.com/hub
AppSupportURL=https://github.com/HermanDebush/universal-meta-editor
AppUpdatesURL=https://github.com/HermanDebush/universal-meta-editor/releases
DefaultDirName={autopf}\UniversalMetaEditor
DefaultGroupName=Universal Meta Editor
OutputDir=..\dist\installer
OutputBaseFilename=UniversalMetaEditor_Setup
SetupIconFile=..\assets\icon.ico
WizardStyle=modern
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\UniversalMetaEditor.exe

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\UniversalMetaEditor.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\assets\icon.ico";             DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Ярлык в меню Пуск
Name: "{group}\Universal Meta Editor"; Filename: "{app}\UniversalMetaEditor.exe"; IconFilename: "{app}\icon.ico"
; Ярлык на рабочем столе
Name: "{autodesktop}\Universal Meta Editor"; Filename: "{app}\UniversalMetaEditor.exe"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные значки"

[Run]
Filename: "{app}\UniversalMetaEditor.exe"; Description: "Запустить Universal Meta Editor"; Flags: nowait postinstall skipifsilent
