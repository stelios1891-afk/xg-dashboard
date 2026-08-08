@echo off
rem ============================================================
rem  BETTING MODEL - ONE-CLICK PIPELINE
rem  Runs in order: discover -> dl -> build_inputs -> picks
rem  Usage:  double-click (season 2627)   OR   run_pipeline.bat 2526
rem  (Batch text is ASCII on purpose; Greek output comes from Python.)
rem ============================================================
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

rem --- season (default = current 2627) ---
set "SEASON=%~1"
if "%SEASON%"=="" set "SEASON=2627"

rem --- locate python: prefer the real install directly (avoids the MS Store stub) ---
set "PY=C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=python"

echo ============================================================
echo   BETTING MODEL PIPELINE  -  season %SEASON%
echo ============================================================

echo.
echo [1/4] DISCOVER  -  find new finished matches...
%PY% discover.py %SEASON%

echo.
echo [2/4] DOWNLOAD  -  shots + Opta re-check (4 days)...
for %%L in (EPL LaLiga SerieA Bundesliga Ligue1 Belgium ScottishPrem PrimeiraLiga) do %PY% dl.py %%L_%SEASON%

echo.
echo [3/4] BUILD INPUTS  -  compression / penalty / red...
%PY% build_inputs.py

echo.
echo [4/4] PICKS  -  value +handicap bets...
%PY% picks.py picks %SEASON%

echo.
echo ============================================================
echo   DONE  -  opening picks (picks_output.txt)
echo ============================================================
if exist picks_output.txt start "" notepad picks_output.txt
