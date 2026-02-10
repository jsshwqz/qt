@echo off
chcp 65001 >nul
echo ========================================
echo   Native Mirroring Pro - 启动程序
echo ========================================
echo.
echo 正在检查 Python 环境...
"C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe" --version
if errorlevel 1 (
    echo [错误] Python 未找到！
    pause
    exit /b 1
)
echo.
echo 正在检查 PyQt5...
"C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe" -c "import PyQt5; print('PyQt5: OK')" 2>nul
if errorlevel 1 (
    echo [错误] PyQt5 未安装！
    echo 正在安装 PyQt5...
    pip install PyQt5
)
echo.
echo 正在检查 ADB 设备...
"E:\Program Files\qt\QtScrcpy-Release\QtScrcpy-win-x64-v3.3.3\adb.exe" devices
echo.
echo ========================================
echo   启动投屏程序...
echo ========================================
echo.
cd /d "E:\Program Files\qt"
"C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe" wifi_mirroring_final.py
if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出！
    pause
)
