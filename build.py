#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build script for Native Mirroring Pro
Creates a standalone executable with all dependencies included.
"""

import os
import sys
import subprocess
import shutil


def main():
    """Main build function."""
    print("=== Native Mirroring Pro Build Script ===")
    print()
    
    # Check PyInstaller is installed
    try:
        subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], 
                    check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ PyInstaller not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], 
                    check=True)
        print("✅ PyInstaller installed")
    
    # Clean previous builds
    print("\n🧹 Cleaning previous builds...")
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    if os.path.exists("Native_Mirroring_Pro.spec"):
        os.remove("Native_Mirroring_Pro.spec")
    print("✅ Cleaned previous builds")
    
    # Check for required files
    print("\n📋 Checking required files...")
    required_files = [
        "wifi_mirroring_final.py",
        "adb_manager.py",
        "scrcpy_server.py",
        "h264_stream_parser.py",
        "video_decoder.py",
        "control_socket.py",
        "coordinate_transformer.py"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return 1
    
    print("✅ All required files found")
    
    # Check for optional assets
    print("\n📦 Checking for optional assets...")
    assets_found = []
    if os.path.exists("adb.exe"):
        assets_found.append("adb.exe")
    if os.path.exists("scrcpy-server.jar"):
        assets_found.append("scrcpy-server.jar")
    
    if assets_found:
        print(f"✅ Found assets: {', '.join(assets_found)}")
    else:
        print("⚠️ No assets found - will need to bundle separately")
    
    # Build executable
    print("\n🔨 Building executable...")
    build_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--uac-admin",
        "--collect-all", "cv2",
        "--collect-all", "PyQt5",
        "--name=Native_Mirroring_Pro",
        "--windowed",
        "--icon=NONE",
        "--add-data=adb.exe;." if os.path.exists("adb.exe") else "",
        "--add-data=scrcpy-server.jar;." if os.path.exists("scrcpy-server.jar") else "",
        "wifi_mirroring_final.py"
    ]
    
    # Remove empty args
    build_cmd = [arg for arg in build_cmd if arg]
    
    try:
        subprocess.run(build_cmd, check=True)
        print("✅ Build completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return 1
    
    # Check output
    exe_path = os.path.join("dist", "Native_Mirroring_Pro.exe")
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\n📦 Build output: {exe_path}")
        print(f"📏 Size: {size_mb:.1f} MB")
        
        # Show post-build instructions
        print("\n📋 Post-build instructions:")
        print("1. Test the executable in dist/")
        print("2. If adb.exe and scrcpy-server.jar are not bundled:")
        print("   - Copy them to the same directory as the EXE")
        print("   - Or place them in QtScrcpy-win-x64-v3.3.3/")
        print("3. Distribute the entire dist/ folder")
        
        # Optional: Create distribution folder
        if assets_found:
            print("\n📦 Creating distribution package...")
            dist_folder = "Native_Mirroring_Pro_Distribution"
            if os.path.exists(dist_folder):
                shutil.rmtree(dist_folder)
            
            os.makedirs(dist_folder)
            shutil.copy(exe_path, dist_folder)
            if os.path.exists("adb.exe"):
                shutil.copy("adb.exe", dist_folder)
            if os.path.exists("scrcpy-server.jar"):
                shutil.copy("scrcpy-server.jar", dist_folder)
            
            # Create README
            readme_content = """Native Mirroring Pro - 原生投屏专业版

使用说明：
1. 用USB线连接手机和电脑
2. 手机开启"开发者选项" -> "USB调试"
3. 运行 Native_Mirroring_Pro.exe
4. 点击"刷新"选择设备，然后点击"连接"

如果程序无法找到ADB：
- 将 adb.exe 和 scrcpy-server.jar 复制到程序同一目录
- 或放置在 QtScrcpy-win-x64-v3.3.3/ 目录中

技术支持：100% 自研代码，无需安装 QtScrcpy
"""
            
            with open(os.path.join(dist_folder, "README.txt"), "w", encoding="utf-8") as f:
                f.write(readme_content)
            
            print(f"✅ Distribution package created: {dist_folder}/")
        
        return 0
    else:
        print("❌ Executable not found in dist/")
        return 1


if __name__ == "__main__":
    sys.exit(main())