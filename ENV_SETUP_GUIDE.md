# Native Mirroring Pro - 环境配置与运行手册

## 1. 快速开始 (推荐方式)
本项目已提供预编译的 `dist/NativeMirroringPro.exe`。只需双击即可运行。

## 2. 开发者环境设置
如果您想运行源代码或进行二次开发，请按照以下步骤操作：

### 2.1 安装 Python
建议安装 **Python 3.12**。
[下载地址](https://www.python.org/downloads/windows/)

### 2.2 安装依赖
在项目根目录下运行：
```bash
pip install PyQt5 opencv-python numpy
```

### 2.3 运行项目
使用以下命令启动统一入口：
```bash
python unified_launcher.py
```

## 3. 核心功能说明
- **USB 投屏**: 需要开启手机的 "USB 调试"。某些设备（如小米）还需要开启 "USB 调试（安全设置）" 才能进行触摸控制。
- **WiFi 投屏**: 确保手机和电脑在同一局域网内。
- **自动构建**: 运行 `python build_enhanced.py` 即可一键生成 EXE。

## 4. 常见问题排查 (Troubleshooting)

| 问题 | 原因 | 解决方法 |
|------|------|----------|
| 找不到设备 | USB 连接不良或驱动未装 | 重新插拔，检查设备管理器中是否有 ADB 接口 |
| 无法控制屏幕 | 权限不足 | 在开发者选项中开启“模拟点击”或“安全设置”权限 |
| 画面黑屏 | 设备锁屏或协议冲突 | 解锁手机，或重启应用 |
| 启动闪退 | 环境缺失或编码错误 | 运行 `python project_validator.py` 检查并查看 `scrcpy_enhanced.log` |

## 5. 项目结构
- `adb.exe`: Android 调试桥
- `scrcpy-server.jar`: 服务端程序
- `scrcpy_client_enhanced.py`: 核心客户端逻辑
- `video_decoder_enhanced.py`: 强化版视频解码器
- `control_enhanced.py`: 触摸与事件映射
- `unified_launcher.py`: 统一启动器（GUI）
