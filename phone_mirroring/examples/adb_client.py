"""
ADB客户端示例 - 连接Android设备
"""

import asyncio
import logging
from phone_mirroring import MirroringServer, Config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    """主函数 - 展示ADB投屏功能"""
    
    # 创建ADB专用配置
    config = Config()
    config.enabled_protocols = ["ADB"]  # 只启用ADB协议
    config.video.width = 1920
    config.video.height = 1080
    config.video.fps = 30
    config.video.bitrate = 2000000
    config.control.enable_touch = True
    config.control.enable_keyboard = True
    config.control.enable_mouse = True
    
    # ADB特定配置
    adb_config = {
        "device_id": "",  # 留空自动检测
        "max_width": 1920,
        "max_height": 1080,
        "bitrate": 2000000,
        "max_fps": 30,
        "scrcpy_port": 27183
    }
    
    # 创建服务器
    server = MirroringServer(config)
    
    # 注册回调函数
    def on_server_started():
        print("✅ ADB投屏服务器启动成功")
        print("\n使用说明:")
        print("1. 确保Android设备已启用USB调试")
        print("2. 通过USB连接设备或使用adb connect连接网络设备")
        print("3. 服务器将自动检测并连接设备")
        print("\n控制功能:")
        print("- 点击: 在屏幕上点击")
        print("- 滑动: 从一点滑动到另一点")
        print("- 按键: 发送Android按键事件")
        print("- 文本: 输入文字")
    
    def on_client_connected(client_id, address):
        print(f"\n📱 设备已连接: {client_id}")
        print(f"   地址: {address}")
    
    def on_client_disconnected(client_id):
        print(f"\n❌ 设备已断开: {client_id}")
    
    def on_frame_received(frame_data, metadata):
        if metadata.get("size", 0) > 0:
            print(f"📺 收到视频帧: {metadata['size']} bytes")
            # 这里可以解码并显示视频帧
            # 也可以转发给其他客户端
    
    server.register_callback("server_started", on_server_started)
    server.register_callback("client_connected", on_client_connected)
    server.register_callback("client_disconnected", on_client_disconnected)
    server.register_callback("frame_received", on_frame_received)
    
    # 启动服务器
    print("🚀 启动ADB投屏服务器...")
    success = await server.start()
    
    if success:
        print("\n⏳ 等待设备连接...")
        
        # 模拟控制输入的协程
        async def demo_controls():
            """演示控制功能"""
            await asyncio.sleep(10)  # 等待设备连接
            
            while server.is_running:
                try:
                    # 检查是否有连接的设备
                    if server.get_client_count() > 0:
                        print("\n🎮 演示控制功能...")
                        
                        # 点击屏幕中心
                        await server.handle_control({
                            "type": "touch",
                            "action": "click",
                            "x": 960,
                            "y": 540
                        })
                        print("   点击屏幕中心")
                        
                        await asyncio.sleep(2)
                        
                        # 滑动操作
                        await server.handle_control({
                            "type": "gesture",
                            "action": "swipe",
                            "x1": 100,
                            "y1": 540,
                            "x2": 1000,
                            "y2": 540,
                            "duration": 500
                        })
                        print("   向右滑动")
                        
                        await asyncio.sleep(2)
                        
                        # 按下Home键
                        await server.handle_control({
                            "type": "system",
                            "action": "home"
                        })
                        print("   按下Home键")
                        
                        # 等待30秒后继续演示
                        await asyncio.sleep(30)
                    else:
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    print(f"❌ 控制演示出错: {e}")
                    await asyncio.sleep(5)
        
        # 运行控制演示
        asyncio.create_task(demo_controls())
        
        # 保持运行
        try:
            while server.is_running:
                await asyncio.sleep(5)
                
                # 定期打印状态
                if server.get_client_count() > 0:
                    stats = server.get_stats()
                    print(f"\n📊 状态统计:")
                    print(f"   连接设备数: {server.get_client_count()}")
                    print(f"   总接收帧数: {stats['total_frames']}")
                    print(f"   接收字节数: {stats['total_bytes_received'] / 1024:.1f} KB")
        
        except KeyboardInterrupt:
            print("\n\n🛑 收到中断信号，正在关闭服务器...")
        
        finally:
            await server.stop()
            print("👋 服务器已关闭")
    else:
        print("❌ 服务器启动失败！")
        print("\n可能的解决方案:")
        print("1. 确保已安装Android SDK platform-tools")
        print("2. 确保adb命令在系统PATH中")
        print("3. 检查设备是否正确连接并启用USB调试")

if __name__ == "__main__":
    asyncio.run(main())