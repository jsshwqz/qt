"""
模块加载测试
验证所有核心模块是否可以正确导入
"""

import sys
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_imports():
    """测试所有模块导入"""
    results = []
    
    # 测试协议模块
    try:
        from phone_mirroring.protocols.base import BaseProtocol
        logger.info("✅ protocols/base.py 加载成功")
        results.append(("protocols/base", True, None))
    except Exception as e:
        logger.error(f"❌ protocols/base.py 加载失败: {e}")
        results.append(("protocols/base", False, str(e)))
    
    try:
        from phone_mirroring.protocols.rtsp import RTSPProtocol, RTPPacket, H264Packetizer
        logger.info("✅ protocols/rtsp.py 加载成功")
        results.append(("protocols/rtsp", True, None))
    except Exception as e:
        logger.error(f"❌ protocols/rtsp.py 加载失败: {e}")
        results.append(("protocols/rtsp", False, str(e)))
    
    try:
        from phone_mirroring.protocols.adb import ADBProtocol, H264Parser
        logger.info("✅ protocols/adb.py 加载成功")
        results.append(("protocols/adb", True, None))
    except Exception as e:
        logger.error(f"❌ protocols/adb.py 加载失败: {e}")
        results.append(("protocols/adb", False, str(e)))
    
    # 测试核心模块
    try:
        from phone_mirroring.config import Config, Presets
        logger.info("✅ config.py 加载成功")
        results.append(("config", True, None))
    except Exception as e:
        logger.error(f"❌ config.py 加载失败: {e}")
        results.append(("config", False, str(e)))
    
    try:
        from phone_mirroring.video_encoder import VideoEncoder, FFmpegEncoder, EncodeConfig
        logger.info("✅ video_encoder.py 加载成功")
        results.append(("video_encoder", True, None))
    except Exception as e:
        logger.error(f"❌ video_encoder.py 加载失败: {e}")
        results.append(("video_encoder", False, str(e)))
    
    try:
        from phone_mirroring.screen_capture import ScreenCapture, CaptureConfig
        logger.info("✅ screen_capture.py 加载成功")
        results.append(("screen_capture", True, None))
    except Exception as e:
        logger.error(f"❌ screen_capture.py 加载失败: {e}")
        results.append(("screen_capture", False, str(e)))
    
    try:
        from phone_mirroring.streaming_manager import StreamingManager, StreamSource
        logger.info("✅ streaming_manager.py 加载成功")
        results.append(("streaming_manager", True, None))
    except Exception as e:
        logger.error(f"❌ streaming_manager.py 加载失败: {e}")
        results.append(("streaming_manager", False, str(e)))
    
    try:
        from phone_mirroring.server import MirroringServer, create_server
        logger.info("✅ server.py 加载成功")
        results.append(("server", True, None))
    except Exception as e:
        logger.error(f"❌ server.py 加载失败: {e}")
        results.append(("server", False, str(e)))
    
    try:
        from phone_mirroring.app_main import MirroringApp
        logger.info("✅ app_main.py 加载成功")
        results.append(("app_main", True, None))
    except Exception as e:
        logger.error(f"❌ app_main.py 加载失败: {e}")
        results.append(("app_main", False, str(e)))
    
    # 汇总结果
    logger.info("\n" + "="*50)
    logger.info("模块加载测试结果汇总")
    logger.info("="*50)
    
    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)
    
    for name, success, error in results:
        status = "✅" if success else "❌"
        logger.info(f"{status} {name}")
        if error:
            logger.info(f"   错误: {error}")
    
    logger.info("="*50)
    logger.info(f"总计: {success_count}/{total_count} 个模块加载成功")
    
    return success_count == total_count

def test_rtsp_packet():
    """测试RTSP包创建"""
    try:
        from phone_mirroring.protocols.rtsp import RTPPacket, H264Packetizer
        
        # 测试RTP包
        packet = RTPPacket()
        packet.sequence_number = 100
        packet.timestamp = 12345
        packet.ssrc = 0x12345678
        packet.payload = b'\x00\x00\x00\x01test_data'
        
        packed = packet.pack()
        assert len(packed) > 12, "RTP包头部长度应为12字节"
        
        # 测试H264分包器
        packetizer = H264Packetizer(mtu=1400)
        
        # 创建测试帧数据（带起始码）
        test_frame = b'\x00\x00\x00\x01' + b'A' * 1000
        packets = packetizer.packetize(test_frame)
        
        assert len(packets) > 0, "应至少生成一个RTP包"
        
        logger.info("✅ RTSP/RTP 功能测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ RTSP/RTP 功能测试失败: {e}")
        return False

def test_h264_parser():
    """测试H264解析器"""
    try:
        from phone_mirroring.protocols.adb import H264Parser, VideoFrameInfo
        
        parser = H264Parser()
        
        # 测试NAL单元检测
        test_data = b'\x00\x00\x00\x01\x67' + b'A' * 100  # SPS NAL单元
        parser.feed_data(test_data)
        
        assert parser.sps_data is not None, "应检测到SPS数据"
        
        # 测试帧解析
        test_frame = (
            b'\x00\x00\x00\x01\x67' + b'S' * 50 +  # SPS
            b'\x00\x00\x00\x01\x68' + b'P' * 50 +  # PPS
            b'\x00\x00\x00\x01\x65' + b'I' * 100   # IDR帧
        )
        
        frames_received = []
        def frame_callback(data, info):
            frames_received.append((data, info))
        
        parser.frame_callback = frame_callback
        parser.feed_data(test_frame)
        parser._emit_frame()  # 手动触发帧发送
        
        logger.info(f"✅ H264解析器测试通过，收到 {len(frames_received)} 帧")
        return True
        
    except Exception as e:
        logger.error(f"❌ H264解析器测试失败: {e}")
        return False

def test_config():
    """测试配置模块"""
    try:
        from phone_mirroring.config import Config, Presets
        
        # 测试默认配置
        config = Config()
        assert config.video.width == 1920
        assert config.video.fps == 30
        
        # 测试预设
        high_quality = Presets.high_quality()
        assert high_quality.video.bitrate == 5000000
        
        mobile = Presets.mobile_optimized()
        assert mobile.video.width == 1280
        
        # 测试配置转换
        config_dict = config.to_dict()
        assert 'video' in config_dict
        assert 'audio' in config_dict
        
        logger.info("✅ 配置模块测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 配置模块测试失败: {e}")
        return False

def main():
    """主测试函数"""
    logger.info("\n" + "="*50)
    logger.info("WiFi投屏系统 - 模块测试")
    logger.info("="*50 + "\n")
    
    # 运行所有测试
    tests = [
        ("模块导入测试", test_imports),
        ("RTSP包测试", test_rtsp_packet),
        ("H264解析器测试", test_h264_parser),
        ("配置模块测试", test_config),
    ]
    
    results = []
    for name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"运行: {name}")
        logger.info('='*50)
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            logger.error(f"测试异常: {e}")
            results.append((name, False))
    
    # 汇总
    logger.info("\n" + "="*50)
    logger.info("测试汇总")
    logger.info("="*50)
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        logger.info(f"{status} - {name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    logger.info("="*50)
    logger.info(f"结果: {passed}/{total} 测试通过")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
