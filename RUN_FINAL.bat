@echo off
title WiFi Mirroring Launcher (Final)
cd /d "%~dp0"

echo [1/4] Configuring Environment...
:: Set Python Path
set PY_PATH="C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe"

:: Set ADB Path (Borrowed from QtScrcpy)
set ADB_DIR=E:\Program Files\qt\QtScrcpy-Release\QtScrcpy-win-x64-v3.3.3
set PATH=%ADB_DIR%;%PATH%

if exist %PY_PATH% (
    echo Python: OK
) else (
    echo ERROR: Python not found.
    pause
    exit /b
)

echo.
echo [2/4] Verifying ADB...
adb version >nul 2>&1
if errorlevel 1 (
    echo WARNING: ADB not found. Android mirroring might fail.
) else (
    echo ADB: OK
)

echo.
echo [3/4] Checking Dependencies...
%PY_PATH% -m pip install PyQt5 qasync opencv-python numpy mss >nul 2>&1
echo Dependencies: OK

echo.
echo [4/4] Launching Application...
echo ---------------------------------------------------
echo Running... Please check the GUI window.
echo ---------------------------------------------------

%PY_PATH% wifi_mirroring_final.py

if errorlevel 1 (
    echo.
    echo CRITICAL ERROR: Application failed to start.
    echo Please take a screenshot of this window.
    pause
)
pause
