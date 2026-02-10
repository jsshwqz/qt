"""
RTSP协议实现
实现完整的RTP数据包封装和视频流发送功能
"""

import asyncio
import logging
import socket
import struct
import time
import random
import threading
from typing import Dict, Any, Optional, List, Callable, Tuple
from enum import Enum
from .base import BaseProtocol

logger = logging.getLogger(__name__)

class RTSPState(Enum):
    """RTSP会话状态"""
    INIT = "INIT"
    READY = "READY"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    RECORDING = "RECORDING"

class RTPPacket:
    """RTP数据包"""
    
    # RTP头部常量
    RTP_VERSION = 2
    RTP_HEADER_SIZE = 12
    
    # NAL单元类型
    NAL_TYPE_SINGLE = 1      # 单一NAL单元
    NAL_TYPE_FU_A = 28       # FU-A分片
    NAL_TYPE_FU_B = 29       # FU-B分片
    
    def __init__(self):
        self.version = self.RTP_VERSION
        self.padding = 0
        self.extension = 0
        self.csrc_count = 0
        self.marker = 0
        self.payload_type = 96  # H.264动态payload类型
        self.sequence_number = 0
        self.timestamp = 0
        self.ssrc = 0
        self.payload = b''
        self.csrc_list = []
    
    def pack(self) -> bytes:
        """打包RTP头部"""
        # 第一个字节: V(2) P(1) X(1) CC(4)
        byte1 = (self.version << 6) | (self.padding << 5) | (self.extension << 4) | self.csrc_count
        
        # 第二个字节: M(1) PT(7)
        byte2 = (self.marker << 7) | self.payload_type
        
        header = struct.pack('!BBHII',
            byte1,
            byte2,
            self.sequence_number & 0xFFFF,
            self.timestamp & 0xFFFFFFFF,
            self.ssrc & 0xFFFFFFFF
        )
        
        # 添加CSRC列表
        for csrc in self.csrc_list:
            header += struct.pack('!I', csrc & 0xFFFFFFFF)
        
        return header + self.payload
    
    @classmethod
    def unpack(cls, data: bytes) -> 'RTPPacket':
        """解包RTP数据"""
        if len(data) < cls.RTP_HEADER_SIZE:
            raise ValueError("RTP packet too short")
        
        packet = cls()
        
        byte1, byte2, seq, ts, ssrc = struct.unpack('!BBHII', data[:12])
        
        packet.version = (byte1 >> 6) & 0x03
        packet.padding = (byte1 >> 5) & 0x01
        packet.extension = (byte1 >> 4) & 0x01
        packet.csrc_count = byte1 & 0x0F
        packet.marker = (byte2 >> 7) & 0x01
        packet.payload_type = byte2 & 0x7F
        packet.sequence_number = seq
        packet.timestamp = ts
        packet.ssrc = ssrc
        
        # 解析CSRC列表
        header_size = 12 + packet.csrc_count * 4
        for i in range(packet.csrc_count):
            csrc = struct.unpack('!I', data[12 + i * 4:16 + i * 4])[0]
            packet.csrc_list.append(csrc)
        
        packet.payload = data[header_size:]
        
        return packet

