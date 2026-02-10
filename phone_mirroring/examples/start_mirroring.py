"""
示例启动脚本
展示如何使用核心功能模块
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def start_screen_mirroring():
    """启动桌面屏幕投屏"""
    from phone_mirroring.streaming_manager import start_screen_mirror
    from phone_mirroring.config import Config
    
    try:
        config = Config()
        
        # 配置参数
        stream_config = {
            'port': 8554,
            'width': 1920,
            'height': 1080,
            'fps': 30,
            'bitrate': 2000000,
            'capture_method': 'mss'
        }
        
        logger.info("🚀 启动屏幕投屏...")
        logger.info(f"配置: {stream_config}")
        
        manager = await start_screen_mirror(stream_config)
        
        logger.info(f"✅ 屏幕投屏已启动")
        logger.info(f"📡 RTSP地址: rtsp://localhost:{stream_config['port']}/")
        logger.info(f"🎥 分辨率: {stream_config['width']}x{stream_config['height']}")
        logger.info(f"📊 帧率: {stream_config['fps']} FPS")
        logger.info("")
        logger.info("使用方法:")
        logger.info("1. 在同一WiFi下的设备上使用VLC或其他播放器")
        logger.info("2. 打开网络串流，输入上面的RTSP地址")
        logger.info("3. 按 Ctrl+C 停止投屏")
        logger.info("")
        
        # 保持运行
        while True:
            stats = manager.get_stats()
            logger.debug(f"Stats: {stats}")
            await asyncio.sleep(5)
            
    except Exception as e:
        logger.error(f"❌ 屏幕投屏失败: {e}")
        raise

async def start_adb_mirroring(device_id: Optional[str] = None):
    """启动ADB设备投屏
    
    Args:
        device_id: 设备ID，如果为None则自动检测
    """
    from phone_mirroring.protocols.adb import ADBProtocol
    from phone_mirroring.streaming_manager import start_adb_mirror
    
    try:
        logger.info("🚀 启动ADB投屏...")
        
        # 创建ADB协议实例
        adb_config = {
            'adb_port': 5555,
            'scrcpy_port': 27183,
            'device_id': device_id or '',
            'max_width': 1920,
            'max_height': 1080,
            'bitrate': 2000000,
            'max_fps': 30
        }
        
        adb = ADBProtocol(adb_config)
        
        # 启动ADB
        if not await adb.start():
            logger.error("❌ 无法启动ADB")
            return
        
        logger.info(f"✅ ADB已连接: {adb.active_device}")
        
        # 配置RTSP流
        stream_config = {
            'port': 8554
        }
        
        manager = await start_adb_mirror(adb, stream_config)
        
        logger.info(f"✅ ADB投屏已启动")
        logger.info(f"📡 RTSP地址: rtsp://localhost:{stream_config['port']}/")
        logger.info("")
        logger.info("使用方法:")
        logger.info("1. 在同一WiFi下的设备上使用VLC或其他播放器")
        logger.info("2. 打开网络串流，输入上面的RTSP地址")
        logger.info("3. 按 Ctrl+C 停止投屏")
        logger.info("")
        
        # 保持运行
        while True:
            stats = manager.get_stats()
            adb_info = adb.get_device_info()
            logger.debug(f"Stats: {stats}")
            logger.debug(f"Device: {adb_info}")
            await asyncio.sleep(5)
            
    except Exception as e:
        logger.error(f"❌ ADB投屏失败: {e}")
        raise

async def start_full_server():
    """启动完整服务器（屏幕+ADB）"""
    from phone_mirroring.server import MirroringServer, create_server
    from phone_mirroring.config import Config
    
    try:
        logger.info("🚀 启动完整服务器...")
        
        config = Config()
        config.enabled_protocols = ["RTSP", "ADB"]
        config.video.width = 1920
        config.video.height = 1080
        config.video.fps = 30
        config.video.bitrate = 2000000
        config.network.port = 8554
        
        server = await create_server(config)
        
        logger.info(f"✅ 服务器已启动")
        logger.info(f"📡 RTSP地址: rtsp://localhost:{config.network.port}/")
        logger.info(f"🔧 启用的协议: {', '.join(server.get_active_protocols())}")
        logger.info("")
        logger.info("功能:")
        logger.info("- 桌面屏幕投屏: 使用RTSP协议")
        logger.info("- Android设备投屏: 连接USB设备自动启动")
        logger.info("- 按 Ctrl+C 停止服务器")
        logger.info("")
        
        # 保持运行
        while server.is_running:
            stats = server.get_stats()
            logger.debug(f"Server stats: {stats}")
            await asyncio.sleep(5)
            
    except Exception as e:
        logger.error(f"❌ 服务器启动失败: {e}")
        raise

def print_usage():
    """打印使用说明"""
    print("""
WiFi手机投屏系统 - 示例启动脚本

使用方法:
    python examples\start_mirroring.py <mode>

模式:
    screen          - 启动桌面屏幕投屏
    adb [device_id] - 启动ADB设备投屏
    server          - 启动完整服务器
    help            - 显示此帮助信息

示例:
    python examples\start_mirroring.py screen
    python examples\start_mirroring.py adb
    python examples\start_mirroring.py adb 127.0.0.1:5555
    python examples\start_mirroring.py server
    """)

async def main():
    """主函数"""
    # 处理命令行参数
    if len(sys.argv) < 2:
        print_usage()
        return
    
    mode = sys.argv[1].lower()
    
    # 设置信号处理
    def signal_handler(sig, frame):
        logger.info("\n🛑 接收到停止信号，正在关闭...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if mode == 'screen':
            await start_screen_mirroring()
        elif mode == 'adb':
            device_id = sys.argv[2] if len(sys.argv) > 2 else None
            await start_adb_mirroring(device_id)
        elif mode == 'server':
            await start_full_server()
        elif mode == 'help':
            print_usage()
        else:
            print(f"未知模式: {mode}")
            print_usage()
            
    except KeyboardInterrupt:
        logger.info("\n👋 已停止")
    except Exception as e:
        logger.error(f"发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
