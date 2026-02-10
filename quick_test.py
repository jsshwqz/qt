#!/usr/bin/env python3
"""
快速连接测试
"""
import socket
import time

def test():
    print("尝试连接到 127.0.0.1:27183...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('127.0.0.1', 27183))
        print("✓ 连接成功！")
        
        # 尝试接收数据
        data = sock.recv(1024)
        print(f"收到数据: {len(data)} 字节")
        print(f"数据内容 (hex): {data[:64].hex()}")
        
        sock.close()
        return True
    except ConnectionRefusedError:
        print("✗ 连接被拒绝 - 服务器未运行")
        return False
    except socket.timeout:
        print("✗ 连接超时")
        return False
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False

if __name__ == '__main__':
    test()
