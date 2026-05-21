@echo off
setlocal
rem Starts the console uploader. Use run_web.bat for the browser IDE.
call "%~dp0scripts\run_uploader.bat"
exit /b %ERRORLEVEL%
