@echo off
cd /d "%~dp0"
title WiFi Mirroring Debug Launcher

echo ===================================================
echo   DEBUG MODE: WiFi Mirroring Launcher
echo ===================================================
echo.

:: 1. Locate Python
set PY_PATH="C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe"
if not exist %PY_PATH% (
    echo [ERROR] Python not found at %PY_PATH%
    pause
    exit /b
)
echo [OK] Python found.

:: 2. Set Qt Environment Variables (Crucial for UI)
echo [INFO] Setting Qt environment variables...
set QT_QPA_PLATFORM_PLUGIN_PATH=%~dp0\venv\Lib\site-packages\PyQt5\Qt5\plugins\platforms
set QT_DEBUG_PLUGINS=1

:: 3. Run Application with Error Reporting
echo.
echo [INFO] Starting Application...
echo ---------------------------------------------------
%PY_PATH% wifi_mirroring_final.py
echo ---------------------------------------------------

if errorlevel 1 (
    echo.
    echo [CRITICAL ERROR] Application crashed!
    echo Please take a screenshot of the error message above.
    pause
) else (
    echo [INFO] Application exited normally.
    pause
)
