@echo off
cd /d "%~dp0"
python issue_token.py %*
if errorlevel 1 pause
