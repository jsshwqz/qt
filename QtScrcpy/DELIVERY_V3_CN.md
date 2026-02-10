# QtScrcpy 交付说明（v3）

本版本按你的 12 条需求做了交付整理，主入口为 `QtScrcpy`（C++/Qt）。

## 功能核对

1. 实时显示安卓设备屏幕：已支持  
模块：`QtScrcpy/src/stream/videostream.cpp`、`QtScrcpy/src/decoder/decoder.cpp`

2. 安卓设备实时鼠标和键盘控制：已支持  
模块：`QtScrcpy/src/input/inputhandler.cpp`

3. 无线连接（按电脑 Wi-Fi 网段自动搜索手机）：已支持  
模块：`QtScrcpy/src/adb/devicediscovery.cpp`、`QtScrcpy/src/ui/mainwindow.cpp`  
说明：优先扫描 Wi-Fi 接口网段，并自动周期扫描。

4. 全屏显示：已支持  
模块：`QtScrcpy/src/ui/videowidget.cpp`

5. 顶部下拉（通知栏/快捷设置）：已支持  
模块：`QtScrcpy/src/adb/shortcuts.cpp`、`QtScrcpy/src/ui/toolbarwidget.cpp`

6. 安装 APK（拖拽到视频窗口）：已支持  
模块：`QtScrcpy/src/filetransfer/filetransfer.cpp`、`QtScrcpy/src/ui/videowidget.cpp`

7. 传输文件（拖拽到视频窗口）：已支持  
模块：`QtScrcpy/src/filetransfer/filetransfer.cpp`、`QtScrcpy/src/ui/videowidget.cpp`

8. 双向复制粘贴同步：已支持  
模块：`QtScrcpy/src/clipboard/clipboardmanager.cpp`、`QtScrcpy/src/stream/controlstream.cpp`

9. 投屏后手机静音，断开后自动恢复：已支持  
模块：`QtScrcpy/src/adb/volumecontroller.cpp`、`QtScrcpy/src/ui/mainwindow.cpp`

10. 电脑输入法在手机打字：已支持（含 IME 提交文本）  
模块：`QtScrcpy/src/ui/videowidget.cpp`、`QtScrcpy/src/input/inputhandler.cpp`

11. 支持手机快捷操作：已支持  
模块：`QtScrcpy/src/adb/shortcuts.cpp`、`QtScrcpy/src/ui/toolbarwidget.cpp`

12. 交付 EXE + 可开源兼容：已支持  
模块：`.github/workflows/build-windows.yml`、`QtScrcpy/CMakeLists.txt`

## EXE 交付方式

### 方式 A（已有本地可运行版本）

直接使用：  
`QtScrcpy-Release/QtScrcpy-win-x64-v3.3.3/QtScrcpy.exe`

### 方式 B（云端自动构建，避免本地安装大体积 Qt）

1. 推送代码到 GitHub。  
2. 在 Actions 里运行 `Build QtScrcpy Windows EXE`。  
3. 下载 artifact：`QtScrcpy-win-x64.zip`。

## 开源与兼容性

- 主项目许可证：Apache-2.0（见 `QtScrcpy/LICENSE`）。
- Android 投屏核心依赖 `scrcpy-server`，按其上游协议分发。
- ADB、FFmpeg 作为第三方依赖随发布包分发（保留第三方说明文件）。

