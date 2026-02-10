@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo WiFi手机投屏 - 快速启动
echo ========================================
echo.

echo [1/3] 检查Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo 错误: 未安装Python!
    echo 请从 https://python.org 下载安装Python 3.8+
    echo 安装时勾选 "Add Python to PATH"
    pause
    exit /b 1
)
echo Python已安装

echo.
echo [2/3] 安装依赖...
pip install -q PyQt5 qasync opencv-python numpy mss 2>nul
if errorlevel 1 (
    echo 安装失败，尝试用户模式安装...
    pip install --user -q PyQt5 qasync opencv-python numpy mss
)
echo 依赖完成

echo.
echo [3/3] 启动程序...
echo.
echo ========================================
echo 正在启动WiFi投屏系统...
echo ========================================
echo.

python wifi_mirroring_final.py

if errorlevel 1 (
    echo.
    echo 启动失败! 可能原因:
    echo 1. 依赖未正确安装
    echo 2. 请手动运行: pip install PyQt5 qasync opencv-python numpy mss
    pause
)
