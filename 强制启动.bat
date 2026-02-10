@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   WiFi手机投屏 - 强制修复启动版
echo ========================================
echo.

set PYTHON_PATH="C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe"

echo [1/3] 检测Python...
if exist %PYTHON_PATH% (
    echo Python路径有效: %PYTHON_PATH%
) else (
    echo 错误: 未在默认位置找到Python!
    echo 请尝试重新安装Python 3.13
    pause
    exit /b
)

echo.
echo [2/3] 强制安装依赖...
%PYTHON_PATH% -m pip install PyQt5 qasync opencv-python numpy mss

echo.
echo [3/3] 启动程序...
echo ========================================
echo 程序即将启动，请勿关闭此窗口...
echo ========================================
%PYTHON_PATH% wifi_mirroring_final.py

if errorlevel 1 (
    echo.
    echo 程序异常退出!
    pause
)
