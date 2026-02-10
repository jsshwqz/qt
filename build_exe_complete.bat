@echo off
REM Native Mirroring Pro v2.1 - EXE构建脚本
REM 自动化的打包流程

setlocal enabledelayedexpansion

REM 设置路径
set PROJECT_DIR=%~dp0
set PYTHON_EXE=C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe

echo.
echo ======================================================
echo Native Mirroring Pro v2.1 - EXE Build
echo ======================================================
echo.

REM 1. 检查Python
echo [1] 检查Python环境...
if not exist "%PYTHON_EXE%" (
    echo ERROR: Python不存在于 %PYTHON_EXE%
    pause
    exit /b 1
)
echo OK: Python found

REM 2. 检查源文件
echo [2] 检查源文件...
if not exist "%PROJECT_DIR%scrcpy_client_v2.1.py" (
    echo ERROR: 找不到 scrcpy_client_v2.1.py
    pause
    exit /b 1
)
echo OK: Source file found

REM 3. 创建输出目录
echo [3] 创建输出目录...
if not exist "%PROJECT_DIR%dist" mkdir "%PROJECT_DIR%dist"
if not exist "%PROJECT_DIR%build" mkdir "%PROJECT_DIR%build"
echo OK: Directories created

REM 4. 安装PyInstaller
echo [4] 安装依赖...
"%PYTHON_EXE%" -m pip install pyinstaller PyQt5 opencv-python numpy --quiet
if %ERRORLEVEL% neq 0 (
    echo WARNING: 依赖安装可能有问题，继续...
)
echo OK: Dependencies processed

REM 5. 构建EXE
echo [5] 编译EXE文件...
cd /d "%PROJECT_DIR%"
"%PYTHON_EXE%" -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "scrcpy_client_v2.1" ^
    --distpath "%PROJECT_DIR%dist" ^
    --buildpath "%PROJECT_DIR%build" ^
    --specpath "%PROJECT_DIR%build" ^
    --add-data "config_manager.py;." ^
    --add-data "log_manager.py;." ^
    --add-data "exceptions.py;." ^
    --hidden-import=PyQt5 ^
    --hidden-import=cv2 ^
    --hidden-import=numpy ^
    "scrcpy_client_v2.1.py"

if %ERRORLEVEL% neq 0 (
    echo WARNING: EXE build returned non-zero exit code
)

REM 6. 验证
echo [6] 验证EXE...
if exist "%PROJECT_DIR%dist\scrcpy_client_v2.1.exe" (
    echo OK: EXE file created successfully
    for %%A in ("%PROJECT_DIR%dist\scrcpy_client_v2.1.exe") do (
        set size=%%~zA
        echo    File size: !size! bytes
    )
) else (
    echo ERROR: EXE file not found
    if exist "%PROJECT_DIR%dist" (
        echo Files in dist directory:
        dir "%PROJECT_DIR%dist"
    )
)

REM 7. 创建启动脚本
echo [7] 创建启动脚本...
(
    echo @echo off
    echo REM Native Mirroring Pro v2.1 - 启动脚本
    echo cd /d "%PROJECT_DIR%dist"
    echo if exist "scrcpy_client_v2.1.exe" (
    echo     scrcpy_client_v2.1.exe
    echo ) else (
    echo     echo ERROR: 找不到 scrcpy_client_v2.1.exe
    echo     pause
    echo )
) > "%PROJECT_DIR%run_app.bat"
echo OK: Launcher created at %PROJECT_DIR%run_app.bat

echo.
echo ======================================================
echo 构建完成！
echo ======================================================
echo.
echo EXE文件位置: %PROJECT_DIR%dist\scrcpy_client_v2.1.exe
echo 启动脚本: %PROJECT_DIR%run_app.bat
echo.
pause
