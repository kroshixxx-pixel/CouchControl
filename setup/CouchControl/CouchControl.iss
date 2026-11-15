#define MyAppName "CouchControl"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "CouchControl"

[Setup]
AppId={{B1A5E3D4-8A27-4F2A-9A6C-CC0123A45D67}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\CouchControl
DefaultGroupName=CouchControl
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=CouchControl-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
UninstallDisplayIcon={app}\CouchControl.ico

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные параметры:"; Flags: checkedonce
Name: "autostart"; Description: "Запускать CouchControl автоматически при входе в Windows"; GroupDescription: "Дополнительные параметры:"; Flags: unchecked

[Files]
Source: "bot.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "install.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: ".env.example"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\CouchControl"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\bot.py"""; WorkingDir: "{app}"
Name: "{autodesktop}\CouchControl"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\bot.py"""; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userstartup}\CouchControl"; Filename: "{app}\.venv\Scripts\pythonw.exe"; Parameters: """{app}\bot.py"""; WorkingDir: "{app}"; Tasks: autostart

[Run]
Filename: "powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\install.ps1"""; StatusMsg: "Загрузка Python и установка компонентов CouchControl..."; Flags: runhidden waituntilterminated

[Code]
var
  TelegramPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  TelegramPage := CreateInputQueryPage(wpSelectDir,
    'Настройка Telegram',
    'Введите данные вашего Telegram-бота',
    'Токен получите у @BotFather командой /newbot. ' +
    'Ваш числовой Telegram User ID можно узнать у @userinfobot.');
  TelegramPage.Add('Bot Token:', False);
  TelegramPage.Add('Telegram User ID:', False);
end;

function IsDigitsOnly(const S: string): Boolean;
var
  I: Integer;
begin
  Result := (S <> '');
  for I := 1 to Length(S) do
    if (S[I] < '0') or (S[I] > '9') then
    begin
      Result := False;
      Exit;
    end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = TelegramPage.ID then
  begin
    if Trim(TelegramPage.Values[0]) = '' then
    begin
      MsgBox('Введите токен Telegram-бота.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    if not IsDigitsOnly(Trim(TelegramPage.Values[1])) or
       (Trim(TelegramPage.Values[1]) = '0') then
    begin
      MsgBox('Введите числовой Telegram User ID.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvText: string;
begin
  if CurStep = ssPostInstall then
  begin
    EnvText := 'BOT_TOKEN=' + Trim(TelegramPage.Values[0]) + #13#10 +
               'ALLOWED_USER_ID=' + Trim(TelegramPage.Values[1]) + #13#10;
    if not SaveStringToFile(ExpandConstant('{app}\.env'), EnvText, False) then
      RaiseException('Не удалось сохранить настройки Telegram в .env');
  end;
end;
