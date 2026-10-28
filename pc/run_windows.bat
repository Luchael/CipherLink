@echo off
chcp 949 >nul
setlocal
cd /d "%~dp0"
rem 한국어 Windows CMD: CP949 + CRLF / Python 런처: python
where python >nul 2>&1
if errorlevel 1 goto missing
python -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>&1
if errorlevel 1 goto missing
rem GUI를 먼저 보여주므로 API 키를 입력할 필요가 없습니다.
python -m gametodo gui
if errorlevel 1 pause
exit /b %ERRORLEVEL%
:missing
echo [ERROR] Python 3.10+ 명령을 찾지 못했습니다.
echo CMD에서 python --version 을 확인해주세요.
pause
exit /b 1
