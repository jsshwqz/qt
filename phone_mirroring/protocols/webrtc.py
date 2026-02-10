"""
WebRTC协议实现
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List, Set
from .base import BaseProtocol

logger = logging.getLogger(__name__)

try:
    import aiohttp
    import websockets
    from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
    from aiortc.contrib.media import MediaStreamTrack, MediaPlayer, MediaRecorder
    from av import VideoFrame, AudioFrame
    WEBRTC_AVAILABLE = True
except ImportError:
    logger.warning("WebRTC dependencies not installed. Please install: pip install aiohttp websockets aiortc av")
    WEBRTC_AVAILABLE = False

class WebRTCTrack(MediaStreamTrack):
    """WebRTC媒体轨道"""
    
    kind = "video"
    
    def __init__(self, track_type: str = "video"):
        super().__init__()
        self.track_type = track_type
        self._queue = asyncio.Queue()
        self._ended = False
    
    async def recv(self):
        """接收帧数据"""
        if self._ended:
            raise MediaStreamTrack.EndedError
        
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            # 返回空帧而不是结束流
            if self.track_type == "video":
                return VideoFrame.from_ndarray(
                    __import__('numpy').zeros((480, 640, 3), dtype=__import__('numpy').uint8),
                    format="rgb24"
                )
            else:
                return AudioFrame.from_ndarray(
                    __import__('numpy').zeros((1024,), dtype=__import__('numpy').int16),
                    format="s16",
                    layout="mono"
                )
    
    def put_frame(self, frame):
        """放入帧数据"""
        if not self._ended:
            self._queue.put_nowait(frame)
    
    def stop(self):
        """停止轨道"""
        self._ended = True
        self._queue.put_nowait(None)

class WebRTCProtocol(BaseProtocol):
    """WebRTC协议实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.connections: Dict[str, RTCPeerConnection] = {}
        self.websockets: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.server: Optional[websockets.WebSocketServer] = None
        self.video_track: Optional[WebRTCTrack] = None
        self.audio_track: Optional[WebRTCTrack] = None
        
        # WebRTC配置
        self.signaling_port = config.get("signaling_port", 8081)
        self.ice_servers = [
            RTCIceServer("stun:stun.l.google.com:19302")
        ] + config.get("ice_servers", [])
        
        if not WEBRTC_AVAILABLE:
            logger.error("WebRTC dependencies not available")
    
    async def start(self) -> bool:
        """启动WebRTC服务"""
        if not WEBRTC_AVAILABLE:
            logger.error("Cannot start WebRTC: dependencies not installed")
            return False
        
        try:
            self.is_running = True
            self.stats["start_time"] = time.time()
            
            # 创建HTTP会话
            self.http_session = aiohttp.ClientSession()
            
            # 创建媒体轨道
            self.video_track = WebRTCTrack("video")
            self.audio_track = WebRTCTrack("audio")
            
            # 启动WebSocket信令服务器
            self.server = await websockets.serve(
                self._handle_websocket,
                "0.0.0.0",
                self.signaling_port
            )
            
            logger.info(f"WebRTC signaling server started on port {self.signaling_port}")
            self.emit("started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start WebRTC server: {e}")
            self.stats["errors"] += 1
            return False
    
    async def stop(self) -> bool:
        """停止WebRTC服务"""
        try:
            self.is_running = False
            
            # 停止所有连接
            for connection in list(self.connections.values()):
                await connection.close()
            
            # 停止媒体轨道
            if self.video_track:
                self.video_track.stop()
            if self.audio_track:
                self.audio_track.stop()
            
            # 关闭WebSocket服务器
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            
            # 关闭HTTP会话
            if self.http_session:
                await self.http_session.close()
            
            logger.info("WebRTC server stopped")
            self.emit("stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping WebRTC server: {e}")
            return False
    
    async def _handle_websocket(self, websocket, path):
        """处理WebSocket信令"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}_{int(time.time())}"
        self.websockets[client_id] = websocket
        
        self.stats["connected_clients"] += 1
        logger.info(f"New WebRTC client connected: {client_id}")
        self.emit("client_connected", client_id, websocket.remote_address)
        
        try:
            async for message in websocket:
                data = json.loads(message)
                await self._handle_signaling(client_id, data)
                self.stats["bytes_received"] += len(message)
                
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Error handling WebRTC client {client_id}: {e}")
            self.stats["errors"] += 1
        finally:
            # 清理连接
            if client_id in self.connections:
                await self.connections[client_id].close()
                del self.connections[client_id]
            
            if client_id in self.websockets:
                del self.websockets[client_id]
            
            self.stats["connected_clients"] -= 1
            logger.info(f"WebRTC client disconnected: {client_id}")
            self.emit("client_disconnected", client_id)
    
    async def _handle_signaling(self, client_id: str, data: Dict[str, Any]):
        """处理信令消息"""
        message_type = data.get("type")
        
        if message_type == "offer":
            await self._handle_offer(client_id, data)
        elif message_type == "answer":
            await self._handle_answer(client_id, data)
        elif message_type == "ice-candidate":
            await self._handle_ice_candidate(client_id, data)
        elif message_type == "control":
            await self.handle_control(data.get("data", {}))
        else:
            logger.warning(f"Unknown signaling message type: {message_type}")
    
    async def _handle_offer(self, client_id: str, data: Dict[str, Any]):
        """处理Offer信令"""
        try:
            # 创建RTCPeerConnection
            configuration = RTCConfiguration(self.ice_servers)
            pc = RTCPeerConnection(configuration)
            self.connections[client_id] = pc
            
            # 添加媒体轨道
            if self.video_track:
                pc.addTrack(self.video_track)
            if self.audio_track:
                pc.addTrack(self.audio_track)
            
            # 设置连接事件处理器
            @pc.on("iceconnectionstatechange")
            async def on_iceconnectionstatechange():
                logger.info(f"ICE connection state for {client_id}: {pc.iceConnectionState}")
                if pc.iceConnectionState == "failed":
                    await pc.close()
                    if client_id in self.connections:
                        del self.connections[client_id]
            
            @pc.on("track")
            def on_track(track):
                logger.info(f"Track {track.kind} received from {client_id}")
            
            # 设置远端描述
            offer = RTCSessionDescription(
                sdp=data["sdp"],
                type=data["type"]
            )
            await pc.setRemoteDescription(offer)
            
            # 创建Answer
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            
            # 发送Answer
            await self._send_signaling(client_id, {
                "type": answer.type,
                "sdp": answer.sdp
            })
            
        except Exception as e:
            logger.error(f"Error handling offer for {client_id}: {e}")
            self.stats["errors"] += 1
    
    async def _handle_answer(self, client_id: str, data: Dict[str, Any]):
        """处理Answer信令"""
        # 通常服务器端不需要处理answer，因为我们是主动发送方
        pass
    
    async def _handle_ice_candidate(self, client_id: str, data: Dict[str, Any]):
        """处理ICE候选"""
        try:
            pc = self.connections.get(client_id)
            if pc:
                from aiortc import RTCIceCandidate
                candidate = RTCIceCandidate(
                    component=data["candidate"]["component"],
                    foundation=data["candidate"]["foundation"],
                    ip=data["candidate"]["ip"],
                    port=data["candidate"]["port"],
                    priority=data["candidate"]["priority"],
                    protocol=data["candidate"]["protocol"],
                    type=data["candidate"]["type"],
                    sdpMid=data["candidate"]["sdpMid"],
                    sdpMLineIndex=data["candidate"]["sdpMLineIndex"]
                )
                await pc.addIceCandidate(candidate)
        except Exception as e:
            logger.error(f"Error handling ICE candidate for {client_id}: {e}")
    
    async def _send_signaling(self, client_id: str, data: Dict[str, Any]):
        """发送信令消息"""
        websocket = self.websockets.get(client_id)
        if websocket:
            try:
                message = json.dumps(data)
                await websocket.send(message)
                self.stats["bytes_sent"] += len(message)
            except Exception as e:
                logger.error(f"Error sending signaling to {client_id}: {e}")
    
    async def send_frame(self, frame_data: bytes, metadata: Dict[str, Any]) -> bool:
        """发送视频帧"""
        if not WEBRTC_AVAILABLE or not self.video_track:
            return False
        
        try:
            # 转换为VideoFrame
            import cv2
            import numpy as np
            
            # 假设frame_data是H.264编码数据，需要解码
            # 这里简化处理，实际需要根据编码格式处理
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
                video_frame.pts = int(time.time() * 90000)  # 90kHz时钟
                video_frame.time_base = None
                
                self.video_track.put_frame(video_frame)
                self.stats["frames_sent"] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending WebRTC frame: {e}")
            self.stats["errors"] += 1
            return False
    
    async def send_audio(self, audio_data: bytes, metadata: Dict[str, Any]) -> bool:
        """发送音频数据"""
        if not WEBRTC_AVAILABLE or not self.audio_track:
            return False
        
        try:
            # 转换为AudioFrame
            import numpy as np
            
            # 假设音频是16位PCM格式
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            audio_frame = AudioFrame.from_ndarray(
                audio_array.reshape(1, -1),
                format="s16",
                layout="mono"
            )
            audio_frame.pts = int(time.time() * 44100)  # 44.1kHz采样率
            audio_frame.sample_rate = 44100
            
            self.audio_track.put_frame(audio_frame)
            return True
            
        except Exception as e:
            logger.error(f"Error sending WebRTC audio: {e}")
            self.stats["errors"] += 1
            return False
    
    async def handle_control(self, control_data: Dict[str, Any]) -> bool:
        """处理控制指令"""
        try:
            # 通过信令通道广播控制指令
            message = {
                "type": "control",
                "data": control_data
            }
            
            for client_id in self.websockets:
                await self._send_signaling(client_id, message)
            
            logger.info(f"Broadcast control data: {control_data}")
            return True
            
        except Exception as e:
            logger.error(f"Error handling WebRTC control: {e}")
            self.stats["errors"] += 1
            return False