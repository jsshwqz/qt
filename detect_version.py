#!/usr/bin/env python3
"""
Scrcpy 版本检测和启动工具
自动检测 JAR 版本并使用正确的版本号启动
"""
import subprocess
import zipfile
import json
import os

def get_jar_version():
    """从 scrcpy-server.jar 中检测版本号"""
    try:
        with zipfile.ZipFile('scrcpy-server.jar', 'r') as zf:
            # 查找 version.txt 或 AndroidManifest.xml
            if 'com/genymobile/scrcpy/version.txt' in zf.namelist():
                with zf.open('com/genymobile/scrcpy/version.txt') as f:
                    return f.read().decode().strip()
            
            # 尝试从其他地方读取版本
            for name in zf.namelist():
                if 'version' in name.lower():
                    print(f"Found version file: {name}")
                    try:
                        with zf.open(name) as f:
                            content = f.read().decode('utf-8', errors='ignore')
                            # 提取版本号（简单匹配）
                            for line in content.split('\n'):
                                if 'version' in line.lower():
                                    print(line)
                    except:
                        pass
    except Exception as e:
        print(f"Cannot read JAR: {e}")
    
    return None

def detect_version_from_jar_file():
    """通过检查 JAR 文件属性检测版本"""
    try:
        # 使用 JAR 文件修改时间和大小推断版本
        size = os.path.getsize('scrcpy-server.jar')
        
        # 已知的版本大小映射（可能不准确但作为备选）
        version_sizes = {
            90164: '3.3.3',
            89000: '3.3.0',
            88000: '2.4',
            87000: '2.0'
        }
        
        for sz, ver in version_sizes.items():
            if abs(size - sz) < 1000:
                return ver
    except:
        pass
    
    return None

def test_connection_with_version(version):
    """测试指定版本是否能连接"""
    print(f"\nTesting version: {version}")
    
    device = "APH7N19507009494"
    adb = "adb.exe"
    
    try:
        # 设置端口转发
        subprocess.run([adb, "-s", device, "forward", "tcp:27183", "tcp:27183"], 
                      capture_output=True, timeout=5)
        
        # 启动服务
        import socket
        import struct
        import time
        
        cmd = [
            adb, "-s", device, "shell",
            f"CLASSPATH=/data/local/tmp/scrcpy-server.jar app_process / com.genymobile.scrcpy.Server {version}"
        ]
        
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(2)
        
        # 尝试连接
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect(('127.0.0.1', 27183))
            
            # 握手
            device_name = sock.recv(64)
            res_data = sock.recv(8)
            
            if len(res_data) == 8:
                w, h = struct.unpack('>II', res_data)
                print(f"✅ Version {version} works! Resolution: {w}x{h}")
                sock.close()
                proc.terminate()
                return True
        except:
            pass
        
        proc.terminate()
        
    except Exception as e:
        print(f"Error testing version {version}: {e}")
    
    return False

def main():
    """主函数"""
    print("=" * 60)
    print("🔍 Scrcpy Version Detection Tool")
    print("=" * 60)
    
    # 尝试从 JAR 读取版本
    version = get_jar_version()
    
    if not version:
        print("\nTrying to detect version from JAR file size...")
        version = detect_version_from_jar_file()
    
    if not version:
        print("\n⚠️  Could not auto-detect version")
        print("Trying common versions...")
        
        # 尝试常见版本
        for v in ['3.3.3', '3.3.0', '2.4', '2.0']:
            if test_connection_with_version(v):
                version = v
                break
    else:
        print(f"\n✅ Detected version: {version}")
        test_connection_with_version(version)
    
    if version:
        print(f"\n✅ Ready to use version: {version}")
    else:
        print("\n❌ Could not determine working version")

if __name__ == '__main__':
    main()
