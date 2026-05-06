@echo off
setlocal
cd /d "%~dp0"
python trigger.py %*
exit /b %errorlevel%
