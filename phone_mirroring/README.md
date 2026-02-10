# WiFi 手机投屏系统

一个基于 Python 的 WiFi 手机投屏解决方案，支持桌面屏幕镜像和 Android 设备投屏。

## 功能特性

- **桌面屏幕投屏**: 将电脑屏幕实时投射到其他设备
- **Android设备投屏**: 通过 ADB 连接 Android 手机并镜像屏幕
- **RTSP流媒体协议**: 使用标准 RTSP/RTP 协议传输视频
- **H.264视频编码**: 高效的视频压缩和传输
- **模块化设计**: 易于扩展和维护

## 系统架构

```
phone_mirroring/
├── video_encoder.py          # 视频编码模块 (H.264)
├── screen_capture.py         # 屏幕捕获模块
├── streaming_manager.py      # 流媒体管理器
├── protocols/
│   ├── base.py              # 协议基类
│   ├── rtsp.py              # RTSP/RTP 协议实现
│   └── adb.py               # ADB 协议实现
├── server.py                # 主服务器
├── config.py                # 配置管理
└── app_main.py              # 应用集成
```

## 快速开始

### 安装依赖

```bash
cd phone_mirroring
pip install -r requirements.txt
```

### 启动桌面屏幕投屏

```bash
# 快速启动
python -m phone_mirroring.app_main screen

# 或指定参数
python -m phone_mirroring.app_main screen --port 8554 --quality high
```

### 启动 ADB 投屏 (Android 设备)

```bash
# 连接 USB 设备自动投屏
python -m phone_mirroring.app_main adb

# 指定设备
python -m phone_mirroring.app_main adb --device 127.0.0.1:5555
```

### 启动完整服务器

```bash
python -m phone_mirroring.app_main server
```

### 使用示例脚本

```bash
# 桌面投屏
python examples\start_mirroring.py screen

# ADB投屏
python examples\start_mirroring.py adb

# 完整服务器
python examples\start_mirroring.py server
```

## 使用方法

### 查看投屏

启动后，在同一 WiFi 网络下的设备上使用播放器打开 RTSP 地址：

```
rtsp://<电脑IP>:8554/
```

支持的播放器：
- VLC 媒体播放器
- PotPlayer
- 手机端的 RTSP 播放器（如 VLC for Mobile）

### Python API 使用

```python
import asyncio
from phone_mirroring.app_main import MirroringApp

async def main():
    # 创建应用
    app = MirroringApp()
    
    # 配置
    app.setup(preset='high_quality')  # 或 'low_latency', 'mobile_optimized'
    
    # 启动屏幕投屏
    await app.start_screen_mirroring({
        'port': 8554,
        'width': 1920,
        'height': 1080,
        'fps': 30,
        'bitrate': 2000000
    })
    
    # 保持运行
    await asyncio.sleep(3600)
    
    # 停止
    await app.stop()

asyncio.run(main())
```

### ADB 投屏示例

```python
import asyncio
from phone_mirroring.app_main import MirroringApp

async def main():
    app = MirroringApp()
    
    # 启动 ADB 投屏
    await app.start_adb_mirroring(device_id='your-device-id')
    
    # 保持运行
    await asyncio.sleep(3600)
    
    await app.stop()

asyncio.run(main())
```

## 配置说明

### 视频质量预设

- **low**: 1280x720, 15fps, 1Mbps - 低带宽模式
- **medium**: 1920x1080, 30fps, 2Mbps - 标准质量（默认）
- **high**: 1920x1080, 30fps, 4Mbps - 高质量
- **ultra**: 2560x1440, 60fps, 8Mbps - 超高质量

### 自定义配置

```python
from phone_mirroring.config import Config

config = Config()
config.video.width = 1920
config.video.height = 1080
config.video.fps = 60
config.video.bitrate = 4000000
config.network.port = 8554
config.enabled_protocols = ["RTSP", "ADB"]

# 使用配置
app = MirroringApp()
app.setup(config=config)
```

## 技术细节

### 视频编码

- **编码格式**: H.264
- **编码器**: FFmpeg (libx264) 或硬件加速 (NVENC/QuickSync)
- **像素格式**: YUV420p
- **关键帧间隔**: 30帧

### 屏幕捕获

- **Windows**: 使用 MSS 库（性能最佳）
- **捕获速率**: 可配置，默认 30 FPS
- **支持区域捕获**: 可以只捕获屏幕的一部分

### RTSP/RTP 协议

- **RTSP端口**: 8554 (可配置)
- **RTP端口范围**: 5000-6000
- **Payload类型**: 96 (H.264), 97 (AAC)
- **时钟频率**: 90kHz

### ADB 协议

