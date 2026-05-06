@echo off
setlocal
cd /d "%~dp0"
python listen.py %*
exit /b %errorlevel%
