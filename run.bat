@echo off
setlocal

cd /d "%~dp0"

python -m pip install -q -r requirements.txt
if errorlevel 1 exit /b %errorlevel%

python main.py %*
exit /b %errorlevel%
