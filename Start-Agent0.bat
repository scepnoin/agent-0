@echo off
cd /d "%~dp0"
start /b python backend\main.py --project "%~dp0." --port 7800 --no-ui
timeout /t 5 /nobreak > nul
start "" "%~dp0Agent-0.exe"
