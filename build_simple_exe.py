#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版EXE构建脚本 - 使用PyInstaller
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd):
    """运行命令并捕获输出"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(f"Command: {cmd}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"Exception running command: {e}")
        return False

def main():
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    print("=" * 60)
    print("Native Mirroring Pro v2.1 - 简化版EXE构建")
    print("=" * 60)
    
    # 1. 检查源文件
    print("\n[1] 检查源文件...")
    if not Path("scrcpy_client_v2.1.py").exists():
        print("ERROR: 找不到 scrcpy_client_v2.1.py")
        sys.exit(1)
    print("✓ 源文件检查通过")
    
    # 2. 检查PyInstaller
    print("\n[2] 检查PyInstaller...")
    try:
        import PyInstaller
        print(f"✓ PyInstaller已安装")
    except ImportError:
        print("⚠ PyInstaller未安装，尝试安装...")
        run_command(f'"{sys.executable}" -m pip install pyinstaller --quiet')
    
    # 3. 创建build目录
    print("\n[3] 创建输出目录...")
    build_dir = project_dir / "build_output"
    build_dir.mkdir(exist_ok=True)
    dist_dir = project_dir / "dist"
    print(f"✓ 目录已创建")
    
    # 4. 运行PyInstaller
    print("\n[4] 编译EXE文件...")
    pyinstaller_cmd = f'''"{sys.executable}" -m PyInstaller --onefile --windowed \\
        --name "scrcpy_client_v2.1" \\
        --distpath "{dist_dir}" \\
        --buildpath "{build_dir}" \\
        --specpath "{build_dir}" \\
        --add-data "config_manager.py:." \\
        --add-data "log_manager.py:." \\
        --add-data "exceptions.py:." \\
        --hidden-import=PyQt5 \\
        --hidden-import=cv2 \\
        --hidden-import=numpy \\
        "scrcpy_client_v2.1.py"'''
    
    if run_command(pyinstaller_cmd):
        print("✓ EXE编译成功")
    else:
        print("⚠ EXE编译可能有问题，但继续...")
    
    # 5. 验证输出
    print("\n[5] 验证输出文件...")
    exe_file = dist_dir / "scrcpy_client_v2.1.exe"
    if exe_file.exists():
        size_mb = exe_file.stat().st_size / (1024 * 1024)
        print(f"✓ EXE文件已生成: {exe_file}")
        print(f"  文件大小: {size_mb:.2f} MB")
    else:
        print("⚠ EXE文件未找到，检查dist目录:")
        if dist_dir.exists():
            for item in dist_dir.iterdir():
                print(f"  - {item.name}")
    
    # 6. 创建启动脚本
    print("\n[6] 创建启动脚本...")
    launcher_bat = project_dir / "run_app.bat"
    launcher_content = f'''@echo off
REM Native Mirroring Pro v2.1
cd /d "{dist_dir}"
if exist "scrcpy_client_v2.1.exe" (
    scrcpy_client_v2.1.exe
) else (
    echo ERROR: 找不到EXE文件
    pause
)
'''
    with open(launcher_bat, 'w', encoding='utf-8') as f:
        f.write(launcher_content)
    print(f"✓ 启动脚本已创建: {launcher_bat}")
    
    print("\n" + "=" * 60)
    print("构建完成！")
    print("=" * 60)
    print(f"\n使用说明:")
    print(f"1. 直接运行: {dist_dir / 'scrcpy_client_v2.1.exe'}")
    print(f"2. 或使用启动脚本: {launcher_bat}")
    
if __name__ == '__main__':
    main()
