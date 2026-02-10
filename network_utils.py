#!/usr/bin/env python3
"""
网络工具模块 - 改进连接稳定性
支持自动重连、状态监控、网络诊断
"""
import socket
import threading
import logging
import time
from typing import Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """连接状态"""
    IDLE = "idle"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class RobustSocketConnection:
    """健壮的 Socket 连接管理器"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 27183, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket: Optional[socket.socket] = None
        self.state = ConnectionState.IDLE
        self.connected = False
        
        # 回调函数
        self.on_state_changed: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_data: Optional[Callable] = None
        
        logger.info(f'RobustSocketConnection 初始化: {host}:{port}')
    
    def connect(self) -> bool:
        """连接到服务器"""
        try:
            self._set_state(ConnectionState.CONNECTING)
            
            logger.info(f'正在连接到 {self.host}:{self.port}...')
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            
            # 设置套接字选项
            self._configure_socket()
            
            self.connected = True
            self._set_state(ConnectionState.CONNECTED)
            logger.info(f'已连接到 {self.host}:{self.port}')
            return True
            
        except socket.timeout:
            msg = f'连接超时 ({self.timeout}s)'
            logger.error(msg)
            self._handle_error(msg)
            return False
        except ConnectionRefusedError:
            msg = f'连接被拒绝'
            logger.error(msg)
            self._handle_error(msg)
            return False
        except Exception as e:
            msg = f'连接失败: {e}'
            logger.error(msg, exc_info=True)
            self._handle_error(msg)
            return False
    
    def disconnect(self):
        """断开连接"""
        try:
            self._set_state(ConnectionState.DISCONNECTING)
            
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
            
            self.socket = None
            self.connected = False
            self._set_state(ConnectionState.DISCONNECTED)
            logger.info('已断开连接')
            
        except Exception as e:
            logger.error(f'断开连接失败: {e}')
    
    def send(self, data: bytes) -> bool:
        """发送数据"""
        if not self.connected or not self.socket:
            logger.warning('未连接，无法发送数据')
            return False
        
        try:
            self.socket.sendall(data)
            return True
        except Exception as e:
            msg = f'发送数据失败: {e}'
            logger.error(msg)
            self._handle_error(msg)
            return False
    
    def recv(self, buffer_size: int = 65536) -> Optional[bytes]:
        """接收数据"""
        if not self.connected or not self.socket:
            return None
        
        try:
            data = self.socket.recv(buffer_size)
            if not data:
                logger.warning('对端已关闭连接')
                self._handle_error('对端已关闭连接')
                return None
            return data
        except socket.timeout:
            logger.debug('接收超时')
            return None
        except Exception as e:
            msg = f'接收数据失败: {e}'
            logger.error(msg)
            self._handle_error(msg)
            return None
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.connected and self.socket is not None
    
    def _configure_socket(self):
        """配置套接字参数"""
        try:
            # TCP_NODELAY：禁用 Nagle 算法，降低延迟
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            # SO_KEEPALIVE：启用 TCP keepalive
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            
            logger.debug('Socket 参数配置完成')
        except Exception as e:
            logger.warning(f'配置 Socket 参数失败: {e}')
    
    def _set_state(self, new_state: ConnectionState):
        """设置连接状态"""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            logger.debug(f'状态变化: {old_state.value} -> {new_state.value}')
            
            if self.on_state_changed:
                try:
                    self.on_state_changed(new_state)
                except Exception as e:
                    logger.error(f'状态变化回调失败: {e}')
    
    def _handle_error(self, error_msg: str):
        """处理错误"""
        self._set_state(ConnectionState.ERROR)
        self.connected = False
        
        if self.on_error:
            try:
                self.on_error(error_msg)
            except Exception as e:
                logger.error(f'错误回调失败: {e}')


class AutoReconnectSocket:
    """自动重连的 Socket 连接"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 27183, 
                 max_retries: int = 3, retry_delay: float = 2.0):
        self.host = host
        self.port = port
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.connection = RobustSocketConnection(host, port)
        self.retry_count = 0
        self.receive_thread: Optional[threading.Thread] = None
        self.running = False
        
        # 回调
        self.on_data: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        self.on_connected: Optional[Callable] = None
        
        logger.info(f'AutoReconnectSocket 初始化: {host}:{port}')
    
    def connect(self) -> bool:
        """连接（带自动重连）"""
        logger.info(f'开始连接，最多重试 {self.max_retries} 次...')
        
        for attempt in range(self.max_retries):
            logger.info(f'连接尝试 {attempt + 1}/{self.max_retries}...')
            
            if self.connection.connect():
                self.retry_count = 0
                self.running = True
                
                # 启动接收线程
                self.receive_thread = threading.Thread(
                    target=self._receive_loop,
                    daemon=True
                )
                self.receive_thread.start()
                
                if self.on_connected:
                    try:
                        self.on_connected()
                    except Exception as e:
                        logger.error(f'连接回调失败: {e}')
                
                return True
            
            if attempt < self.max_retries - 1:
                logger.info(f'等待 {self.retry_delay}s 后重试...')
                time.sleep(self.retry_delay)
        
        msg = f'连接失败，已重试 {self.max_retries} 次'
        logger.error(msg)
        
        if self.on_error:
            try:
                self.on_error(msg)
            except Exception as e:
                logger.error(f'错误回调失败: {e}')
        
        return False
    
    def disconnect(self):
        """断开连接"""
        logger.info('断开连接中...')
        self.running = False
        
        if self.receive_thread:
            self.receive_thread.join(timeout=2)
        
        self.connection.disconnect()
        logger.info('已断开连接')
    
    def send(self, data: bytes) -> bool:
        """发送数据"""
        return self.connection.send(data)
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.connection.is_connected()
    
    def _receive_loop(self):
        """接收数据循环"""
        logger.info('接收线程启动')
        
        while self.running:
            try:
                data = self.connection.recv()
                
                if data:
                    if self.on_data:
                        try:
                            self.on_data(data)
                        except Exception as e:
                            logger.error(f'数据回调失败: {e}')
                else:
                    logger.warning('未接收到数据，连接可能已断开')
                    break
                    
            except Exception as e:
                logger.error(f'接收循环异常: {e}')
                break
        
        self.running = False
        logger.info('接收线程退出')


# 网络诊断工具
def diagnose_connection(host: str, port: int, timeout: float = 5.0) -> dict:
    """诊断网络连接"""
    result = {
        'host': host,
        'port': port,
        'reachable': False,
        'latency': None,
        'error': None
    }
    
    try:
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        
        result['reachable'] = True
        result['latency'] = (time.time() - start) * 1000  # 毫秒
        
    except socket.timeout:
        result['error'] = '连接超时'
    except ConnectionRefusedError:
        result['error'] = '连接被拒绝'
    except Exception as e:
        result['error'] = str(e)
    
    return result
