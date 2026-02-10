# Native Mirroring Pro v2.1 - PowerShell EXE Build Script

$ErrorActionPreference = "Continue"
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = "C:\Users\Administrator\AppData\Local\Programs\Python\Python313\python.exe"

Write-Host ""
Write-Host "======================================================"
Write-Host "Native Mirroring Pro v2.1 - EXE Build"
Write-Host "======================================================"
Write-Host ""

# 1. Check Python
Write-Host "[1] 检查Python环境..."
if (-not (Test-Path $pythonExe)) {
    Write-Host "ERROR: Python not found at $pythonExe" -ForegroundColor Red
    exit 1
}
Write-Host "OK: Python found" -ForegroundColor Green

# 2. Check source file
Write-Host "[2] 检查源文件..."
$sourceFile = Join-Path $projectDir "scrcpy_client_v2.1.py"
if (-not (Test-Path $sourceFile)) {
    Write-Host "ERROR: Source file not found" -ForegroundColor Red
    exit 1
}
Write-Host "OK: Source file found" -ForegroundColor Green

# 3. Create directories
Write-Host "[3] 创建输出目录..."
$distDir = Join-Path $projectDir "dist"
$buildDir = Join-Path $projectDir "build"
if (-not (Test-Path $distDir)) { New-Item -ItemType Directory -Path $distDir -Force | Out-Null }
if (-not (Test-Path $buildDir)) { New-Item -ItemType Directory -Path $buildDir -Force | Out-Null }
Write-Host "OK: Directories created" -ForegroundColor Green

# 4. Install dependencies
Write-Host "[4] 安装依赖..."
$packages = @("pyinstaller", "PyQt5", "opencv-python", "numpy")
foreach ($pkg in $packages) {
    Write-Host "  Installing $pkg..."
    & $pythonExe -m pip install $pkg --quiet
}
Write-Host "OK: Dependencies processed" -ForegroundColor Green

# 5. Build EXE
Write-Host "[5] 编译EXE文件..."
cd $projectDir
$specFile = Join-Path $buildDir "scrcpy_client_v2.1.spec"
$args = @(
    "--onefile",
    "--windowed",
    "--name", "scrcpy_client_v2.1",
    "--distpath", $distDir,
    "--buildpath", $buildDir,
    "--specpath", $buildDir,
    "--add-data", "config_manager.py;.",
    "--add-data", "log_manager.py;.",
    "--add-data", "exceptions.py;.",
    "--hidden-import=PyQt5",
    "--hidden-import=cv2",
    "--hidden-import=numpy",
    $sourceFile
)
& $pythonExe -m PyInstaller $args
if ($LASTEXITCODE -eq 0) {
    Write-Host "OK: EXE compilation completed" -ForegroundColor Green
} else {
    Write-Host "WARNING: Build exited with code $LASTEXITCODE" -ForegroundColor Yellow
}

# 6. Verify
Write-Host "[6] 验证EXE..."
$exeFile = Join-Path $distDir "scrcpy_client_v2.1.exe"
if (Test-Path $exeFile) {
    $size = (Get-Item $exeFile).Length
    $sizeMB = [math]::Round($size / 1MB, 2)
    Write-Host "OK: EXE file created successfully" -ForegroundColor Green
    Write-Host "    File size: $sizeMB MB ($size bytes)"
} else {
    Write-Host "ERROR: EXE file not found" -ForegroundColor Red
    Write-Host "Files in dist directory:"
    Get-ChildItem $distDir -Recurse | ForEach-Object { Write-Host "  $_" }
}

# 7. Create launcher
Write-Host "[7] 创建启动脚本..."
$launcherPath = Join-Path $projectDir "run_app.bat"
$launcherContent = @"
@echo off
REM Native Mirroring Pro v2.1 - Launcher Script
cd /d "$distDir"
if exist "scrcpy_client_v2.1.exe" (
    scrcpy_client_v2.1.exe
) else (
    echo ERROR: scrcpy_client_v2.1.exe not found
    pause
)
"@
Set-Content -Path $launcherPath -Value $launcherContent -Encoding UTF8
Write-Host "OK: Launcher created" -ForegroundColor Green

Write-Host ""
Write-Host "======================================================"
Write-Host "构建完成！"
Write-Host "======================================================"
Write-Host ""
Write-Host "EXE文件位置: $exeFile"
Write-Host "启动脚本: $launcherPath"
Write-Host ""
