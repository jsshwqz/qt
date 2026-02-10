#!/usr/bin/env python3
"""
AndroidMirror Windows EXE 打包脚本
用于将 Electron 应用打包为独立的 Windows 可执行文件

使用方法:
    python build_exe.py

注意事项:
    - 需要安装 PyInstaller: pip install pyinstaller
    - 需要在 Windows 环境下运行
    - 确保有足够的磁盘空间 (约 2-3 GB)
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def check_dependencies():
    """检查必要的依赖是否已安装"""
    print("检查依赖...")
    
    try:
        import PyInstaller
        print("  ✓ PyInstaller 已安装")
    except ImportError:
        print("  ✗ PyInstaller 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("  ✓ PyInstaller 安装完成")
    
    print("依赖检查完成\n")


def clean_dist():
    """清理旧的构建文件"""
    dist_path = Path("dist")
    build_path = Path("build")
    spec_path = Path("AndroidMirror.spec")
    
    if dist_path.exists():
        print("清理 dist 目录...")
        shutil.rmtree(dist_path)
    
    if build_path.exists():
        print("清理 build 目录...")
        shutil.rmtree(build_path)
    
    if spec_path.exists():
        print("清理 .spec 文件...")
        spec_path.unlink()
    
    print("清理完成\n")


def create_spec_file():
    """创建 PyInstaller spec 文件"""
    print("创建 spec 文件...")
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for AndroidMirror

from PyInstaller.utils.hooks import collect_all
from PyInstaller.building.build_main import Analysis, PYZ, EXE

block_cipher = None

a = Analysis(
    ['main.js'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('src', 'src'),
        ('resources', 'resources'),
    ],
    hiddenimports=[
        'electron',
        'child_process',
        'fs',
        'path',
        'os',
        'net',
        'tls',
        'crypto',
        'buffer',
        'stream',
        'events',
        'url',
        'querystring',
        'http',
        'https',
        'zlib',
        'util',
        'string_decoder',
        'v8',
        'uv',
        'nghttp2',
        'node_modules',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AndroidMirror',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='x64',
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icon.ico',
)
'''
    
    with open("AndroidMirror.spec", "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    print("  spec 文件创建完成\n")


def build_executable():
    """构建可执行文件"""
    print("开始构建 EXE 文件...")
    print("=" * 50)
    print("注意: 首次构建可能需要较长时间下载依赖")
    print("=" * 50)
    print()
    
    # 使用 spec 文件构建
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--windowed",
        "--icon=resources/icon.ico",
        "--name=AndroidMirror",
        "--add-data=src;src",
        "--add-data=resources;resources",
        "main.js"
    ]
    
    print("执行命令:", " ".join(cmd))
    print()
    
    result = subprocess.run(cmd, cwd=os.getcwd())
    
    if result.returncode == 0:
        print("\n✓ 构建成功!")
        return True
    else:
        print("\n✗ 构建失败")
        return False


def copy_additional_files():
    """复制额外的必要文件"""
    print("\n复制额外文件...")
    
    dist_path = Path("dist/AndroidMirror-win32-x64")
    
    if not dist_path.exists():
        dist_path = Path("dist/AndroidMirror")
    
    if not dist_path.exists():
        print("  警告: 未找到 dist 目录")
        return
    
    # 复制 ADB 工具（如果存在）
    resources_adb = Path("resources/adb")
    if resources_adb.exists():
        target_adb = dist_path / "adb"
        if target_adb.exists():
            shutil.rmtree(target_adb)
        shutil.copytree(resources_adb, target_adb)
        print(f"  ✓ 复制 ADB 工具到 {target_adb}")
    
    print("额外文件复制完成\n")


def print_summary():
    """打印构建摘要"""
    print("\n" + "=" * 50)
    print("构建完成!")
    print("=" * 50)
    
    exe_path = Path("dist/AndroidMirror.exe")
    exe_path2 = Path("dist/AndroidMirror/AndroidMirror.exe")
    
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n主程序: {exe_path}")
        print(f"文件大小: {size_mb:.2f} MB")
    elif exe_path2.exists():
        size_mb = exe_path2.stat().st_size / (1024 * 1024)
        print(f"\n主程序: {exe_path2}")
        print(f"文件大小: {size_mb:.2f} MB")
    else:
        print("\n警告: 未找到生成的 EXE 文件")
    
    print("\n使用方法:")
    print("  1. 双击 AndroidMirror.exe 启动应用")
    print("  2. 连接 Android 设备并启用 USB 调试")
    print("  3. 在应用中选择设备开始投屏")
    
    print("\n注意事项:")
    print("  - 首次启动可能需要较长时间（解压依赖）")
    print("  - 请确保 Windows Defender 或安全软件允许运行")
    print("  - 需要 ADB 驱动支持（可从 Android SDK 获取）")


def main():
    """主函数"""
    print("\n" + "=" * 50)
    print("AndroidMirror Windows EXE 打包工具")
    print("=" * 50)
    print()
    
    # 获取当前目录
    current_dir = Path(__file__).parent.absolute()
    os.chdir(current_dir)
    print(f"工作目录: {current_dir}")
    print()
    
    try:
        # 检查依赖
        check_dependencies()
        
        # 清理旧文件
        clean_dist()
        
        # 检查必要文件
        if not Path("main.js").exists():
            print("错误: 未找到 main.js 文件")
            print("请确保在 AndroidMirror 项目根目录下运行此脚本")
            sys.exit(1)
        
        if not Path("resources/adb/adb.exe").exists():
            print("警告: 未找到 adb.exe，将无法使用 ADB 功能")
            print("建议从 Android SDK 平台工具获取 adb.exe")
            print()
        
        # 构建可执行文件
        success = build_executable()
        
        if success:
            # 复制额外文件
            copy_additional_files()
            
            # 打印摘要
            print_summary()
        else:
            print("\n构建失败，请检查错误信息")
            print("\n可能的解决方案:")
            print("  1. 确保有足够的磁盘空间（至少 2GB）")
            print("  2. 关闭杀毒软件（可能阻止打包过程）")
            print("  3. 以管理员身份运行此脚本")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
