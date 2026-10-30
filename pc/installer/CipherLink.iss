; Korean per-user installer. AppId and data paths must stay stable across versions.
#ifndef AppVersion
  #error AppVersion must be provided by the build script
#endif
#ifndef SourceExe
  #error SourceExe must be provided by the build script
#endif
#ifndef OutputDir
  #error OutputDir must be provided by the build script
#endif

[Setup]
AppId={{E20AD5AC-9435-4B4D-A688-3759D01B5DBE}
AppName=사이퍼링크
AppVersion={#AppVersion}
AppPublisher=CipherLink
DefaultDirName={localappdata}\Programs\CipherLink
DefaultGroupName=사이퍼링크
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0
UsePreviousAppDir=yes
UsePreviousTasks=yes
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\CipherLink.exe
SetupIconFile=..\assets\cipherlink.ico
OutputDir={#OutputDir}
OutputBaseFilename=CipherLink-Windows-Setup
Compression=lzma2/fast
SolidCompression=yes
; Restart Manager must also stop hidden or non-responsive holders of our EXE.
CloseApplications=force
RestartApplications=no
WizardStyle=modern
VersionInfoVersion={#AppVersion}.0

[Languages]
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"

[Tasks]
Name: "desktopicon"; Description: "바탕 화면에 바로 가기 만들기"; Flags: unchecked

[Files]
Source: "{#SourceExe}"; DestDir: "{app}"; DestName: "CipherLink.exe"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\사이퍼링크"; Filename: "{app}\CipherLink.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\사이퍼링크"; Filename: "{app}\CipherLink.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\CipherLink.exe"; Description: "사이퍼링크 실행"; Flags: nowait postinstall skipifsilent

[Code]
const
  RunKey = 'Software\Microsoft\Windows\CurrentVersion\Run';
  UninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{E20AD5AC-9435-4B4D-A688-3759D01B5DBE}_is1';

function NextVersionPart(var Text: String): Integer;
var Position: Integer; Part: String;
begin
  Position := Pos('.', Text);
  if Position = 0 then begin Part := Text; Text := ''; end
  else begin Part := Copy(Text, 1, Position - 1); Delete(Text, 1, Position); end;
  Result := StrToIntDef(Part, 0);
end;

function CompareVersions(One, Two: String): Integer;
var I, A, B: Integer;
begin
  Result := 0;
  for I := 1 to 3 do begin
    A := NextVersionPart(One); B := NextVersionPart(Two);
    if A > B then begin Result := 1; Exit; end;
    if A < B then begin Result := -1; Exit; end;
  end;
end;

function InitializeSetup(): Boolean;
var InstalledVersion: String;
begin
  Result := True;
  if RegQueryStringValue(HKCU, UninstallKey, 'DisplayVersion', InstalledVersion) then
    if CompareVersions(InstalledVersion, '{#AppVersion}') > 0 then begin
      SuppressibleMsgBox('이미 더 새로운 사이퍼링크가 설치되어 있습니다. 최신 설치 파일을 사용해 주세요.', mbError, MB_OK, IDOK);
      Result := False;
    end;
end;

function OwnedExecutable(Value: String): Boolean;
var Name, Number: String; I, Dots: Integer;
begin
  Name := Lowercase(ExtractFileName(RemoveQuotes(Trim(Value))));
  Result := (Name = 'cipherlink.exe') or (Name = 'questlink.exe');
  if Result then Exit;
  if (Copy(Name, 1, 11) <> 'cipherlink-') or (Copy(Name, Length(Name) - 3, 4) <> '.exe') then Exit;
  Number := Copy(Name, 12, Length(Name) - 15); Dots := 0;
  if Number = '' then Exit;
  for I := 1 to Length(Number) do begin
    if Number[I] = '.' then Dots := Dots + 1
    else if (Number[I] < '0') or (Number[I] > '9') then Exit;
  end;
  Result := Dots = 2;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var Value: String;
begin
  if CurStep = ssPostInstall then begin
    { Retain the user's existing autorun choice and Windows disabled state. }
    if RegQueryStringValue(HKCU, RunKey, 'CipherLink', Value) and OwnedExecutable(Value) then
      RegWriteStringValue(HKCU, RunKey, 'CipherLink', '"' + ExpandConstant('{app}\CipherLink.exe') + '"');
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var Value: String;
begin
  if CurUninstallStep = usUninstall then begin
    if RegQueryStringValue(HKCU, RunKey, 'CipherLink', Value) then
      if CompareText(RemoveQuotes(Trim(Value)), ExpandConstant('{app}\CipherLink.exe')) = 0 then
        RegDeleteValue(HKCU, RunKey, 'CipherLink');
    { Never remove ~/.gametodo, credentials, databases or a different portable copy. }
  end;
end;
