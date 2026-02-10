#!/usr/bin/env python3
"""
自动化测试脚本
模拟完整的连接和视频流接收过程
"""
import socket
import subprocess
import struct
import time
import sys

def run_test():
    """运行完整的连接测试"""
    device = "APH7N19507009494"
    adb = "adb.exe"
    
    print("=" * 70)
    print("🧪 Scrcpy Full Connection Test")
    print("=" * 70)
    
    # Step 1: 推送 JAR
    print("\n[1/6] Pushing JAR...")
    try:
        result = subprocess.run(
            [adb, "-s", device, "push", "scrcpy-server.jar", "/data/local/tmp/"],
            capture_output=True, text=True, timeout=30, creationflags=0x08000000
        )
        print(f"✓ {result.stdout.strip()}")
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    time.sleep(1)
    
    # Step 2: 设置端口转发
    print("\n[2/6] Setting up port forwarding...")
    try:
        subprocess.run(
            [adb, "-s", device, "forward", "tcp:27183", "tcp:27183"],
            capture_output=True, timeout=5, creationflags=0x08000000
        )
        print("✓ Port forwarding set up (tcp:27183)")
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    # Step 3: 启动 Scrcpy Server
    print("\n[3/6] Starting Scrcpy Server v3.3.3...")
    try:
        cmd = [
            adb, "-s", device, "shell",
            "CLASSPATH=/data/local/tmp/scrcpy-server.jar app_process / com.genymobile.scrcpy.Server 3.3.3"
        ]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=0x08000000
        )
        time.sleep(3)
        print("✓ Server started")
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    
    # Step 4: 连接到 Socket
    print("\n[4/6] Connecting to localhost:27183...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('127.0.0.1', 27183))
        print("✓ Socket connected!")
    except ConnectionRefusedError:
        print("✗ Connection refused - Server may not be ready")
        proc.terminate()
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        proc.terminate()
        return False
    
    # Step 5: 握手
    print("\n[5/6] Performing handshake...")
    try:
        sock.settimeout(5)
        
        # 接收设备名 (64 字节)
        device_name = sock.recv(64)
        print(f"Device: {device_name[:32].decode('utf-8', errors='ignore')}")
        
        # 接收分辨率 (8 字节: 宽高各 4 字节)
        res_data = sock.recv(8)
        if len(res_data) == 8:
            w, h = struct.unpack('>II', res_data)
            print(f"Resolution: {w}x{h}")
            print("✓ Handshake successful!")
        else:
            print(f"✗ Unexpected resolution data length: {len(res_data)}")
            sock.close()
            proc.terminate()
            return False
        
        sock.settimeout(None)  # 设置为非阻塞
    except socket.timeout:
        print("✗ Handshake timeout")
        sock.close()
        proc.terminate()
        return False
    except Exception as e:
        print(f"✗ Handshake error: {e}")
        sock.close()
        proc.terminate()
        return False
    
    # Step 6: 接收视频帧
    print("\n[6/6] Receiving video frames...")
    try:
        sock.settimeout(10)
        frames_received = 0
        total_bytes = 0
        
        for frame_num in range(10):  # 接收最多 10 帧
            try:
                # 读取帧头 (4 字节大小 + 1 字节类型)
                header = sock.recv(5)
                if len(header) < 5:
                    print(f"Connection closed after {frames_received} frames")
                    break
                
                size = struct.unpack('>I', header[:4])[0]
                frame_type = header[4]
                
                print(f"  Frame {frame_num}: type=0x{frame_type:02x}, size={size} bytes", end='')
                
                # 读取帧数据
                frame_data = b''
                while len(frame_data) < size:
                    chunk = sock.recv(min(65536, size - len(frame_data)))
                    if not chunk:
                        print(" [INCOMPLETE]")
                        break
                    frame_data += chunk
                
                if len(frame_data) == size:
                    frames_received += 1
                    total_bytes += size
                    print(" ✓")
                else:
                    print(f" ✗ (got {len(frame_data)}/{size} bytes)")
                
                if frames_received >= 3:
                    break
                    
            except socket.timeout:
                print(f"  [Timeout after {frames_received} frames]")
                break
            except Exception as e:
                print(f"  [Error: {e}]")
                break
        
        if frames_received > 0:
            print(f"\n✓ Successfully received {frames_received} frames ({total_bytes} bytes)")
            sock.close()
            proc.terminate()
            return True
        else:
            print("\n✗ No frames received")
            sock.close()
            proc.terminate()
            return False
            
    except Exception as e:
        print(f"✗ Error receiving frames: {e}")
        sock.close()
        proc.terminate()
        return False

def main():
    print("\n" + "=" * 70)
    print("Starting Scrcpy Connection Test...")
    print("Make sure your phone is connected and USB debugging is enabled!")
    print("=" * 70)
    
    success = run_test()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ TEST PASSED - Scrcpy is working correctly!")
        print("You can now use the GUI client to view your phone screen.")
    else:
        print("❌ TEST FAILED - There are connection issues.")
        print("\nTroubleshooting steps:")
        print("1. Ensure your phone is connected via USB")
        print("2. Enable USB Debugging on your phone")
        print("3. Authorize the computer on your phone")
        print("4. Try restarting ADB: adb kill-server && adb start-server")
    print("=" * 70 + "\n")
    
    input("Press ENTER to exit...")

if __name__ == '__main__':
    main()
