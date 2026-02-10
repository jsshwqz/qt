@echo off
chcp 65001 >nul
echo ============================================
echo    WiFi手机投屏系统启动器
echo ============================================
echo.
echo 正在检查Python环境...

python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.8+
    pause
    exit /b 1
)

echo [OK] Python已安装
echo.

REM 检查并安装依赖
echo 正在检查依赖...
if not exist "requirements.txt" (
    echo [警告] 未找到requirements.txt
) else (
    pip install -r requirements.txt -q
    if errorlevel 1 (
        echo [警告] 依赖安装可能不完整，继续启动...
    ) else (
        echo [OK] 依赖已安装
    )
)

echo.
echo 请选择运行模式：
echo 1. 启动GUI界面（推荐）
echo 2. 启动桌面屏幕投屏（命令行）
echo 3. 启动ADB投屏（命令行）
echo 4. 启动完整服务器（命令行）
echo.

set /p choice="请输入选项 (1-4): "

if "%choice%"=="1" goto gui
if "%choice%"=="2" goto screen
if "%choice%"=="3" goto adb
if "%choice%"=="4" goto server
echo 无效选项，默认启动GUI...
goto gui

:gui
echo.
echo 正在启动GUI界面...
python -m phone_mirroring.app
goto end

:screen
echo.
echo 正在启动桌面屏幕投屏...
echo RTSP地址: rtsp://本机IP:8554/
echo 按Ctrl+C停止
python -m phone_mirroring.app_main screen --port 8554 --quality medium
goto end

:adb
echo.
echo 正在启动ADB投屏...
echo 请确保：
echo   1. Android设备已启用USB调试
echo   2. 设备已通过USB连接到电脑
echo   3. 已授权调试权限
echo.
echo RTSP地址: rtsp://本机IP:8554/
echo 按Ctrl+C停止
python -m phone_mirroring.app_main adb --port 8554
goto end

:server
echo.
echo 正在启动完整服务器...
echo RTSP地址: rtsp://本机IP:8554/
echo 按Ctrl+C停止
python -m phone_mirroring.app_main server --port 8554
goto end

:end
echo.
echo 投屏系统已停止
echo 按任意键退出...
pause >nul
