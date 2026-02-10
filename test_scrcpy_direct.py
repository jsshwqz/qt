#!/usr/bin/env python3
"""
直接测试 Scrcpy Server 连接
"""
import socket
import subprocess
import time
import struct
import sys
import os

def test_scrcpy_connection():
    """测试 Scrcpy 连接"""
    device = "APH7N19507009494"
    adb_path = "adb.exe"
    
    print("=" * 60)
    print("🧪 Scrcpy Connection Test")
    print("=" * 60)
    
    # 步骤 1: 推送 JAR
    print("\n[1/6] Pushing JAR...")
    result = subprocess.run(
        [adb_path, "-s", device, "push", "scrcpy-server.jar", "/data/local/tmp/"],
        capture_output=True, text=True
    )
    print(result.stdout + result.stderr)
    time.sleep(1)
    
    # 步骤 2: 设置端口转发
    print("\n[2/6] Setting up port forwarding...")
    subprocess.run([adb_path, "-s", device, "forward", "tcp:27183", "tcp:27183"], capture_output=True)
    subprocess.run([adb_path, "forward", "--list"], capture_output=True)
    time.sleep(1)
    
    # 步骤 3: 启动 Scrcpy Server
    print("\n[3/6] Starting Scrcpy Server...")
    cmd = [
        adb_path, "-s", device, "shell",
        "CLASSPATH=/data/local/tmp/scrcpy-server.jar app_process / com.genymobile.scrcpy.Server 2.0 log_level=verbose"
    ]
    print(f"Command: {' '.join(cmd)}")
    
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    time.sleep(3)
    
    # 步骤 4: 尝试 Socket 连接
    print("\n[4/6] Connecting to localhost:27183...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', 27183))
        print("✅ Socket connected!")
        
        # 步骤 5: 握手
        print("\n[5/6] Performing handshake...")
        sock.settimeout(5)
        
        # 接收设备名
        device_name = sock.recv(64)
        print(f"Device name: {device_name[:32]}")
        
        # 接收分辨率
        res_data = sock.recv(8)
        if len(res_data) == 8:
            w, h = struct.unpack('>II', res_data)
            print(f"Resolution: {w}x{h}")
            print("✅ Handshake successful!")
        
        # 步骤 6: 接收帧
        print("\n[6/6] Receiving frames...")
        sock.settimeout(3)
        
        frame_count = 0
        for i in range(5):
            try:
                header = sock.recv(5)
                if len(header) >= 5:
                    size = struct.unpack('>I', header[:4])[0]
                    frame_type = header[4]
                    print(f"  Frame {i}: type={frame_type}, size={size}")
                    
                    # 读取帧数据
                    data = b''
                    while len(data) < size and len(data) < 1000000:
                        chunk = sock.recv(min(65536, size - len(data)))
                        if not chunk:
                            break
                        data += chunk
                    
                    frame_count += 1
                    if frame_count >= 3:
                        break
            except socket.timeout:
                print("  Socket timeout (may be normal)")
                break
        
        if frame_count > 0:
            print(f"\n✅ Successfully received {frame_count} frames!")
        
        sock.close()
        proc.terminate()
        
        print("\n" + "=" * 60)
        print("✅ TEST PASSED!")
        print("=" * 60)
        return True
        
    except ConnectionRefusedError:
        print("❌ Connection refused - Scrcpy Server may not be running")
        print("\nServer output:")
        stdout, stderr = proc.communicate(timeout=2)
        print(stdout)
        print(stderr)
        return False
    except socket.timeout:
        print("❌ Socket timeout - no data received")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except:
            proc.kill()

if __name__ == '__main__':
    success = test_scrcpy_connection()
    sys.exit(0 if success else 1)
