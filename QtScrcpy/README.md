# QtScrcpy

<p align="center">
  <img src="resources/icons/logo.png" width="128" height="128" alt="QtScrcpy Logo">
</p>

<p align="center">
  <strong>一款开源的安卓投屏控制软件</strong>
</p>

<p align="center">
  <a href="#功能特性">功能特性</a> •
  <a href="#安装">安装</a> •
  <a href="#使用方法">使用方法</a> •
  <a href="#快捷键">快捷键</a> •
  <a href="#编译">编译</a>
</p>

---

## 功能特性

- 🖥️ **实时屏幕镜像** - 高帧率、低延迟的屏幕投射
- 🖱️ **鼠标键盘控制** - 完整的输入控制支持
- 📶 **无线连接** - 自动扫描局域网内的安卓设备
- 🔲 **全屏模式** - 沉浸式全屏体验
- 📲 **下拉通知栏** - 支持手机系统快捷操作
- 📦 **APK安装** - 拖放APK文件即可安装
- 📁 **文件传输** - 拖放文件传输到手机
- 📋 **剪贴板同步** - 双向剪贴板共享
- 🔇 **静音控制** - 投屏时自动静音手机
- ⌨️ **输入法支持** - 使用电脑输入法在手机打字
- ⚡ **快捷操作** - 丰富的快捷键支持

## 系统要求

### 电脑端
- Windows 10/11 (64位)
- 已安装 Visual C++ Redistributable 2019+

### 安卓端
- Android 5.0 (API 21) 或更高版本
- 已启用 USB 调试
- 无线连接需要 Android 11+ 并启用无线调试

## 安装

### 方式一：下载预编译版本

从 [Releases](https://github.com/user/QtScrcpy/releases) 下载最新版本。

### 方式二：从源码编译

参见下方 [编译](#编译) 章节。

## 使用方法

### USB 连接

1. 在手机上启用 **USB 调试**（设置 → 开发者选项）
2. 使用 USB 数据线连接手机和电脑
3. 启动 QtScrcpy，设备会自动显示在列表中
4. 点击设备名称开始投屏

### 无线连接

1. 确保手机和电脑在同一 WiFi 网络
2. 在手机上启用 **无线调试**（Android 11+）或先通过 USB 执行 `adb tcpip 5555`
3. 启动 QtScrcpy，点击 **扫描设备**
4. 等待扫描完成，选择设备连接

### 安装 APK

只需将 `.apk` 文件拖放到投屏窗口即可安装。

### 传输文件

将任意文件拖放到投屏窗口，文件将传输到手机的 `/sdcard/Download/` 目录。

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+H` | Home 键 |
| `Ctrl+B` 或 `Backspace` | 返回键 |
| `Ctrl+S` | 多任务切换 |
| `Ctrl+M` | 菜单键 |
| `Ctrl+P` | 电源键 |
| `Ctrl+↑` | 音量增加 |
| `Ctrl+↓` | 音量减少 |
| `Ctrl+N` | 下拉通知栏 |
| `Ctrl+Shift+N` | 展开快捷设置 |
| `F11` 或双击 | 切换全屏 |
| `Ctrl+G` | 调整窗口大小为1:1 |
| `Ctrl+X` | 调整窗口适应屏幕 |
| `Esc` | 退出全屏 |

## 编译

### 依赖项

- CMake 3.16+
- Qt 6.2+
- FFmpeg 6.0+
- C++17 编译器

### Windows 编译步骤

```bash
# 克隆仓库
git clone https://github.com/user/QtScrcpy.git
cd QtScrcpy

# 下载依赖（FFmpeg、ADB）
# 将 FFmpeg 解压到 third_party/ffmpeg
# 将 platform-tools 解压到 third_party/adb

# 创建构建目录
mkdir build && cd build

# 配置（请根据实际路径修改 Qt 路径）
cmake -G "Visual Studio 17 2022" -A x64 ^
    -DCMAKE_PREFIX_PATH="C:/Qt/6.6.0/msvc2019_64" ..

# 编译
cmake --build . --config Release
```

## 技术栈

- **Qt 6** - GUI 框架
- **FFmpeg** - 视频解码
- **ADB** - Android 调试桥
- **scrcpy-server** - 安卓端服务

## 致谢

本项目参考了以下开源项目：

- [scrcpy](https://github.com/Genymobile/scrcpy) - Android 投屏工具的先驱
- [QtScrcpy](https://github.com/barry-ran/QtScrcpy) - Qt 实现参考

## 许可证

本项目采用 [Apache License 2.0](LICENSE) 许可证。

---

<p align="center">
  Made with ❤️ using Qt and C++
</p>
