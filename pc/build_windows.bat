@echo off
chcp 949 >nul
setlocal
cd /d "%~dp0"
rem Windows 배포용 EXE: 로그인 모듈을 빌드할 때 포함해야 로그인 버튼이 작동함
python -m pip install -r requirements-login.txt
if errorlevel 1 goto fail
python -m pip install pyinstaller
if errorlevel 1 goto fail
python -m PyInstaller --noconfirm --clean --windowed --onefile --name CipherLink --icon "assets\cipherlink.ico" --version-file "assets\version_info.txt" --collect-all genshin --collect-all arkprts --collect-all playwright --collect-submodules browser_cookie3 --add-data "assets\cipherlink.ico;assets" --add-data "assets\cipherlink.png;assets" --add-data "config.example.json;." --add-data "todoist_bindings.json;." --add-data "endgame_goals.json;." --add-data "game_rules.json;." gametodo_desktop.py
if errorlevel 1 goto fail
echo dist\CipherLink.exe 생성됨
pause
exit /b 0
:fail
echo [ERROR] 빌드 실패. python -m pip 명령을 확인하세요.
pause
exit /b 1
