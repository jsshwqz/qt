#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版 Scrcpy Client 构建脚本
包含完整的错误处理和依赖检查
"""

import os
import sys
import subprocess
import shutil
import json
from pathlib import Path
from datetime import datetime

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'


DEFAULT_MAX_LOCAL_INSTALL_MB = int(os.environ.get('MAX_LOCAL_INSTALL_MB', '1024'))
FORCE_CLOUD_BUILD = os.environ.get('FORCE_CLOUD_BUILD', '0').lower() in ('1', 'true', 'yes')
CLOUD_BUILD_DIR = Path('CloudBuild')

# Rough wheel+dependency footprint estimates used for disk-aware decisions.
PACKAGE_SIZE_ESTIMATE_MB = {
    'PyQt5': 380,
    'opencv-python': 330,
    'numpy': 70,
    'PyInstaller': 120,
}


def log(msg, level='INFO'):
    """记录日志"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    def safe_print(text):
        try:
            print(text)
        except UnicodeEncodeError:
            # Some Windows consoles still use gbk/cp936 and cannot print emoji symbols.
            encoding = getattr(sys.stdout, 'encoding', None) or 'utf-8'
            print(text.encode(encoding, errors='replace').decode(encoding, errors='replace'))

    if level == 'INFO':
        safe_print(f"{Colors.BLUE}[{timestamp}] INFO{Colors.END}: {msg}")
    elif level == 'SUCCESS':
        safe_print(f"{Colors.GREEN}[{timestamp}] ✓{Colors.END}: {msg}")
    elif level == 'WARNING':
        safe_print(f"{Colors.YELLOW}[{timestamp}] ⚠{Colors.END}: {msg}")
    elif level == 'ERROR':
        safe_print(f"{Colors.RED}[{timestamp}] ✗{Colors.END}: {msg}")


def check_python():
    """检查 Python 版本"""
    log(f"Python version: {sys.version}")
    if sys.version_info < (3, 7):
        log("Python 3.7+ required", 'ERROR')
        return False
    return True


def check_package(package_name, pip_name=None):
    """检查包是否安装"""
    if pip_name is None:
        pip_name = package_name
    
    try:
        __import__(package_name)
        log(f"✓ {package_name} available", 'SUCCESS')
        return True
    except ImportError:
        log(f"✗ {package_name} not found", 'WARNING')
        return False


def install_package(pip_name, max_local_install_mb=DEFAULT_MAX_LOCAL_INSTALL_MB):
    """安装包"""
    estimated_mb = PACKAGE_SIZE_ESTIMATE_MB.get(pip_name, 0)
    if estimated_mb > max_local_install_mb:
        log(
            f"Skip local install for {pip_name}: estimated {estimated_mb}MB > limit {max_local_install_mb}MB",
            'WARNING'
        )
        return False

    log(f"Installing {pip_name}...", 'INFO')
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", pip_name],
            check=True
        )
        log(f"✓ {pip_name} installed", 'SUCCESS')
        return True
    except subprocess.CalledProcessError:
        log(f"✗ Failed to install {pip_name}", 'ERROR')
        return False


def estimate_missing_size(missing):
    """估算缺失依赖的安装体积（MB）"""
    return sum(PACKAGE_SIZE_ESTIMATE_MB.get(pip_name, 0) for _, pip_name in missing)


def prepare_cloud_build_workspace(missing, total_estimated_mb, reason):
    """准备云端打包工作区，避免本地安装大体积依赖"""
    log(f"Preparing cloud build workspace ({reason})...", 'INFO')

    if not CLOUD_BUILD_DIR.exists():
        log(f"Cloud build directory not found: {CLOUD_BUILD_DIR}", 'ERROR')
        return False

    files_to_sync = {
        'scrcpy_client_v2.1.py': CLOUD_BUILD_DIR / 'client.py',
        'video_decoder_v2.1.py': CLOUD_BUILD_DIR / 'video_decoder_v2.1.py',
        'adb_manager.py': CLOUD_BUILD_DIR / 'adb_manager.py',
        'config_manager.py': CLOUD_BUILD_DIR / 'config_manager.py',
        'exceptions.py': CLOUD_BUILD_DIR / 'exceptions.py',
        'log_manager.py': CLOUD_BUILD_DIR / 'log_manager.py',
        'requirements.txt': CLOUD_BUILD_DIR / 'requirements.txt',
        'scrcpy-server.jar': CLOUD_BUILD_DIR / 'scrcpy-server.jar',
    }

    for src_name, dst_path in files_to_sync.items():
        src_path = Path(src_name)
        if not src_path.exists():
            log(f"Skip sync (missing): {src_name}", 'WARNING')
            continue
        shutil.copy2(src_path, dst_path)
        log(f"Synced: {src_name} -> {dst_path}", 'SUCCESS')

    request = {
        'timestamp': datetime.now().isoformat(),
        'reason': reason,
        'estimated_missing_dependency_mb': total_estimated_mb,
        'missing_dependencies': [pip_name for _, pip_name in missing],
        'build_entry': 'client.py',
    }
    request_path = CLOUD_BUILD_DIR / 'cloud_build_request.json'
    with open(request_path, 'w', encoding='utf-8') as f:
        json.dump(request, f, indent=2, ensure_ascii=False)
    log(f"Cloud build request saved: {request_path}", 'SUCCESS')
    log("Use CloudBuild/.github workflows or CloudBuild/build.ps1 for remote packaging", 'INFO')
    return True


