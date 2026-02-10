#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Native Mirroring Pro v2.1 - EXE 构建脚本
完整的自动化打包脚本，包含依赖检查和构建
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'


def log(msg, level='INFO'):
    """记录日志"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    if level == 'INFO':
        print(f"{Colors.BLUE}[{timestamp}] INFO{Colors.END}: {msg}")
    elif level == 'SUCCESS':
        print(f"{Colors.GREEN}[{timestamp}] ✓{Colors.END}: {msg}")
    elif level == 'WARNING':
        print(f"{Colors.YELLOW}[{timestamp}] ⚠{Colors.END}: {msg}")
    elif level == 'ERROR':
        print(f"{Colors.RED}[{timestamp}] ✗{Colors.END}: {msg}")
    elif level == 'DEBUG':
        print(f"{Colors.CYAN}[{timestamp}] ◆{Colors.END}: {msg}")


def check_python_version():
    """检查 Python 版本"""
    log(f"Python version: {sys.version}")
    if sys.version_info < (3, 7):
        log("Python 3.7+ required", 'ERROR')
        return False
    log("Python version check passed", 'SUCCESS')
    return True


def install_package(pip_name):
    """安装包"""
    log(f"Installing {pip_name}...", 'INFO')
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", pip_name],
            check=True,
            capture_output=True
        )
        log(f"{pip_name} installed successfully", 'SUCCESS')
        return True
    except subprocess.CalledProcessError as e:
        log(f"Failed to install {pip_name}: {e}", 'ERROR')
        return False


def check_and_install_dependencies():
    """检查并安装所有依赖"""
    log("Checking dependencies...", 'INFO')
    print()
    
    dependencies = [
        ('PyQt5', 'PyQt5'),
        ('cv2', 'opencv-python'),
        ('numpy', 'numpy'),
        ('pyinstaller', 'pyinstaller'),
    ]
    
    failed = []
    
    for package_name, pip_name in dependencies:
        try:
            __import__(package_name)
            log(f"✓ {package_name} available", 'SUCCESS')
        except ImportError:
            log(f"✗ {package_name} not found, installing...", 'WARNING')
            if not install_package(pip_name):
                failed.append(package_name)
    
    print()
    
    if failed:
        log(f"Failed to install: {', '.join(failed)}", 'ERROR')
        return False
    
    log("All dependencies installed", 'SUCCESS')
    return True


def build_exe():
    """构建 EXE 文件"""
    log("Building EXE file...", 'INFO')
    print()
    
    script_path = Path('scrcpy_client_v2.1.py')
    if not script_path.exists():
        log(f"Script not found: {script_path}", 'ERROR')
        return False
    
    output_dir = Path('dist')
    spec_file = Path('scrcpy_client_v2.1.spec')
    build_dir = Path('build')
    
    # 清理旧的构建
    log("Cleaning old build files...", 'INFO')
    for path in [output_dir, build_dir, spec_file]:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
                log(f"Removed directory: {path}", 'DEBUG')
            else:
                path.unlink()
                log(f"Removed file: {path}", 'DEBUG')
    
    print()
    
    # 构建命令
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name', 'scrcpy_client_v2.1',
        '--onefile',  # 打包成单个文件
        '--windowed',  # 无控制台窗口
        '--icon', 'google.png' if Path('google.png').exists() else None,
        '--add-data', f'{Path(".").absolute()}/config_manager.py:.',
        '--add-data', f'{Path(".").absolute()}/log_manager.py:.',
        '--add-data', f'{Path(".").absolute()}/exceptions.py:.',
        '--hidden-import=PyQt5',
        '--hidden-import=cv2',
        '--hidden-import=numpy',
        str(script_path)
    ]
    
    # 移除 None 值
    cmd = [c for c in cmd if c is not None]
    
    log("PyInstaller command:", 'DEBUG')
    log(" ".join(cmd), 'DEBUG')
    print()
    
    try:
        log("Starting PyInstaller build...", 'INFO')
        result = subprocess.run(cmd, check=False, capture_output=False)
        
        if result.returncode != 0:
            log("PyInstaller build failed", 'ERROR')
            return False
        
        # 检查输出文件
        exe_path = output_dir / 'scrcpy_client_v2.1.exe'
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            log(f"EXE built successfully: {exe_path} ({size_mb:.2f} MB)", 'SUCCESS')
            return True
        else:
            log("EXE file not found in output directory", 'ERROR')
            return False
            
    except Exception as e:
        log(f"Build error: {e}", 'ERROR')
        return False


def create_launcher_batch():
    """创建启动批处理文件"""
    log("Creating launcher batch file...", 'INFO')
    
    batch_content = '''@echo off
REM Native Mirroring Pro v2.1 启动脚本
REM 启动 scrcpy_client_v2.1.exe

setlocal enabledelayedexpansion

cd /d "%~dp0"

REM 检查 EXE 是否存在
if not exist "dist\\scrcpy_client_v2.1.exe" (
    echo 错误: EXE 文件未找到
    echo 请先运行: python build_exe_v2.1.py
    pause
    exit /b 1
)

REM 启动应用
echo 启动 Native Mirroring Pro v2.1...
start "" "dist\\scrcpy_client_v2.1.exe"

exit /b 0
'''
    
    batch_path = Path('start_v2.1.bat')
    batch_path.write_text(batch_content, encoding='utf-8')
    log(f"Launcher created: {batch_path}", 'SUCCESS')
    return True


def create_readme():
    """创建 README 文件"""
    log("Creating README file...", 'INFO')
    
    readme_content = '''# Native Mirroring Pro v2.1 EXE 版本

## 📋 文件说明

- `scrcpy_client_v2.1.exe` - 完整的应用程序
  - 包含所有依赖
  - 无需 Python 环境
  - 即开即用

## 🚀 使用方法

### 方式 1: 直接运行
双击 `scrcpy_client_v2.1.exe` 启动应用

### 方式 2: 批处理启动
运行 `start_v2.1.bat` 启动应用

### 方式 3: 命令行启动
```bash
dist\\scrcpy_client_v2.1.exe
```

## 📦 系统要求

- Windows 7 或更高版本
- USB 驱动程序（用于 Android 设备）
- adb.exe（已包含在项目中）
- scrcpy-server.jar（已包含在项目中）

## 🔧 功能说明

### 核心功能
- ✅ USB 设备连接
- ✅ 实时视频流显示
- ✅ 触摸事件转发
- ✅ 按键事件支持
- ✅ 自动设备检测
- ✅ 完善的错误处理

### 新增功能 (v2.1)
- ✨ 完整的异常处理框架
- ✨ 灵活的日志管理系统
- ✨ 强大的配置管理系统
- ✨ 改进的视频解码器
- ✨ 规范的代码质量
- ✨ 详细的技术文档

## 📝 日志文件

应用日志保存在: `scrcpy_enhanced.log`

查看日志命令:
```bash
type scrcpy_enhanced.log
```

或者用记事本打开

## 🐛 常见问题

**Q: 应用无法启动？**  
A: 查看 `scrcpy_enhanced.log` 了解错误信息

**Q: 无法检测到设备？**  
A: 
1. 确保 USB 驱动已安装
2. 设备已启用 USB 调试
3. 检查 USB 连接

**Q: 视频显示黑屏？**  
A:
1. 解锁您的 Android 设备
2. 允许应用屏幕截图权限
3. 检查网络连接（WiFi 模式）

## 📚 文档

更多详细信息请参考:
- `FINAL_IMPROVEMENTS_SUMMARY.md` - 改进总结
- `IMPROVEMENT_REPORT.md` - 完整报告
- `FILE_INDEX_IMPROVEMENTS.md` - 文件索引

## 🔄 更新日志

### v2.1.0 (2026-02-08)
- ✨ 新增异常处理框架
- ✨ 新增日志管理系统
- ✨ 新增配置管理系统
- 🔧 改进视频解码器
- 🔧 改进代码规范
- 📝 新增完整文档

### v2.0.0 (原始版本)
- 基础的 USB 投屏功能
- PyQt5 GUI 界面
- 设备列表和连接管理

## 💡 高级用法

### 命令行参数
```bash
scrcpy_client_v2.1.exe [选项]
```

### 配置文件
修改 `config.json` 自定义设置:
```json
{
  "device": {
    "auto_detect": true,
    "connection_timeout": 10
  },
  "video": {
    "bitrate": 8000000,
    "fps": 30
  }
}
```

## 📞 技术支持

如遇问题，请:
1. 查看日志文件
2. 参考项目文档
3. 检查依赖和驱动

## 📄 许可证

本项目遵循相关开源许可证

---

**版本**: 2.1.0  
**编译日期**: 2026-02-08  
**应用状态**: ✅ 生产就绪  

感谢使用 Native Mirroring Pro!
'''
    
    readme_path = Path('README_EXE_v2.1.md')
    readme_path.write_text(readme_content, encoding='utf-8')
    log(f"README created: {readme_path}", 'SUCCESS')
    return True


def verify_exe():
    """验证 EXE 文件"""
    log("Verifying EXE file...", 'INFO')
    
    exe_path = Path('dist') / 'scrcpy_client_v2.1.exe'
    
    if not exe_path.exists():
        log(f"EXE not found: {exe_path}", 'ERROR')
        return False
    
    # 检查文件大小
    size_bytes = exe_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    
    log(f"EXE file verified", 'SUCCESS')
    log(f"  Path: {exe_path.absolute()}", 'DEBUG')
    log(f"  Size: {size_mb:.2f} MB", 'DEBUG')
    
    return True


def main():
    """主函数"""
    print("=" * 80)
    print("  Native Mirroring Pro v2.1 - EXE Builder")
    print("=" * 80)
    print()
    
    # 检查 Python 版本
    if not check_python_version():
        return False
    
    print()
    
    # 检查和安装依赖
    if not check_and_install_dependencies():
        log("Dependency check failed", 'ERROR')
        return False
    
    print()
    
    # 构建 EXE
    if not build_exe():
        log("EXE build failed", 'ERROR')
        return False
    
    print()
    
    # 创建启动脚本
    if not create_launcher_batch():
        log("Launcher creation failed", 'WARNING')
    
    print()
    
    # 创建 README
    if not create_readme():
        log("README creation failed", 'WARNING')
    
    print()
    
    # 验证 EXE
    if not verify_exe():
        log("EXE verification failed", 'ERROR')
        return False
    
    print()
    print("=" * 80)
    log("✓ EXE build completed successfully!", 'SUCCESS')
    print("=" * 80)
    print()
    log("Next steps:", 'INFO')
    print(f"  1. Run: dist\\scrcpy_client_v2.1.exe")
    print(f"  2. Or: start_v2.1.bat")
    print()
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
