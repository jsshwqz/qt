# AndroidMirror 云端打包项目

这是一个完整的打包项目，可以在云端环境（如 GitHub Codespaces、Gitpod、或任何有完整Python环境的Windows机器）生成Windows EXE。

## 快速开始（在云端环境）

### 方式1：使用 GitHub Codespaces（推荐）

1. 访问: https://github.com/new 创建新仓库
2. 上传本项目所有文件
3. 点击 "Code" → "Codespaces" → "Create codespace"
4. 在Codespaces终端中执行:
   ```bash
   cd AndroidMirror
   pip install pyinstaller
   python build_exe.py
   ```
5. 完成后从 Codespaces 下载 dist 目录

### 方式2：使用本地Windows虚拟机

1. 安装 Windows 10/11 虚拟机
2. 安装 Python 3.9+ (64位)
3. 执行:
   ```powershell
   cd E:\Program Files\qt\AndroidMirror
   pip install pyinstaller
   python build_exe.py
   ```

## 打包产物

打包成功后，EXE文件位于:
- 单文件: `dist/AndroidMirror.exe` (约 150MB)
- 便携版: `dist/AndroidMirror/` 目录

## 包含的功能

- ✅ USB/无线 Android 设备投屏
- ✅ 实时屏幕镜像
- ✅ 鼠标键盘控制
- ✅ 文件传输
- ✅ APK 安装
- ✅ 剪贴板同步

## 系统要求

- Windows 10/11 64位
- 4GB RAM
- 10GB 空闲磁盘空间
- ADB 驱动（可选，用于USB连接）

## 技术架构

- **前端**: Electron + HTML/CSS/JavaScript
- **打包工具**: PyInstaller
- **视频解码**: JMuxer + H.264
- **通信协议**: WebSocket + ADB

## 文件说明

```
AndroidMirror/
├── main.js           # Electron 主进程
├── preload.js        # 预加载脚本（安全API）
├── src/
│   ├── index.html    # 主界面
│   ├── renderer/
│   │   ├── app.js    # 前端逻辑
│   │   └── jmuxer.min.js  # 视频解码库
│   └── styles/
│       └── main.css  # 样式文件
├── resources/
│   ├── adb/          # ADB 工具（需要自备）
│   ├── scrcpy-server # scrcpy 服务端
│   └── icon.ico      # 应用图标
├── build_exe.py      # 打包脚本
├── package.json      # NPM 配置
└── README.md         # 说明文档
```

## 故障排除

### 打包失败: 内存不足
```powershell
# 使用更小的打包选项
pyinstaller --onefile --name AndroidMirror main.js --debug=no
```

### 打包失败: 权限问题
- 以管理员身份运行命令行
- 关闭杀毒软件

### 运行EXE时崩溃
- 安装 VC++ Redistributable
- 以管理员身份运行

## 许可证

MIT License

## 作者

Matrix Agent
