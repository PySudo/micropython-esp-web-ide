@echo off
setlocal
rem Starts the browser-based MicroPython Web IDE.
call "%~dp0scripts\run_web.bat"
exit /b %ERRORLEVEL%
