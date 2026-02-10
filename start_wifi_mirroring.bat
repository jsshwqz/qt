@echo off
echo ================================
echo   WiFi手机投屏系统启动器
echo ================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

REM 检查必要的包
echo [信息] 检查依赖包...
python -c "import PyQt5" 2>nul
if errorlevel 1 (
    echo [警告] PyQt5未安装，正在安装...
    pip install PyQt5
)

python -c "import qasync" 2>nul
if errorlevel 1 (
    echo [警告] qasync未安装，正在安装...
    pip install qasync
)

REM 创建配置目录
if not exist "phone_mirroring\config" mkdir "phone_mirroring\config"

REM 启动应用
echo [信息] 启动WiFi投屏应用...
python phone_mirroring\app.py

if errorlevel 1 (
    echo.
    echo [错误] 应用启动失败
    pause
)