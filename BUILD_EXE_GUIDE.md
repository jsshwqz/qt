# Windows EXE 打包指南

由于当前环境限制（硬盘空间不足），请在有完整环境的Windows机器上执行以下步骤：

## 环境要求
- Windows 10/11 64位
- Python 3.9+ (64位)
- 至少 10GB 空闲硬盘空间
- 网络连接（用于下载依赖）

## 快速打包步骤

### 1. 安装依赖
```powershell
# 安装 Python (从 https://www.python.org/downloads/ 下载)

# 打开 PowerShell 并执行：
pip install pyinstaller pyqt5 qasync pypiwin32
```

### 2. 执行打包
```powershell
# 进入项目目录
cd "E:\Program Files\qt"

# 运行打包脚本
python build_exe.py
```

打包完成后，EXE文件位于：`dist\AndroidMirror\AndroidMirror.exe`

## 手动打包命令

如果自动脚本失败，可以手动执行：

```powershell
cd "E:\Program Files\qt"
pyinstaller --onefile `
    --name "AndroidMirror" `
    --windowed `
    --icon "resources/icon.ico" `
    --add-data "src;src" `
    --add-data "resources;resources" `
    main.py
```

## 打包选项说明

### 选项1：单文件EXE（推荐）
```powershell
pyinstaller --onefile --windowed --name AndroidMirror main.py
```
- 优点：单个EXE文件，易于分发
- 缺点：首次启动较慢（需要解压）

### 选项2：目录分发
```powershell
pyinstaller --windowed --name AndroidMirror main.py
```
- 优点：启动快，可更新部分文件
- 缺点：多个文件，需要整个目录

## 文件说明

打包后的文件结构：
```
dist\
  └─ AndroidMirror/
      ├─ AndroidMirror.exe          # 主程序
      ├─ python39.dll               # Python运行时
      ├─ Qt5Core.dll                # Qt5核心库
      ├─ Qt5Gui.dll                 # Qt5 GUI库
      ├─ Qt5Widgets.dll             # Qt5 widgets库
      ├─ PyQt5/                     # PyQt5插件
      ├─ ssl/                       # SSL证书目录
      └─ adb/                       # ADB工具目录
```

## 运行应用

双击 `dist\AndroidMirror\AndroidMirror.exe` 即可运行。

## ADB要求

应用需要 ADB (Android Debug Bridge) 来连接Android设备。请确保：
1. ADB 在系统 PATH 中，或
2. 将 adb.exe 放在应用目录的 `adb\` 子文件夹中

## 故障排除

### 问题：应用启动后立即崩溃
解决方案：
- 安装 Visual C++ Redistributable
- 以管理员身份运行

### 问题：无法连接设备
解决方案：
- 检查 USB 调试是否在手机上启用
- 检查 ADB 驱动是否正确安装
- 尝试重新插拔 USB 线

### 问题：视频显示黑屏
解决方案：
- 检查设备是否已授权
- 确认 USB 调试模式已启用
- 尝试重启ADB服务

## 支持的功能

- [x] USB 连接 Android 设备
- [x] 实时屏幕镜像
- [x] 鼠标/键盘控制
- [x] 无线投屏（需要先USB连接后开启无线模式）
- [x] 文件传输
- [x] APK 安装
- [x] 剪贴板同步
- [x] 全屏模式

## 已知限制

- 仅支持 Windows 10/11
- 需要 Android 设备开启 USB 调试
- 某些安全软件可能会阻止 ADB 操作

## 版本信息

- 应用版本：1.0.0
- 构建日期：2026-01-31
- Python 要求：3.9+
