# Set execution policy for this session
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Native Mirroring Pro - 启动程序" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "正在检查 Python 环境..." -ForegroundColor Yellow
$python = "C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "[错误] Python 未找到: $python" -ForegroundColor Red
    Read-Host "按 Enter 退出"
    exit 1
}
& $python --version
Write-Host ""

# Check PyQt5
Write-Host "正在检查 PyQt5..." -ForegroundColor Yellow
$result = & $python -c "import PyQt5; print('PyQt5: OK')" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] PyQt5 未安装！" -ForegroundColor Red
    Write-Host "正在安装 PyQt5..." -ForegroundColor Yellow
    pip install PyQt5
} else {
    Write-Host $result -ForegroundColor Green
}
Write-Host ""

# Check ADB devices
Write-Host "正在检查 ADB 设备..." -ForegroundColor Yellow
$adb = "E:\Program Files\qt\QtScrcpy-Release\QtScrcpy-win-x64-v3.3.3\adb.exe"
if (Test-Path $adb) {
    & $adb devices
} else {
    Write-Host "[警告] ADB 未找到: $adb" -ForegroundColor Red
}
Write-Host ""

# Start the program
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  启动投屏程序..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$projectDir = "E:\Program Files\qt"
Set-Location $projectDir

try {
    & $python wifi_mirroring_final.py
} catch {
    Write-Host ""
    Write-Host "[错误] 程序异常退出！" -ForegroundColor Red
    Write-Host "错误信息: $_" -ForegroundColor Red
    Read-Host "按 Enter 退出"
    exit 1
}