def check_dependencies(force_cloud=False, max_local_install_mb=DEFAULT_MAX_LOCAL_INSTALL_MB):
    """检查所有依赖"""
    log("Checking dependencies...", 'INFO')
    print()
    
    dependencies = [
        ('PyQt5', 'PyQt5'),
        ('cv2', 'opencv-python'),
        ('numpy', 'numpy'),
    ]
    
    missing = []
    for module, pip_name in dependencies:
        if not check_package(module, pip_name):
            missing.append((module, pip_name))
    
    print()
    
    if missing:
        log(f"Found {len(missing)} missing package(s)", 'WARNING')
        total_estimated_mb = estimate_missing_size(missing)
        log(f"Estimated missing dependency footprint: ~{total_estimated_mb} MB", 'INFO')

        if force_cloud:
            ok = prepare_cloud_build_workspace(
                missing,
                total_estimated_mb,
                'FORCE_CLOUD_BUILD enabled'
            )
            return 'CLOUD' if ok else 'FAILED'

        if total_estimated_mb > max_local_install_mb:
            ok = prepare_cloud_build_workspace(
                missing,
                total_estimated_mb,
                f'estimated footprint exceeds local limit ({max_local_install_mb}MB)'
            )
            return 'CLOUD' if ok else 'FAILED'

        for module, pip_name in missing:
            if not install_package(pip_name, max_local_install_mb=max_local_install_mb):
                return 'FAILED'
    else:
        log("All dependencies available", 'SUCCESS')
    
    return 'LOCAL'


def check_pyinstaller():
    """检查 PyInstaller"""
    log("Checking PyInstaller...", 'INFO')
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--version"],
            capture_output=True,
            text=True
        )
        log(f"PyInstaller {result.stdout.strip()}", 'SUCCESS')
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        log("PyInstaller not found, installing...", 'WARNING')
        return install_package('PyInstaller')


def clean_build_files():
    """清理旧的构建文件"""
    log("Cleaning previous builds...", 'INFO')
    
    dirs_to_remove = ['build', 'dist', '__pycache__']
    files_to_remove = [
        'scrcpy_client_enhanced.spec',
        'scrcpy_enhanced.log'
    ]
    
    for dir_name in dirs_to_remove:
        dir_path = Path(dir_name)
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path)
                log(f"Removed directory: {dir_name}", 'SUCCESS')
            except Exception as e:
                log(f"Failed to remove {dir_name}: {e}", 'WARNING')
    
    for file_name in files_to_remove:
        file_path = Path(file_name)
        if file_path.exists():
            try:
                file_path.unlink()
                log(f"Removed file: {file_name}", 'SUCCESS')
            except Exception as e:
                log(f"Failed to remove {file_name}: {e}", 'WARNING')


def check_required_files():
    """检查必要的文件"""
    log("Checking required files...", 'INFO')
    
    required_files = [
        'scrcpy_client_enhanced.py',
        'adb_manager.py',
        'scrcpy_server.py',
        'adb.exe',
        'scrcpy-server.jar'
    ]
    
    missing = []
    for file_name in required_files:
        if not Path(file_name).exists():
            missing.append(file_name)
            log(f"✗ {file_name} not found", 'WARNING')
        else:
            log(f"✓ {file_name} found", 'SUCCESS')
    
    if missing:
        log(f"Found {len(missing)} missing file(s)", 'ERROR')
        return False
    
    return True


def build_exe():
    """构建 EXE"""
    log("Building executable...", 'INFO')
    print()
    
    # PyInstaller 命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "NativeMirroringPro",
        "--add-data", f"adb.exe{os.pathsep}.",
        "--add-data", f"scrcpy-server.jar{os.pathsep}.",
        "--add-data", f"project_config.json{os.pathsep}.",
        "--hidden-import=PyQt5.sip",
        "--hidden-import=cv2",
        "--hidden-import=numpy",
        "--collect-all=PyQt5",
        "--console",
        "--log-level=INFO"
    ]

    # Optional icon
    if Path("qt_icon.ico").exists():
        cmd.extend(["--icon", "qt_icon.ico"])
        
    # Entry point
    cmd.append("unified_launcher.py")
    
    log(f"Command: {' '.join(cmd)}", 'INFO')
    print()
    
    try:
        result = subprocess.run(cmd, check=True)
        log("Build completed successfully", 'SUCCESS')
        return True
    except subprocess.CalledProcessError as e:
        log(f"Build failed with error code: {e.returncode}", 'ERROR')
        return False


