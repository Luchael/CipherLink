@echo off
chcp 949 >nul
setlocal
cd /d "%~dp0"
rem Windows 개발자용 빌드. 최종 사용자는 CipherLink.exe만 실행합니다.
where python >nul 2>&1
if errorlevel 1 goto fail
python -c "import sys; assert sys.version_info >= (3, 10), 'Python 3.10+ is required for builds'"
if errorlevel 1 goto fail
python -m pip install -r requirements-login.txt -r requirements-endgame.txt
if errorlevel 1 goto fail
python -m pip install "pyinstaller>=6,<7"
if errorlevel 1 goto fail
rem Build prerequisites: required modules and required build resources.
python -c "import tkinter, genshin, arkprts, browser_cookie3, playwright.sync_api"
if errorlevel 1 goto fail
python -c "from pathlib import Path; required = ('assets/cipherlink.ico', 'assets/cipherlink.png', 'assets/version_info.txt', 'config.example.json', 'todoist_bindings.json', 'endgame_goals.json', 'game_rules.json'); missing = [name for name in required if not Path(name).is_file()]; assert not missing, 'Missing required build resources: ' + ', '.join(missing)"
if errorlevel 1 goto fail
python -m unittest discover -s tests -q
if errorlevel 1 goto fail
python -m PyInstaller --noconfirm --clean --windowed --onefile --name CipherLink --icon "assets\cipherlink.ico" --version-file "assets\version_info.txt" --collect-all genshin --collect-all arkprts --collect-all playwright --collect-submodules browser_cookie3 --add-data "assets\cipherlink.ico;assets" --add-data "assets\cipherlink.png;assets" --add-data "config.example.json;." --add-data "todoist_bindings.json;." --add-data "endgame_goals.json;." --add-data "game_rules.json;." gametodo_desktop.py
if errorlevel 1 goto fail
if not exist "dist\CipherLink.exe" goto fail
python -c "import hashlib; from pathlib import Path; p=Path('dist/CipherLink.exe'); Path('dist/SHA256SUMS.txt').write_text(hashlib.sha256(p.read_bytes()).hexdigest() + '  CipherLink.exe\n', encoding='ascii')"
if errorlevel 1 goto fail
echo dist\CipherLink.exe 생성됨. Windows 실제 로그인/설치 검증은 별도로 필요합니다.
if not "%CIPHERLINK_BUILD_NONINTERACTIVE%"=="1" pause
exit /b 0
:fail
echo [ERROR] 빌드 실패. 위 오류를 확인하세요. 이전 dist 파일은 새 빌드 결과가 아닐 수 있습니다.
if not "%CIPHERLINK_BUILD_NONINTERACTIVE%"=="1" pause
exit /b 1