- **ADB端口**: 5555
- **Scrcpy端口**: 27183
- **支持设备**: 所有启用 ADB 调试的 Android 设备
- **控制功能**: 触摸、滑动、按键、文本输入

## 目录结构

```
phone_mirroring/
├── __init__.py                 # 包初始化
├── app.py                      # 应用入口
├── app_main.py                 # 主应用集成
├── server.py                   # 投屏服务器
├── config.py                   # 配置管理
├── video_encoder.py            # 视频编码
├── screen_capture.py           # 屏幕捕获
├── streaming_manager.py        # 流管理器
├── error_handling.py           # 错误处理
├── performance.py              # 性能优化
├── client.py                   # 客户端
├── control.py                  # 控制模块
├── requirements.txt            # 依赖列表
├── requirements-dev.txt        # 开发依赖
├── protocols/                  # 协议模块
│   ├── __init__.py
│   ├── base.py                # 协议基类
│   ├── rtsp.py                # RTSP/RTP实现
│   ├── adb.py                 # ADB协议
│   └── webrtc.py              # WebRTC协议
├── gui/                        # GUI界面
│   ├── __init__.py
│   ├── main_window.py         # 主窗口
│   ├── dialogs/               # 对话框
│   └── widgets/               # 自定义控件
└── examples/                   # 示例代码
    ├── start_mirroring.py     # 启动示例
    ├── adb_client.py          # ADB客户端示例
    └── simple_server.py       # 简单服务器示例
```

## 依赖说明

### 必需依赖

- Python 3.8+
- PyQt5: GUI框架
- qasync: Qt异步集成
- opencv-python: 视频处理
- numpy: 数值计算
- Pillow: 图像处理
- mss: 屏幕捕获

### 可选依赖

- FFmpeg: 视频编码（推荐）
- scrcpy: Android投屏工具
- ADB: Android调试桥

### 安装 FFmpeg

**Windows:**
1. 下载 FFmpeg: https://ffmpeg.org/download.html
2. 解压并添加到系统 PATH
3. 验证: `ffmpeg -version`

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

### 安装 Scrcpy

**Windows:**
1. 下载 Scrcpy: https://github.com/Genymobile/scrcpy/releases
2. 解压并添加到系统 PATH

**macOS:**
```bash
brew install scrcpy
```

**Linux:**
```bash
sudo apt install scrcpy
```

## 故障排除

### RTSP 连接失败

1. 检查防火墙设置，确保端口 8554 和 5000-6000 开放
2. 确认设备和电脑在同一 WiFi 网络
3. 检查 VLC 播放器是否支持 RTSP

### ADB 连接失败

1. 在 Android 设备上启用 USB 调试
2. 确认已安装 ADB 工具: `adb version`
3. 尝试重新授权: `adb kill-server && adb start-server`
4. 检查设备是否被识别: `adb devices`

### 视频卡顿

1. 降低视频质量: `--quality low`
2. 减少帧率: 修改 config.video.fps = 15
3. 降低分辨率: 修改 config.video.width/height
4. 使用有线网络连接

### 编码器错误

1. 确保 FFmpeg 已安装并添加到 PATH
2. 检查编码器是否可用: `ffmpeg -encoders | grep h264`
3. 尝试使用软件编码: 修改 preset 为 'ultrafast'

## 性能优化

### 降低延迟

```python
config = Config()
config.video.fps = 30
config.video.bitrate = 1000000  # 降低码率
config.network.buffer_size = 32768  # 减少缓冲区
```

### 提高质量

```python
config = Config()
config.video.width = 1920
config.video.height = 1080
config.video.fps = 60
config.video.bitrate = 8000000  # 8Mbps
config.video.quality = 'ultra'
```

### 使用硬件加速

```python
from phone_mirroring.video_encoder import HardwareEncoder, EncodeConfig

config = EncodeConfig()
encoder = HardwareEncoder(config)
encoder.start()
```

## 开发指南

### 添加新的视频源

```python
class CustomVideoSource:
    def get_frame(self) -> bytes:
        # 返回 H.264 编码的视频帧
        return frame_data

# 注册到 RTSP 服务器
rtsp_server.set_video_source(custom_source.get_frame)
```

### 添加新的协议

```python
from phone_mirroring.protocols.base import BaseProtocol

class CustomProtocol(BaseProtocol):
    async def start(self) -> bool:
        # 启动协议
        pass
    
    async def stop(self) -> bool:
        # 停止协议
        pass
    
    async def send_frame(self, frame_data, metadata):
        # 发送视频帧
        pass
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.0.0
- 初始版本发布
- 支持桌面屏幕投屏
- 支持 ADB 设备投屏
- 实现 RTSP/RTP 协议
- 集成 H.264 视频编码
