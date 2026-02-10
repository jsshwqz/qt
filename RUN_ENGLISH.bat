@echo off
title WiFi Mirroring Launcher
cd /d "%~dp0"

echo [1/3] Locating Python...
set PY_PATH="C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe"

if exist %PY_PATH% (
    echo Python found at: %PY_PATH%
) else (
    echo CRITICAL ERROR: Python executable not found at expected path.
    pause
    exit /b
)

echo.
echo [2/3] Installing libraries (please wait)...
%PY_PATH% -m pip install PyQt5 qasync opencv-python numpy mss

echo.
echo [3/3] Starting Application...
echo.
echo ---------------------------------------------------
echo App is starting. If window does not appear, check errors below.
echo ---------------------------------------------------
echo.

%PY_PATH% wifi_mirroring_final.py

if errorlevel 1 (
    echo.
    echo Application crashed. Please report the error above.
    pause
)
pause
