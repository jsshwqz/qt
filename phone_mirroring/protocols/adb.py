"""
ADB协议实现
实现完整的 Android 屏幕捕获和 H.264 视频流解析
"""

import asyncio
import logging
import socket
import subprocess
import time
import struct
import threading
import numpy as np
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from .base import BaseProtocol

logger = logging.getLogger(__name__)

class ADBConnectionState(Enum):
    """ADB连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    STREAMING = "streaming"
    ERROR = "error"

@dataclass
class VideoFrameInfo:
    """视频帧信息"""
    width: int = 0
    height: int = 0
    orientation: int = 0
    format: str = "H264"
    timestamp: float = 0.0

class H264Parser:
    """H.264视频流解析器"""
    
    # NAL单元起始码
    START_CODE_3 = b'\x00\x00\x01'
    START_CODE_4 = b'\x00\x00\x00\x01'
    
    # NAL单元类型
    NAL_TYPE_SLICE = 1
    NAL_TYPE_DPA = 2
    NAL_TYPE_DPB = 3
    NAL_TYPE_DPC = 4
    NAL_TYPE_IDR = 5
    NAL_TYPE_SEI = 6
    NAL_TYPE_SPS = 7
    NAL_TYPE_PPS = 8
    NAL_TYPE_AUD = 9
    NAL_TYPE_END_SEQUENCE = 10
    NAL_TYPE_END_STREAM = 11
    NAL_TYPE_FILLER = 12
    
    def __init__(self):
        self.buffer = b''
        self.frame_buffer = []
        self.sps_data: Optional[bytes] = None
        self.pps_data: Optional[bytes] = None
        self.frame_callback: Optional[Callable[[bytes, VideoFrameInfo], None]] = None
    
    def feed_data(self, data: bytes):
        """喂入原始数据"""
        self.buffer += data
        
        # 解析NAL单元
        while True:
            nal_unit = self._extract_nal_unit()
            if nal_unit is None:
                break
            self._process_nal_unit(nal_unit)
    
    def _extract_nal_unit(self) -> Optional[bytes]:
        """从缓冲区提取一个NAL单元"""
        if len(self.buffer) < 4:
            return None
        
        # 查找起始码
        start_4 = self.buffer.find(self.START_CODE_4)
        start_3 = self.buffer.find(self.START_CODE_3)
        
        if start_4 != -1 and (start_3 == -1 or start_4 <= start_3):
            start = start_4
            start_len = 4
        elif start_3 != -1:
            start = start_3
            start_len = 3
        else:
            return None
        
        # 查找下一个起始码
        next_start_4 = self.buffer.find(self.START_CODE_4, start + start_len)
        next_start_3 = self.buffer.find(self.START_CODE_3, start + start_len)
        
        if next_start_4 != -1 and (next_start_3 == -1 or next_start_4 <= next_start_3):
            end = next_start_4
        elif next_start_3 != -1:
            end = next_start_3
        else:
            # 没有更多数据，等待
            if len(self.buffer) > 1024 * 1024:  # 防止缓冲区无限增长
                end = len(self.buffer)
            else:
                return None
        
        # 提取NAL单元
        nal_unit = self.buffer[start:end]
        self.buffer = self.buffer[end:]
        
        return nal_unit
    
    def _process_nal_unit(self, nal_unit: bytes):
        """处理NAL单元"""
        if len(nal_unit) < 5:
            return
        
        # 获取NAL类型
        nal_type = nal_unit[4] & 0x1F if nal_unit.startswith(self.START_CODE_4) else nal_unit[3] & 0x1F
        
        # 保存SPS和PPS
        if nal_type == self.NAL_TYPE_SPS:
            self.sps_data = nal_unit
            logger.debug(f"SPS received, size: {len(nal_unit)}")
        elif nal_type == self.NAL_TYPE_PPS:
            self.pps_data = nal_unit
            logger.debug(f"PPS received, size: {len(nal_unit)}")
        
        # 如果是关键帧或普通帧，添加到帧缓冲区
        if nal_type in [self.NAL_TYPE_IDR, self.NAL_TYPE_SLICE]:
            self.frame_buffer.append(nal_unit)
            
            # 如果是IDR帧，发送完整的帧
            if nal_type == self.NAL_TYPE_IDR:
                self._emit_frame()
        elif nal_type == self.NAL_TYPE_AUD:
            # 访问单元分隔符，表示帧结束
            if self.frame_buffer:
                self._emit_frame()
    
    def _emit_frame(self):
        """发送完整帧"""
        if not self.frame_buffer:
            return
        
        # 组合帧数据（包含SPS/PPS）
        frame_data = b''
        if self.sps_data:
            frame_data += self.sps_data
        if self.pps_data:
            frame_data += self.pps_data
        
        for nal in self.frame_buffer:
            frame_data += nal
        
        # 创建帧信息
        info = VideoFrameInfo(
            timestamp=time.time(),
            format="H264"
        )
        
        # 触发回调
        if self.frame_callback:
            self.frame_callback(frame_data, info)
        
        # 清空帧缓冲区（保留SPS/PPS）
        self.frame_buffer = []
    
    def reset(self):
        """重置解析器状态"""
        self.buffer = b''
        self.frame_buffer = []
        self.sps_data = None
        self.pps_data = None

class ADBProtocol(BaseProtocol):
    """ADB协议实现，用于Android设备投屏"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.adb_port = config.get("adb_port", 5555)
        self.scrcpy_port = config.get("scrcpy_port", 27183)
        self.device_id = config.get("device_id", "")
        self.max_width = config.get("max_width", 1920)
        self.max_height = config.get("max_height", 1080)
        self.bitrate = config.get("bitrate", 2000000)
        self.max_fps = config.get("max_fps", 60)
        
        # 状态
        self.connection_state = ADBConnectionState.DISCONNECTED
        
        # 进程和连接
        self.scrcpy_process: Optional[asyncio.subprocess.Process] = None
        self.screenrecord_process: Optional[asyncio.subprocess.Process] = None
        self.video_socket: Optional[socket.socket] = None
        self.control_socket: Optional[socket.socket] = None
        
        # 设备管理
        self.devices_connected: Dict[str, Dict] = {}
        self.active_device: Optional[str] = None
        
        # 视频处理
        self.h264_parser = H264Parser()
        self.h264_parser.frame_callback = self._on_video_frame
        
        # 任务
        self.video_task: Optional[asyncio.Task] = None
        self.control_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        # 帧回调
        self.on_video_frame_callback: Optional[Callable[[bytes, Dict], None]] = None
        
        logger.info(f"ADB Protocol initialized for device: {self.device_id or 'auto-detect'}")
    
    async def start(self) -> bool:
        """启动ADB服务"""
        try:
            # 检查ADB是否可用
            if not await self._check_adb():
                logger.error("ADB not found. Please install Android SDK platform-tools")
                return False
            
            # 启动ADB服务器
            if not await self._start_adb_server():
                logger.error("Failed to start ADB server")
                return False
            
            # 连接设备
            if not await self._connect_devices():
                logger.error("Failed to connect to devices")
                return False
            
            # 启动屏幕捕获
            if not await self._start_screen_capture():
                logger.error("Failed to start screen capture")
                return False
            
            self.is_running = True
            self.connection_state = ADBConnectionState.STREAMING
            self.stats["start_time"] = time.time()
            
            # 启动心跳检测
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            logger.info("ADB screen mirroring started successfully")
            self.emit("started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start ADB protocol: {e}")
            self.connection_state = ADBConnectionState.ERROR
            self.stats["errors"] += 1
            return False
    
    async def stop(self) -> bool:
        """停止ADB服务"""
        try:
            self.is_running = False
            self.connection_state = ADBConnectionState.DISCONNECTED
            
            # 停止任务
            for task in [self.video_task, self.control_task, self.heartbeat_task]:
                if task:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # 停止scrcpy进程
            if self.scrcpy_process:
                try:
                    self.scrcpy_process.terminate()
                    await asyncio.wait_for(self.scrcpy_process.wait(), timeout=5.0)
                except:
                    self.scrcpy_process.kill()
                finally:
                    self.scrcpy_process = None
            
            # 停止screenrecord进程
            if self.screenrecord_process:
                try:
                    self.screenrecord_process.terminate()
                    await asyncio.wait_for(self.screenrecord_process.wait(), timeout=5.0)
                except:
                    self.screenrecord_process.kill()
                finally:
                    self.screenrecord_process = None
            
            # 关闭socket
            for sock in [self.video_socket, self.control_socket]:
                if sock:
                    try:
                        sock.close()
                    except:
                        pass
            self.video_socket = None
            self.control_socket = None
            
            logger.info("ADB screen mirroring stopped")
            self.emit("stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping ADB protocol: {e}")
            return False
    
    async def _check_adb(self) -> bool:
        """检查ADB是否可用"""
        try:
            result = await asyncio.create_subprocess_exec(
                'adb', 'version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                version = stdout.decode('utf-8', errors='ignore').strip()
                logger.info(f"ADB version: {version}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"ADB check failed: {e}")
            return False
    
    async def _start_adb_server(self) -> bool:
        """启动ADB服务器"""
        try:
            result = await asyncio.create_subprocess_exec(
                'adb', 'start-server',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            
            if result.returncode == 0:
                logger.info("ADB server started")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to start ADB server: {e}")
            return False
    
    async def _connect_devices(self) -> bool:
        """连接Android设备"""
        try:
            # 获取设备列表
            result = await asyncio.create_subprocess_exec(
                'adb', 'devices', '-l',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Failed to list devices: {stderr.decode()}")
                return False
            
            # 解析设备列表
            lines = stdout.decode('utf-8').strip().split('\n')[1:]
            self.devices_connected = {}
            
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 2:
                    device_id = parts[0]
                    state = parts[1]
                    
                    if state == 'device':
                        # 提取设备信息
                        info = {'id': device_id, 'state': state, 'connected_time': time.time()}
                        
                        # 解析额外信息
                        for i, part in enumerate(parts[2:], 2):
                            if ':' in part:
                                key, value = part.split(':', 1)
                                info[key] = value
                        
                        self.devices_connected[device_id] = info
                        self.stats["connected_clients"] += 1
            
            if not self.devices_connected:
                logger.warning("No USB devices found, trying TCP connection...")
                return await self._connect_tcp_device()
            
            # 选择设备
            if self.device_id and self.device_id in self.devices_connected:
                self.active_device = self.device_id
            else:
                # 使用第一个可用设备
                self.active_device = list(self.devices_connected.keys())[0]
                self.device_id = self.active_device
            
            logger.info(f"Connected to device: {self.active_device}")
            self.connection_state = ADBConnectionState.CONNECTED
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect devices: {e}")
            return False
    
    async def _connect_tcp_device(self) -> bool:
        """通过TCP连接设备"""
        try:
            # 启用TCP调试模式
            result = await asyncio.create_subprocess_exec(
                'adb', 'tcpip', str(self.adb_port),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            
            # 尝试连接本地设备
            result = await asyncio.create_subprocess_exec(
                'adb', 'connect', f'127.0.0.1:{self.adb_port}',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            output = stdout.decode('utf-8', errors='ignore')
            
            if "connected" in output.lower() or "already connected" in output.lower():
                self.active_device = f"127.0.0.1:{self.adb_port}"
                self.devices_connected[self.active_device] = {
                    'id': self.active_device,
                    'state': 'device',
                    'connected_time': time.time(),
                    'type': 'tcp'
                }
                self.stats["connected_clients"] += 1
                logger.info(f"Connected to TCP device: {self.active_device}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to connect TCP device: {e}")
            return False
    
    async def _start_screen_capture(self) -> bool:
        """启动屏幕捕获"""
        # 优先尝试scrcpy
        if await self._check_scrcpy():
            return await self._start_scrcpy_capture()
        else:
            logger.warning("Scrcpy not available, falling back to screenrecord")
            return await self._start_screenrecord_capture()
    
    async def _check_scrcpy(self) -> bool:
        """检查scrcpy是否可用"""
        try:
            result = await asyncio.create_subprocess_exec(
                'scrcpy', '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            return result.returncode == 0
            
        except:
            return False
    
    async def _start_scrcpy_capture(self) -> bool:
        """使用scrcpy启动屏幕捕获"""
        try:
            cmd = [
                'scrcpy',
                '--serial', self.active_device,
                '--max-size', str(self.max_width),
                '--max-fps', str(self.max_fps),
                '--video-bit-rate', str(self.bitrate),
                '--no-display',
                '--no-control',
                '--record-format', 'mkv',
                '--record', '-'  # 输出到stdout
            ]
            
            self.scrcpy_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 启动视频读取任务
            self.video_task = asyncio.create_task(self._read_scrcpy_stream())
            
            logger.info(f"Scrcpy capture started: {self.max_width}x{self.max_height} @ {self.max_fps}fps")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start scrcpy: {e}")
            return False
    
    async def _start_screenrecord_capture(self) -> bool:
        """使用ADB screenrecord启动屏幕捕获"""
        try:
            cmd = [
                'adb', '-s', self.active_device,
                'shell', 'screenrecord',
                '--output-format=h264',
                '--size', f'{self.max_width}x{self.max_height}',
                '--bit-rate', str(self.bitrate),
                '--time-limit', '3600',  # 1小时
                '-'
            ]
            
            self.screenrecord_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 启动视频读取任务
            self.video_task = asyncio.create_task(self._read_screenrecord_stream())
            
            logger.info(f"Screenrecord capture started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start screenrecord: {e}")
            return False
    
    async def _read_scrcpy_stream(self):
        """读取scrcpy视频流"""
        try:
            while self.is_running and self.scrcpy_process:
                # 读取数据块
                data = await self.scrcpy_process.stdout.read(4096)
                if not data:
                    break
                
                # 解析H.264数据
                self.h264_parser.feed_data(data)
                
                self.stats["bytes_received"] += len(data)
                
        except asyncio.CancelledError:
            logger.info("Scrcpy stream reading cancelled")
        except Exception as e:
            logger.error(f"Error reading scrcpy stream: {e}")
            self.stats["errors"] += 1
    
    async def _read_screenrecord_stream(self):
        """读取screenrecord视频流"""
        try:
            while self.is_running and self.screenrecord_process:
                # 读取数据块
                data = await self.screenrecord_process.stdout.read(4096)
                if not data:
                    break
                
                # 解析H.264数据
                self.h264_parser.feed_data(data)
                
                self.stats["bytes_received"] += len(data)
                
        except asyncio.CancelledError:
            logger.info("Screenrecord stream reading cancelled")
        except Exception as e:
            logger.error(f"Error reading screenrecord stream: {e}")
            self.stats["errors"] += 1
    
    def _on_video_frame(self, frame_data: bytes, info: VideoFrameInfo):
        """视频帧回调"""
        metadata = {
            'timestamp': info.timestamp,
            'size': len(frame_data),
            'device_id': self.active_device,
            'format': info.format
        }
        
        # 触发帧接收事件
        self.emit("frame_received", frame_data, metadata)
        
        # 如果有外部回调，也调用它
        if self.on_video_frame_callback:
            self.on_video_frame_callback(frame_data, metadata)
    
    async def _heartbeat_loop(self):
        """心跳检测循环"""
        while self.is_running:
            try:
                # 检查设备连接状态
                if self.active_device:
                    result = await asyncio.create_subprocess_exec(
                        'adb', '-s', self.active_device, 'shell', 'echo', 'ping',
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await asyncio.wait_for(result.communicate(), timeout=5.0)
                    
                    if result.returncode != 0:
                        logger.warning(f"Device {self.active_device} connection lost")
                        # 尝试重新连接
                        await self._connect_devices()
                
                await asyncio.sleep(10)  # 每10秒检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)
    
    async def send_frame(self, frame_data: bytes, metadata: Dict[str, Any]) -> bool:
        """发送视频帧（ADB通常是接收方）"""
        # ADB协议主要用于接收，此方法用于反向投屏场景
        return True
    
    async def send_audio(self, audio_data: bytes, metadata: Dict[str, Any]) -> bool:
        """发送音频数据"""
        # 暂不支持
        return True
    
    async def handle_control(self, control_data: Dict[str, Any]) -> bool:
        """处理控制指令"""
        try:
            if not self.active_device:
                return False
            
            action = control_data.get("action")
            x = control_data.get("x", 0)
            y = control_data.get("y", 0)
            
            if action == "click":
                await self._execute_shell_command(f'input tap {x} {y}')
                
            elif action == "swipe":
                x2 = control_data.get("x2", x)
                y2 = control_data.get("y2", y)
                duration = control_data.get("duration", 300)
                await self._execute_shell_command(
                    f'input swipe {x} {y} {x2} {y2} {duration}'
                )
                
            elif action == "key":
                key = control_data.get("key", "KEYCODE_ENTER")
                await self._execute_shell_command(f'input keyevent {key}')
                
            elif action == "text":
                text = control_data.get("text", "")
                # 转义特殊字符
                text = text.replace(' ', '%s').replace("'", "\\'").replace('"', '\\"')
                await self._execute_shell_command(f'input text "{text}"')
                
            elif action == "home":
                await self._execute_shell_command('input keyevent KEYCODE_HOME')
                
            elif action == "back":
                await self._execute_shell_command('input keyevent KEYCODE_BACK')
                
            elif action == "recent":
                await self._execute_shell_command('input keyevent KEYCODE_APP_SWITCH')
                
            return True
            
        except Exception as e:
            logger.error(f"Error handling control: {e}")
            self.stats["errors"] += 1
            return False
    
    async def _execute_shell_command(self, command: str) -> bool:
        """执行ADB shell命令"""
        try:
            result = await asyncio.create_subprocess_exec(
                'adb', '-s', self.active_device,
                'shell', command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore').strip()
                logger.error(f"Shell command failed: {command}, error: {error_msg}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing shell command '{command}': {e}")
            return False
    
    def get_device_info(self) -> Dict[str, Any]:
        """获取设备信息"""
        return {
            'active_device': self.active_device,
            'connection_state': self.connection_state.value,
            'devices': self.devices_connected,
            'capture_config': {
                'width': self.max_width,
                'height': self.max_height,
                'fps': self.max_fps,
                'bitrate': self.bitrate
            }
        }
    
    def set_video_frame_callback(self, callback: Callable[[bytes, Dict], None]):
        """设置视频帧回调"""
        self.on_video_frame_callback = callback