class H264Packetizer:
    """H.264视频数据分包器"""
    
    def __init__(self, mtu: int = 1400):
        self.mtu = mtu
        self.sequence_number = random.randint(0, 65535)
        self.timestamp_increment = 3600  # 90kHz时钟频率下的40ms增量
        self.ssrc = random.randint(0, 0xFFFFFFFF)
        self.last_timestamp = 0
    
    def packetize(self, frame_data: bytes, timestamp: int = None) -> List[RTPPacket]:
        """将H.264帧分包为RTP包
        
        Args:
            frame_data: H.264编码的帧数据（包含起始码）
            timestamp: RTP时间戳，如果为None则自动生成
            
        Returns:
            RTP数据包列表
        """
        packets = []
        
        if timestamp is None:
            timestamp = self.last_timestamp + self.timestamp_increment
        self.last_timestamp = timestamp
        
        # 移除H.264起始码 (0x00 0x00 0x00 0x01 或 0x00 0x00 0x01)
        frame_data = self._remove_start_code(frame_data)
        
        if len(frame_data) <= self.mtu:
            # 小包：单一NAL单元模式
            packet = self._create_single_nal_packet(frame_data, timestamp)
            packets.append(packet)
        else:
            # 大包：FU-A分片模式
            packets = self._create_fragmented_packets(frame_data, timestamp)
        
        return packets
    
    def _remove_start_code(self, data: bytes) -> bytes:
        """移除H.264起始码"""
        # 检查4字节起始码
        if data.startswith(b'\x00\x00\x00\x01'):
            return data[4:]
        # 检查3字节起始码
        elif data.startswith(b'\x00\x00\x01'):
            return data[3:]
        return data
    
    def _create_single_nal_packet(self, nal_data: bytes, timestamp: int) -> RTPPacket:
        """创建单一NAL单元RTP包"""
        packet = RTPPacket()
        packet.version = 2
        packet.padding = 0
        packet.extension = 0
        packet.csrc_count = 0
        packet.marker = 1  # 帧结束标记
        packet.payload_type = 96  # H.264
        packet.sequence_number = self._get_next_sequence()
        packet.timestamp = timestamp
        packet.ssrc = self.ssrc
        packet.payload = nal_data
        
        return packet
    
    def _create_fragmented_packets(self, nal_data: bytes, timestamp: int) -> List[RTPPacket]:
        """创建FU-A分片RTP包"""
        packets = []
        
        # 获取NAL单元头部
        nal_header = nal_data[0]
        nal_type = nal_header & 0x1F
        nal_ref_idc = (nal_header >> 5) & 0x03
        
        # FU指示器
        fu_indicator = (nal_ref_idc << 5) | 28  # 28 = FU-A
        
        # 分片数据（跳过原始NAL头部）
        data_to_fragment = nal_data[1:]
        
        # 计算分片数量
        max_fragment_size = self.mtu - 2  # 减去FU指示器和FU头部
        num_fragments = (len(data_to_fragment) + max_fragment_size - 1) // max_fragment_size
        
        offset = 0
        for i in range(num_fragments):
            is_first = (i == 0)
            is_last = (i == num_fragments - 1)
            
            # FU头部
            fu_header = 0
            if is_first:
                fu_header |= 0x80  # S位
            if is_last:
                fu_header |= 0x40  # E位
            fu_header |= nal_type
            
            # 计算当前分片大小
            fragment_size = min(max_fragment_size, len(data_to_fragment) - offset)
            fragment_data = data_to_fragment[offset:offset + fragment_size]
            
            # 创建RTP包
            packet = RTPPacket()
            packet.version = 2
            packet.marker = 1 if is_last else 0
            packet.payload_type = 96
            packet.sequence_number = self._get_next_sequence()
            packet.timestamp = timestamp
            packet.ssrc = self.ssrc
            packet.payload = bytes([fu_indicator, fu_header]) + fragment_data
            
            packets.append(packet)
            offset += fragment_size
        
        return packets
    
    def _get_next_sequence(self) -> int:
        """获取下一个序列号"""
        self.sequence_number = (self.sequence_number + 1) & 0xFFFF
        return self.sequence_number

class RTSPClientSession:
    """RTSP客户端会话"""
    
    def __init__(self, client_id: str, client_socket: socket.socket, 
                 client_address: Tuple[str, int]):
        self.client_id = client_id
        self.socket = client_socket
        self.address = client_address
        self.state = RTSPState.INIT
        self.session_id = str(random.randint(1000000000, 9999999999))
        
        # RTP传输信息
        self.rtp_port = 0
        self.rtcp_port = 0
        self.transport = "RTP/AVP"
        
        # 视频流信息
        self.video_ssrc = random.randint(0, 0xFFFFFFFF)
        self.audio_ssrc = random.randint(0, 0xFFFFFFFF)
        
        # RTP socket
        self.rtp_socket: Optional[socket.socket] = None
        
        # 统计信息
        self.frames_sent = 0
        self.bytes_sent = 0
        self.start_time = 0
    
    def setup_transport(self, rtp_port: int, rtcp_port: int):
        """设置RTP传输端口"""
        self.rtp_port = rtp_port
        self.rtcp_port = rtcp_port
        
        # 创建RTP socket
        try:
            self.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.rtp_socket.setblocking(False)
            logger.info(f"RTP socket created for client {self.client_id}")
        except Exception as e:
            logger.error(f"Failed to create RTP socket: {e}")
    
    def send_rtp_packet(self, packet: RTPPacket) -> bool:
        """发送RTP数据包"""
        if not self.rtp_socket or self.state != RTSPState.PLAYING:
            return False
        
        try:
            data = packet.pack()
            self.rtp_socket.sendto(data, (self.address[0], self.rtp_port))
            self.frames_sent += 1
            self.bytes_sent += len(data)
            return True
        except Exception as e:
            logger.error(f"Error sending RTP packet to {self.client_id}: {e}")
            return False
    
    def close(self):
        """关闭会话"""
        if self.rtp_socket:
            try:
                self.rtp_socket.close()
            except:
                pass
            self.rtp_socket = None
        
        try:
            self.socket.close()
        except:
            pass

