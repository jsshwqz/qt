@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   WiFi手机投屏 - EXE打包
echo ========================================
echo.

:: 检查Python
echo [1/4] 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python
    echo 请安装Python 3.8或更高版本
    pause
    exit /b 1
)
echo Python已安装

:: 安装依赖
echo.
echo [2/4] 安装依赖包...
echo 正在安装 PyInstaller, PyQt5, qasync...
pip install -q pyinstaller pyqt5 qasync 2>nul
if errorlevel 1 (
    echo 尝试使用用户模式安装...
    pip install --user -q pyinstaller pyqt5 qasync 2>nul
)
echo 依赖安装完成

:: 清理
echo.
echo [3/4] 清理旧文件...
if exist build rmdir /s /q build 2>nul
if exist dist rmdir /s /q dist 2>nul
echo 清理完成

:: 打包
echo.
echo [4/4] 开始打包EXE文件...
echo 这可能需要2-5分钟，请耐心等待...
echo.

python -m PyInstaller --onefile --windowed --name "WiFi手机投屏" --clean --noconfirm wifi_mirroring_app.py

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    echo 请检查上方的错误信息
    pause
    exit /b 1
)

:: 复制文件
echo.
if exist "dist\WiFi手机投屏.exe" (
    copy /y "dist\WiFi手机投屏.exe" . >nul
    echo ========================================
    echo [成功] EXE文件已生成！
    echo ========================================
    echo.
    echo 文件位置: %~dp0WiFi手机投屏.exe
    for %%I in ("%~dp0WiFi手机投屏.exe") do (
        echo 文件大小: %%~zI 字节 (约 %%~zI/1024/1024 MB)
    )
    echo.
    echo 使用方法:
    echo   1. 双击运行 "WiFi手机投屏.exe"
    echo   2. 点击"启动服务器"
    echo   3. 在手机上用VLC打开显示的RTSP地址
    echo.
    explorer.exe /select,"%~dp0WiFi手机投屏.exe"
) else (
    echo [错误] 未找到生成的EXE文件
)

pause
