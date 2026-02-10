@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo WiFi Phone Mirroring - Build EXE
echo ========================================
echo.

echo Step 1: Installing dependencies...
pip install -q pyinstaller pyqt5 qasync opencv-python numpy mss
if errorlevel 1 (
    echo Failed to install, trying with --user...
    pip install --user -q pyinstaller pyqt5 qasync opencv-python numpy mss
)

echo.
echo Step 2: Cleaning old builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "WiFi_Mirroring.exe" del "WiFi_Mirroring.exe"

echo.
echo Step 3: Building EXE... This will take 3-5 minutes
echo Please wait...
echo.

python -m PyInstaller --onefile --windowed --name "WiFi_Mirroring" --clean --noconfirm wifi_mirroring_final.py

if exist "dist\WiFi_Mirroring.exe" (
    echo.
    echo ========================================
    echo SUCCESS! EXE created!
    echo ========================================
    copy /y "dist\WiFi_Mirroring.exe" . >nul
    echo.
    echo Location: %~dp0WiFi_Mirroring.exe
    for %%I in ("%~dp0WiFi_Mirroring.exe") do echo Size: %%~zI bytes
    echo.
    echo Double-click WiFi_Mirroring.exe to run
    pause
    explorer.exe /select,"%~dp0WiFi_Mirroring.exe"
) else (
    echo.
    echo ERROR: Build failed!
    echo.
    echo Please check:
    echo 1. Python is installed: python --version
    echo 2. Run manually: pip install pyinstaller pyqt5 qasync
    echo 3. Then: python -m PyInstaller --onefile --windowed wifi_mirroring_final.py
    pause
)
