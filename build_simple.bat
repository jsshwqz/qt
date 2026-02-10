@echo off
chcp 65001 >nul
echo ========================================
echo   WiFi手机投屏 - 快速打包
echo ========================================
echo.

:: 最简单的打包命令 - 单文件模式
echo 正在打包为单个 EXE 文件...
echo.

pyinstaller --onefile --windowed --name "WiFi手机投屏" --clean --noconfirm ^
    --hidden-import PyQt5.QtWidgets ^
    --hidden-import PyQt5.QtCore ^
    --hidden-import PyQt5.QtGui ^
    --hidden-import qasync ^
    --hidden-import asyncio ^
    --exclude-module matplotlib ^
    --exclude-module numpy ^
    --exclude-module pandas ^
    --exclude-module scipy ^
    --exclude-module PIL ^
    --exclude-module tkinter ^
    --exclude-module setuptools ^
    --exclude-module pytest ^
    --exclude-module unittest ^
    --exclude-module pydoc ^
    --exclude-module sphinx ^
    --exclude-module docutils ^
    --exclude-module lxml ^
    --exclude-module bs4 ^
    --exclude-module html5lib ^
    --exclude-module coverage ^
    --exclude-module pylint ^
    --exclude-module mypy ^
    --exclude-module pip ^
    --exclude-module wheel ^
    --exclude-module Cython ^
    wifi_mirroring_app.py

if errorlevel 1 (
    echo.
    echo 错误: 打包失败！
    pause
    exit /b 1
)

echo.
echo ========================================
echo   打包完成！
echo ========================================
echo.
echo 文件位置: dist\WiFi手机投屏.exe
for %%I in ("dist\WiFi手机投屏.exe") do echo 文件大小: %%~zI 字节
echo.
echo 使用方法:
echo   1. 双击 dist\WiFi手机投屏.exe 运行
echo   2. 或复制到桌面使用
echo.
pause
