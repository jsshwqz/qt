@echo off
cd /d "%~dp0"

echo ========================================
echo WiFi Phone Mirroring - Build EXE
echo ========================================
echo.

:: Check Python
echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)
echo Python OK

:: Install dependencies
echo.
echo [2/4] Installing dependencies...
pip install -q pyinstaller pyqt5 qasync
if errorlevel 1 (
    echo Trying user install...
    pip install --user -q pyinstaller pyqt5 qasync
)
echo Dependencies OK

:: Clean old builds
echo.
echo [3/4] Cleaning old builds...
if exist build rmdir /s /q build 2>nul
if exist dist rmdir /s /q dist 2>nul
echo Clean OK

:: Build EXE
echo.
echo [4/4] Building EXE...
echo This may take 3-5 minutes, please wait...
echo.

python -m PyInstaller --onefile --windowed --name "WiFi_Mirroring" --clean --noconfirm wifi_mirroring_app.py

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    echo Please check error messages above
    pause
    exit /b 1
)

:: Copy to root
echo.
if exist "dist\WiFi_Mirroring.exe" (
    copy /y "dist\WiFi_Mirroring.exe" . >nul
    echo ========================================
    echo SUCCESS! EXE file created!
    echo ========================================
    echo.
    echo Location: %~dp0WiFi_Mirroring.exe
    for %%I in ("%~dp0WiFi_Mirroring.exe") do (
        echo Size: %%~zI bytes
    )
    echo.
    echo Usage:
    echo   1. Double click "WiFi_Mirroring.exe"
    echo   2. Click "Start Server"
    echo   3. Open RTSP URL in VLC on phone
    echo.
    explorer.exe /select,"%~dp0WiFi_Mirroring.exe"
) else (
    echo ERROR: EXE file not found!
)

pause
