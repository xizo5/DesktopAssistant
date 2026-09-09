@echo off
setlocal
title Build DesktopAssistant exe

REM ============================================================
REM  Build a single exe for sharing (no Python needed on target PC)
REM  Just double-click this file. First run installs the tools.
REM  Output: dist\DesktopAssistant.exe
REM ============================================================

cd /d "%~dp0"
set "LOG=build_log.txt"

echo Step 1/4: checking Python ...
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY (
  where py >nul 2>nul && set "PY=py -3"
)
if not defined PY (
  echo.
  echo [X] Python was not found on this computer.
  echo     Please install Python 3.10+ from https://www.python.org/downloads/
  echo     and CHECK the box "Add python.exe to PATH" during setup,
  echo     then run this file again.
  echo.
  pause
  exit /b 1
)
%PY% --version

echo Step 2/4: installing build tools, please wait ...
%PY% -m pip install pyinstaller >"%LOG%" 2>&1
if errorlevel 1 (
  echo [X] pip install failed. Log:
  type "%LOG%"
  pause
  exit /b 1
)
%PY% -m pip install pillow >>"%LOG%" 2>&1

echo Step 3/4: making program icon ...
if exist assets\logo.png (
  %PY% make_icon.py >>"%LOG%" 2>&1
)
set "ICON_ARG="
if exist assets\logo.ico set "ICON_ARG=--icon assets\logo.ico"

echo Step 4/4: building the exe, takes 1-2 minutes, keep this window open ...
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name DesktopAssistant %ICON_ARG% main.py >"%LOG%" 2>&1
if errorlevel 1 (
  echo [X] Build failed. Last lines of build_log.txt:
  powershell -NoProfile -Command "Get-Content 'build_log.txt' -Tail 40"
  echo.
  echo Full log saved to build_log.txt - send it to me if you need help.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo  DONE!
echo  Your exe:  dist\DesktopAssistant.exe
echo  Send that ONE file to your friend. No Python needed.
echo  Note: first run on their PC may show a blue SmartScreen
echo  warning - click "More info" then "Run anyway".
echo  Tip: keep the exe in a normal folder (like Desktop),
echo  settings are saved next to the exe.
echo ============================================================
pause
