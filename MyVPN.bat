@echo off
title MyVPN
cd /d "%~dp0"
:: Zitaei dikaiomata diaxeiristi an den ta exei
net session >nul 2>&1
if errorlevel 1 (
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)
if exist "MyVPN.exe" (
  start "" "MyVPN.exe"
  exit /b
)
where pythonw >nul 2>nul
if errorlevel 1 (
  echo [X] Den vrethike oute MyVPN.exe oute Python.
  echo     Trexe prota to build_exe.bat i egkatestise Python.
  pause
  exit /b 1
)
start "" pythonw "%~dp0myvpn.py"
