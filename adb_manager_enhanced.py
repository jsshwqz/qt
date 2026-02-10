#!/usr/bin/env python3
"""
ADB 管理器 - 增强版
支持设备列表更新、无线连接、错误恢复
"""
import subprocess
import os
import sys
import logging
import threading
import time
from typing import List, Optional

logger = logging.getLogger(__name__)


class AdbServerManager:
    """改进的 ADB 服务器管理器"""
    
    def __init__(self):
        self.adb_path = self._find_adb()
        self.server_running = False
        self.device_list = []
        logger.info(f'AdbServerManager 初始化，ADB路径: {self.adb_path}')
    
    def _find_adb(self) -> str:
        """查找 ADB 可执行文件"""
        # 1. 检查当前目录
        if os.path.exists("adb.exe"):
            return os.path.abspath("adb.exe")
        
        # 2. 检查系统 PATH
        try:
            result = subprocess.run(['where', 'adb'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        
        # 3. 使用默认路径
        default_paths = [
            r'E:\Program Files\qt\QtScrcpy-Release\QtScrcpy-win-x64-v3.3.3\adb.exe',
            r'C:\Program Files\Android\Android SDK\platform-tools\adb.exe',
            r'C:\Program Files (x86)\Android\android-sdk\platform-tools\adb.exe'
        ]
        
        for path in default_paths:
            if os.path.exists(path):
                return os.path.abspath(path)
        
        # 如果都找不到，返回默认值
        logger.warning('未能找到 ADB，使用默认路径')
        return 'adb.exe'
    
    def start_server(self) -> bool:
        """启动 ADB 服务"""
        try:
            logger.info('启动 ADB 服务...')
            result = subprocess.run(
                [self.adb_path, 'start-server'],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=0x08000000  # 隐藏窗口
            )
            
            if result.returncode == 0:
                self.server_running = True
                logger.info('ADB 服务已启动')
                return True
            else:
                logger.warning(f'ADB 服务启动失败: {result.stderr}')
                return False
                
        except subprocess.TimeoutExpired:
            logger.error('ADB 服务启动超时')
            return False
        except FileNotFoundError:
            logger.error(f'ADB 可执行文件未找到: {self.adb_path}')
            return False
        except Exception as e:
            logger.error(f'ADB 服务启动异常: {e}')
            return False
    
    def list_devices(self) -> List[str]:
        """列出已连接的设备"""
        try:
            logger.debug('列出设备...')
            result = subprocess.run(
                [self.adb_path, 'devices'],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=0x08000000
            )
            
            devices = []
            lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
            
            for line in lines:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == 'device':
                    devices.append(parts[0])
            
            self.device_list = devices
            logger.info(f'发现 {len(devices)} 个设备: {devices}')
            return devices
            
        except subprocess.TimeoutExpired:
            logger.warning('列出设备超时')
            return []
        except Exception as e:
            logger.error(f'列出设备异常: {e}')
            return []
    
    def forward_port(self, serial: str, local_port: int, remote_port: int) -> bool:
        """设置端口转发"""
        try:
            logger.info(f'设置端口转发: {serial} {local_port}:{remote_port}')
            
            result = subprocess.run(
                [self.adb_path, '-s', serial, 'forward',
                 f'tcp:{local_port}', f'tcp:{remote_port}'],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=0x08000000
            )
            
            if result.returncode == 0:
                logger.info(f'端口转发成功')
                return True
            else:
                logger.warning(f'端口转发失败: {result.stderr}')
                return False
                
        except Exception as e:
            logger.error(f'端口转发异常: {e}')
            return False
    
    def push_file(self, serial: str, local_path: str, remote_path: str) -> bool:
        """推送文件到设备"""
        try:
            logger.info(f'推送文件: {local_path} -> {remote_path}')
            
            result = subprocess.run(
                [self.adb_path, '-s', serial, 'push', local_path, remote_path],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=0x08000000
            )
            
            if result.returncode == 0:
                logger.info('文件推送成功')
                return True
            else:
                logger.warning(f'文件推送失败: {result.stderr}')
                return False
                
        except Exception as e:
            logger.error(f'文件推送异常: {e}')
            return False
    
    def execute_shell(self, serial: str, command: str) -> Optional[str]:
        """在设备上执行 shell 命令"""
        try:
            logger.debug(f'执行 shell 命令: {command}')
            
            result = subprocess.run(
                [self.adb_path, '-s', serial, 'shell'] + command.split(),
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=0x08000000
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.warning(f'Shell 命令执行失败: {result.stderr}')
                return None
                
        except Exception as e:
            logger.error(f'Shell 命令执行异常: {e}')
            return None
    
    def connect_wireless(self, host: str, port: int = 5555) -> bool:
        """无线连接到设备"""
        try:
            logger.info(f'无线连接到设备: {host}:{port}')
            
            result = subprocess.run(
                [self.adb_path, 'connect', f'{host}:{port}'],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=0x08000000
            )
            
            if result.returncode == 0:
                logger.info('无线连接成功')
                return True
            else:
                logger.warning(f'无线连接失败: {result.stderr}')
                return False
                
        except Exception as e:
            logger.error(f'无线连接异常: {e}')
            return False
    
    def disconnect_wireless(self, host: str, port: int = 5555) -> bool:
        """断开无线连接"""
        try:
            logger.info(f'断开无线连接: {host}:{port}')
            
            result = subprocess.run(
                [self.adb_path, 'disconnect', f'{host}:{port}'],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=0x08000000
            )
            
            if result.returncode == 0:
                logger.info('无线连接已断开')
                return True
            else:
                logger.warning(f'断开连接失败: {result.stderr}')
                return False
                
        except Exception as e:
            logger.error(f'断开连接异常: {e}')
            return False
    
    @property
    def path(self) -> str:
        """获取 ADB 路径"""
        return self.adb_path


# 设备监视器（可选）
class DeviceMonitor:
    """设备变化监视器"""
    
    def __init__(self, adb_manager: AdbServerManager, check_interval: float = 2.0):
        self.adb = adb_manager
        self.check_interval = check_interval
        self.running = False
        self.current_devices = set()
        self.on_device_connected = None
        self.on_device_disconnected = None
        self.monitor_thread = None
        
        logger.info('DeviceMonitor 初始化')
    
    def start(self):
        """启动监视"""
        logger.info('启动设备监视...')
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop(self):
        """停止监视"""
        logger.info('停止设备监视...')
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
    
    def _monitor_loop(self):
        """监视循环"""
        while self.running:
            try:
                devices = set(self.adb.list_devices())
                
                # 检查新连接的设备
                new_devices = devices - self.current_devices
                for device in new_devices:
                    logger.info(f'设备已连接: {device}')
                    if self.on_device_connected:
                        try:
                            self.on_device_connected(device)
                        except Exception as e:
                            logger.error(f'设备连接回调失败: {e}')
                
                # 检查断开的设备
                removed_devices = self.current_devices - devices
                for device in removed_devices:
                    logger.info(f'设备已断开: {device}')
                    if self.on_device_disconnected:
                        try:
                            self.on_device_disconnected(device)
                        except Exception as e:
                            logger.error(f'设备断开回调失败: {e}')
                
                self.current_devices = devices
                
            except Exception as e:
                logger.error(f'监视循环异常: {e}')
            
            time.sleep(self.check_interval)
