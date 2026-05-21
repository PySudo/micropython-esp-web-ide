@echo off
setlocal
cd /d "%~dp0.."
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not installed.
    echo Download Python from https://python.org
    pause
    exit /b 1
)
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency installation failed.
    pause
    exit /b 1
)
python uploader.py
pause