class RTSPProtocol(BaseProtocol):
    """RTSP流媒体协议实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.server_socket: Optional[socket.socket] = None
        self.clients: Dict[str, RTSPClientSession] = {}
        self.client_tasks: Dict[str, asyncio.Task] = {}
        self.cseq = 0
        
        # RTSP配置
        self.rtsp_port = config.get("port", 8554)
        self.rtp_port_start = config.get("rtp_port_start", 5000)
        self.next_rtp_port = self.rtp_port_start
        
        # SDP信息
        self.sdp_info = self._generate_sdp()
        
        # H.264分包器
        self.packetizer = H264Packetizer(mtu=1400)
        
        # 视频流任务
        self.video_stream_task: Optional[asyncio.Task] = None
        self.is_streaming = False
        
        # 视频数据源回调
        self.video_source_callback: Optional[Callable[[], bytes]] = None
    
    def _generate_sdp(self) -> str:
        """生成SDP信息"""
        return f"""v=0
o=- {int(time.time())} {int(time.time())} IN IP4 0.0.0.0
s=Phone Mirroring Session
i=WiFi Phone Mirroring Stream
c=IN IP4 0.0.0.0
t=0 0
a=tool:PhoneMirroring/1.0
a=type:broadcast
m=video {self.rtp_port_start} RTP/AVP 96
a=rtpmap:96 H264/90000
a=fmtp:96 packetization-mode=1;profile-level-id=42001E;sprop-parameter-sets=Z0LAHtkAo8or0EQAAAADAEAAAAwgbgIAAV7AAH8eMGUA==,aM48gA==
a=control:trackID=1
a=framerate:30.0
m=audio {self.rtp_port_start + 2} RTP/AVP 97
a=rtpmap:97 MPEG4-GENERIC/44100/2
a=fmtp:97 profile-level-id=1;mode=AAC-hbr;sizelength=13;indexlength=3;indexdeltalength=3;config=1210
a=control:trackID=2"""
    
    async def start(self) -> bool:
        """启动RTSP服务器"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.rtsp_port))
            self.server_socket.listen(10)
            self.server_socket.setblocking(False)
            
            self.is_running = True
            self.stats["start_time"] = time.time()
            
            # 启动接受连接的任务
            loop = asyncio.get_event_loop()
            self.accept_task = loop.create_task(self._accept_connections())
            
            logger.info(f"RTSP Server started on port {self.rtsp_port}")
            self.emit("started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start RTSP server: {e}")
            self.stats["errors"] += 1
            return False
    
    async def stop(self) -> bool:
        """停止RTSP服务器"""
        try:
            self.is_running = False
            self.is_streaming = False
            
            # 停止视频流任务
            if self.video_stream_task:
                self.video_stream_task.cancel()
                try:
                    await self.video_stream_task
                except asyncio.CancelledError:
                    pass
            
            # 停止所有客户端任务
            for task in list(self.client_tasks.values()):
                task.cancel()
            
            # 关闭所有客户端连接
            for client in self.clients.values():
                client.close()
            
            # 关闭服务器socket
            if self.server_socket:
                self.server_socket.close()
            
            self.clients.clear()
            self.client_tasks.clear()
            
            logger.info("RTSP Server stopped")
            self.emit("stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping RTSP server: {e}")
            return False
    
    async def _accept_connections(self):
        """接受客户端连接"""
        loop = asyncio.get_event_loop()
        
        while self.is_running:
            try:
                client_socket, client_address = await loop.sock_accept(self.server_socket)
                client_id = f"{client_address[0]}:{client_address[1]}_{int(time.time() * 1000)}"
                
                # 创建客户端会话
                session = RTSPClientSession(client_id, client_socket, client_address)
                self.clients[client_id] = session
                
                # 创建处理任务
                self.client_tasks[client_id] = loop.create_task(
                    self._handle_client(session)
                )
                
                self.stats["connected_clients"] += 1
                logger.info(f"New RTSP client connected: {client_address}")
                self.emit("client_connected", client_id, client_address)
                
            except Exception as e:
                if self.is_running:
                    logger.error(f"Error accepting connection: {e}")
                    self.stats["errors"] += 1
                await asyncio.sleep(0.1)
    
    async def _handle_client(self, session: RTSPClientSession):
        """处理客户端RTSP请求"""
        loop = asyncio.get_event_loop()
        
        try:
            while self.is_running and session.state != RTSPState.INIT:
                try:
                    # 接收RTSP请求
                    data = await loop.sock_recv(session.socket, 4096)
                    if not data:
                        break
                    
                    # 解析RTSP请求
                    request = data.decode('utf-8', errors='ignore')
                    response = await self._handle_rtsp_request(request, session)
                    
                    if response:
                        await loop.sock_sendall(session.socket, response.encode('utf-8'))
                    
                    self.stats["bytes_received"] += len(data)
                    
                except Exception as e:
                    logger.error(f"Error handling client {session.client_id}: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Client handler error: {e}")
        finally:
            await self._remove_client(session.client_id)
    
    async def _handle_rtsp_request(self, request: str, session: RTSPClientSession) -> Optional[str]:
        """处理RTSP请求命令"""
        lines = request.split('\r\n')
        if not lines:
            return None
        
        # 解析请求行
        request_line = lines[0]
        parts = request_line.split(' ')
        if len(parts) < 3:
            return None
        
        method = parts[0]
        url = parts[1]
        version = parts[2]
        
        # 解析CSeq
        cseq = 0
        headers = {}
        for line in lines[1:]:
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()
                if key.strip() == 'CSeq':
                    cseq = int(value.strip())
        
        logger.debug(f"RTSP {method} from {session.client_id}")
        
        # 处理各命令
        if method == 'OPTIONS':
            return self._create_response(200, "OK", cseq, {
                'Public': 'DESCRIBE, SETUP, TEARDOWN, PLAY, PAUSE, GET_PARAMETER, SET_PARAMETER'
            })
        
        elif method == 'DESCRIBE':
            return self._create_response(200, "OK", cseq, {
                'Content-Type': 'application/sdp',
                'Content-Length': str(len(self.sdp_info)),
                'Content-Base': f'rtsp://{session.address[0]}:{self.rtsp_port}/'
            }, self.sdp_info)
        
        elif method == 'SETUP':
            return await self._handle_setup(session, headers, cseq)
        
        elif method == 'PLAY':
            return await self._handle_play(session, headers, cseq)
        
        elif method == 'PAUSE':
            return await self._handle_pause(session, headers, cseq)
        
        elif method == 'TEARDOWN':
            return await self._handle_teardown(session, headers, cseq)
        
        elif method == 'GET_PARAMETER':
            return self._create_response(200, "OK", cseq)
        
        elif method == 'SET_PARAMETER':
            return self._create_response(200, "OK", cseq)
        
        else:
            return self._create_response(405, "Method Not Allowed", cseq, {
                'Allow': 'DESCRIBE, SETUP, TEARDOWN, PLAY, PAUSE, GET_PARAMETER, SET_PARAMETER'
            })
    
    async def _handle_setup(self, session: RTSPClientSession, headers: Dict, cseq: int) -> str:
        """处理SETUP命令"""
        transport_header = headers.get('Transport', '')
        
        # 解析传输参数
        client_ports = self._parse_client_ports(transport_header)
        if client_ports:
            rtp_port, rtcp_port = client_ports
            session.setup_transport(rtp_port, rtcp_port)
        else:
            # 分配默认端口
            session.setup_transport(self.next_rtp_port, self.next_rtp_port + 1)
            self.next_rtp_port += 2
        
        session.state = RTSPState.READY
        
        transport_response = f"RTP/AVP;unicast;client_port={session.rtp_port}-{session.rtcp_port};server_port={self.rtp_port_start}-{self.rtp_port_start + 1}"
        
        return self._create_response(200, "OK", cseq, {
            'Transport': transport_response,
            'Session': session.session_id,
            'Expires': '300'
        })
    
    async def _handle_play(self, session: RTSPClientSession, headers: Dict, cseq: int) -> str:
        """处理PLAY命令"""
        if session.state not in [RTSPState.READY, RTSPState.PAUSED]:
            return self._create_response(455, "Method Not Valid in This State", cseq)
        
        session.state = RTSPState.PLAYING
        session.start_time = time.time()
        
        # 启动视频流传输
        if not self.is_streaming:
            self.is_streaming = True
            self.video_stream_task = asyncio.create_task(self._video_stream_loop())
        
        logger.info(f"Client {session.client_id} started playing")
        
        return self._create_response(200, "OK", cseq, {
            'Session': session.session_id,
            'RTP-Info': f'url=rtsp://{session.address[0]}:{self.rtsp_port}/trackID=1;seq={self.packetizer.sequence_number}'
        })
    
    async def _handle_pause(self, session: RTSPClientSession, headers: Dict, cseq: int) -> str:
        """处理PAUSE命令"""
        if session.state != RTSPState.PLAYING:
            return self._create_response(455, "Method Not Valid in This State", cseq)
        
        session.state = RTSPState.PAUSED
        
        logger.info(f"Client {session.client_id} paused")
        
        return self._create_response(200, "OK", cseq, {
            'Session': session.session_id
        })
    
    async def _handle_teardown(self, session: RTSPClientSession, headers: Dict, cseq: int) -> str:
        """处理TEARDOWN命令"""
        session.state = RTSPState.INIT
        
        logger.info(f"Client {session.client_id} tearing down")
        
        return self._create_response(200, "OK", cseq, {
            'Session': session.session_id
        })
    
    def _parse_client_ports(self, transport: str) -> Optional[Tuple[int, int]]:
        """解析客户端端口"""
        try:
            if 'client_port=' in transport:
                port_part = transport.split('client_port=')[1].split(';')[0]
                ports = port_part.split('-')
                return (int(ports[0]), int(ports[1]) if len(ports) > 1 else int(ports[0]) + 1)
        except:
            pass
        return None
    
    def _create_response(self, code: int, message: str, cseq: int,
                        headers: Dict[str, str] = None, body: str = "") -> str:
        """生成RTSP响应"""
        response = f"RTSP/1.0 {code} {message}\r\n"
        response += f"CSeq: {cseq}\r\n"
        response += f"Server: PhoneMirroring/1.0\r\n"
        response += f"Date: {self._get_http_date()}\r\n"
        
        if headers:
            for key, value in headers.items():
                response += f"{key}: {value}\r\n"
        
        response += "\r\n"
        
        if body:
            response += body
        
        return response
    
    def _get_http_date(self) -> str:
        """获取HTTP日期格式"""
        from datetime import datetime
        return datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    async def _remove_client(self, client_id: str):
        """移除客户端"""
        if client_id in self.clients:
            session = self.clients[client_id]
            session.close()
            del self.clients[client_id]
        
        if client_id in self.client_tasks:
            del self.client_tasks[client_id]
        
        self.stats["connected_clients"] -= 1
        logger.info(f"RTSP client disconnected: {client_id}")
        self.emit("client_disconnected", client_id)
    
    async def _video_stream_loop(self):
        """视频流发送循环"""
        while self.is_running and self.is_streaming:
            try:
                # 获取视频数据
                frame_data = None
                if self.video_source_callback:
                    frame_data = self.video_source_callback()
                
                if frame_data:
                    await self._send_video_frame(frame_data)
                
                # 控制帧率 (30fps = 33ms)
                await asyncio.sleep(1/30)
                
            except Exception as e:
                logger.error(f"Error in video stream loop: {e}")
                await asyncio.sleep(0.1)
    
    async def _send_video_frame(self, frame_data: bytes):
        """发送视频帧到所有播放中的客户端"""
        # 分包
        timestamp = int(time.time() * 90000)  # 90kHz时钟
        packets = self.packetizer.packetize(frame_data, timestamp)
        
        # 发送到每个播放中的客户端
        for session in list(self.clients.values()):
            if session.state == RTSPState.PLAYING:
                for packet in packets:
                    session.send_rtp_packet(packet)
    
    async def send_frame(self, frame_data: bytes, metadata: Dict[str, Any]) -> bool:
        """发送视频帧（供外部调用）"""
        try:
            await self._send_video_frame(frame_data)
            self.stats["bytes_sent"] += len(frame_data)
            self.stats["frames_sent"] += 1
            return True
        except Exception as e:
            logger.error(f"Error sending frame: {e}")
            self.stats["errors"] += 1
            return False
    
    async def send_audio(self, audio_data: bytes, metadata: Dict[str, Any]) -> bool:
        """发送音频数据"""
        # TODO: 实现音频RTP封装
        logger.debug("Audio sending not yet implemented")
        return True
    
    async def handle_control(self, control_data: Dict[str, Any]) -> bool:
        """处理控制指令"""
        try:
            logger.info(f"Received control data: {control_data}")
            return True
        except Exception as e:
            logger.error(f"Error handling control: {e}")
            self.stats["errors"] += 1
            return False
    
    def set_video_source(self, callback: Callable[[], bytes]):
        """设置视频数据源回调"""
        self.video_source_callback = callback
    
    def get_session_info(self) -> Dict[str, Any]:
        """获取会话信息"""
        return {
            'clients': len(self.clients),
            'streaming': self.is_streaming,
            'sessions': [
                {
                    'id': s.client_id,
                    'state': s.state.value,
                    'address': s.address,
                    'frames_sent': s.frames_sent
                }
                for s in self.clients.values()
            ]
        }
