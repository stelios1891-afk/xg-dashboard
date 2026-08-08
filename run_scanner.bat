@echo off
rem ============================================================
rem  VALUE SCANNER launcher (Task Scheduler)
rem  Reads keys FRESH from registry (HKCU\Environment).
rem  No secret is written inside this file.
rem ============================================================
cd /d "%~dp0"
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v TOA_KEY 2^>nul') do set "TOA_KEY=%%b"
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v TELEGRAM_TOKEN 2^>nul') do set "TELEGRAM_TOKEN=%%b"
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v TELEGRAM_CHAT_ID 2^>nul') do set "TELEGRAM_CHAT_ID=%%b"
set PYTHONIOENCODING=utf-8
set "PY=C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" scan_value.py auto
