"""
简单的投屏服务器示例
"""

import asyncio
import logging
from phone_mirroring import MirroringServer, Config, Presets

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    """主函数"""
    # 使用预设的高质量配置
    config = Presets.high_quality()
    config.enabled_protocols = ["RTSP", "ADB"]  # 启用RTSP和ADB协议
    
    # 创建服务器
    server = MirroringServer(config)
    
    # 注册事件回调
    def on_client_connected(client_id, address):
        print(f"客户端连接: {client_id} from {address}")
    
    def on_frame_received(frame_data, metadata):
        print(f"收到帧数据: 大小={len(frame_data)}bytes")
        # 这里可以转发给其他客户端
    
    server.register_callback("client_connected", on_client_connected)
    server.register_callback("frame_received", on_frame_received)
    
    # 启动服务器
    print("启动投屏服务器...")
    success = await server.start()
    
    if success:
        print(f"服务器启动成功！")
        print(f"RTSP地址: rtsp://localhost:{config.network.port}/stream")
        print(f"支持的协议: {', '.join(server.get_active_protocols())}")
        
        # 模拟发送一些测试帧
        test_frame = b"\x00\x01\x02\x03" * 1000  # 模拟视频帧数据
        
        # 保持运行
        try:
            while server.is_running:
                await asyncio.sleep(1)
                
                # 定期发送测试帧
                if server.get_client_count() > 0:
                    await server.broadcast_frame(test_frame)
                
                # 打印统计信息
                if server.get_client_count() > 0:
                    stats = server.get_stats()
                    print(f"当前连接数: {server.get_client_count()}, "
                          f"总帧数: {stats['total_frames']}")
        
        except KeyboardInterrupt:
            print("\n收到中断信号，正在关闭服务器...")
        
        finally:
            await server.stop()
            print("服务器已关闭")
    else:
        print("服务器启动失败！")

if __name__ == "__main__":
    asyncio.run(main())