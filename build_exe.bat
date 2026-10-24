@echo off
title MyVPN - Ftiaxnei to MyVPN.exe
cd /d "%~dp0"
echo ============================================
echo   MyVPN - Dimiourgia MyVPN.exe
echo ============================================
echo.
where python >nul 2>nul
if errorlevel 1 (
  echo [X] Den vrethike Python.
  echo     Katevase to apo https://www.python.org/downloads/
  echo     kai tsekare "Add python.exe to PATH" stin egkatastasi.
  pause
  exit /b 1
)
echo [*] Egkatastasi PyInstaller...
python -m pip install --upgrade pyinstaller
if errorlevel 1 ( echo [X] Apotyxia egkatastasis PyInstaller. & pause & exit /b 1 )
echo.
echo [*] Ftiaxnetai to exe (1-2 lepta)...
python -m PyInstaller --noconfirm --onefile --windowed --uac-admin --name MyVPN myvpn.py
if errorlevel 1 ( echo [X] Apotyxia build. & pause & exit /b 1 )
copy /y dist\MyVPN.exe MyVPN.exe >nul
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q MyVPN.spec 2>nul
if not exist servers mkdir servers
echo.
echo [OK] Etoimo: %~dp0MyVPN.exe
echo      Vale ta .conf ston fakelo "servers" dipla sto exe.
pause
