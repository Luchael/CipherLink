@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m gametodo.safe_diagnostic --config config.json
pause