def verify_exe():
    """验证 EXE 文件"""
    log("Verifying executable...", 'INFO')
    
    exe_path = Path('dist') / 'NativeMirroringPro.exe'
    
    if not exe_path.exists():
        log(f"Executable not found: {exe_path}", 'ERROR')
        return False
    
    file_size = exe_path.stat().st_size
    size_mb = file_size / (1024 * 1024)
    
    log(f"Executable created: {exe_path}", 'SUCCESS')
    log(f"File size: {size_mb:.2f} MB", 'INFO')
    
    return True


def create_build_info():
    """创建构建信息文件"""
    log("Creating build info...", 'INFO')
    
    build_info = {
        "name": "scrcpy_client_enhanced",
        "version": "1.0.0",
        "build_date": datetime.now().isoformat(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "description": "Native Android Screen Mirroring Client - Enhanced Version"
    }
    
    info_file = Path('dist') / 'build_info.json'
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(build_info, f, indent=2, ensure_ascii=False)
    
    log(f"Build info saved to {info_file}", 'SUCCESS')


def create_readme():
    """创建 README 文件"""
    readme_content = """# Scrcpy Client Enhanced - User Guide

## Quick Start

### 1. Requirements
- Windows 10 or later
- Android device with USB debugging enabled
- USB cable or WiFi connection

### 2. Installation
1. Download `scrcpy_client_enhanced.exe`
2. Install Android USB drivers (optional, usually automatic)
3. Enable USB debugging on your Android device:
   - Settings > Developer Options > USB Debugging

### 3. Usage
1. Double-click `scrcpy_client_enhanced.exe`
2. Select your device from the list
3. Click "Connect"
4. Wait for the connection to establish
5. Your device screen should appear in the window

## Features
✓ Native Android screen mirroring
✓ USB and WiFi support
✓ Real-time video streaming
✓ Click and gesture input
✓ Built-in ADB support
✓ Enhanced error handling and logging

## Troubleshooting

### "No devices found"
- Check USB connection
- Enable USB debugging in Developer Options
- Install appropriate USB drivers

### Connection fails
- Check if device is properly authorized
- Try unplugging and re-plugging USB cable
- Check `scrcpy_enhanced.log` for detailed error messages

### Window crashes
- Check log file for errors
- Try running from Administrator command prompt
- Update graphics drivers

## Logs
Detailed logs are saved in `scrcpy_enhanced.log`

## Support
For issues and support, check the logs or contact support.
"""
    
    readme_file = Path('dist') / 'README.txt'
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    log(f"README created: {readme_file}", 'SUCCESS')


def main():
    """主构建流程"""
    force_cloud = FORCE_CLOUD_BUILD or ('--cloud' in sys.argv)
    max_local_install_mb = DEFAULT_MAX_LOCAL_INSTALL_MB

    print("\n" + "=" * 60)
    print("   Scrcpy Client Enhanced - Build System")
    print("=" * 60 + "\n")
    log(f"Cloud build forced: {force_cloud}", 'INFO')
    log(f"Max local install budget: {max_local_install_mb} MB", 'INFO')
    
    # 1. 检查 Python
    if not check_python():
        return False
    
    print()
    
    # 2. 检查依赖
    dep_status = check_dependencies(force_cloud=force_cloud, max_local_install_mb=max_local_install_mb)
    if dep_status == 'FAILED':
        log("Cannot proceed without dependencies", 'ERROR')
        return False
    if dep_status == 'CLOUD':
        print("\n" + "=" * 60)
        log("Cloud build package prepared successfully", 'SUCCESS')
        log("No heavy local installation performed", 'SUCCESS')
        print("=" * 60)
        return True
    
    print()
    
    # 3. 检查 PyInstaller
    if not check_pyinstaller():
        log("Cannot proceed without PyInstaller", 'ERROR')
        return False
    
    print()
    
    # 4. 检查必要文件
    if not check_required_files():
        log("Cannot proceed without required files", 'ERROR')
        return False
    
    print()
    
    # 5. 清理旧构建
    clean_build_files()
    
    print()
    
    # 6. 构建 EXE
    if not build_exe():
        log("Build failed", 'ERROR')
        return False
    
    print()
    
    # 7. 验证 EXE
    if not verify_exe():
        log("Verification failed", 'ERROR')
        return False
    
    print()
    
    # 8. 创建辅助文件
    create_build_info()
    create_readme()
    
    print("\n" + "=" * 60)
    log("Build completed successfully!", 'SUCCESS')
    print("=" * 60)
    print()
    log("Next steps:", 'INFO')
    log("1. Run: dist/scrcpy_client_enhanced.exe", 'INFO')
    log("2. Check scrcpy_enhanced.log for debug info", 'INFO')
    
    return True


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nBuild cancelled by user")
        sys.exit(1)
    except Exception as e:
        log(f"Unexpected error: {e}", 'ERROR')
        import traceback
        traceback.print_exc()
        sys.exit(1)
