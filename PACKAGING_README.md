# WiFi手机投屏GUI应用 - 打包说明

## 打包为 EXE 可执行文件

### 方法一：使用简单打包脚本（推荐）

双击运行 `build_simple.bat`：

```bash
build_simple.bat
```

这会生成一个单独的 EXE 文件在 `dist\WiFi手机投屏.exe`

### 方法二：使用完整打包脚本

双击运行 `build_exe.bat`：

```bash
build_exe.bat
```

这会使用 `wifi_mirroring.spec` 配置文件进行打包。

### 方法三：手动打包

打开命令提示符，执行：

```bash
# 安装 PyInstaller
pip install pyinstaller

# 打包为单个 EXE
pyinstaller --onefile --windowed --name "WiFi手机投屏" wifi_mirroring_app.py

# 或简写
pyinstaller -F -w -n "WiFi手机投屏" wifi_mirroring_app.py
```

参数说明：
- `--onefile` / `-F`: 打包为单个 EXE 文件
- `--windowed` / `-w`: GUI 模式，不显示控制台窗口
- `--name` / `-n`: 指定输出文件名
- `--icon`: 指定图标文件（可选）

## 减小文件体积

生成的 EXE 文件可能比较大（50-100MB），可以通过以下方式减小：

1. **使用 UPX 压缩**（自动）
   PyInstaller 会自动使用 UPX 压缩（如果已安装）

2. **排除不需要的模块**
   在 spec 文件中添加 excludes 列表

3. **使用虚拟环境**
   在干净的虚拟环境中打包，避免打包不必要的依赖

   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install PyQt5 qasync pyinstaller
   pyinstaller -F -w -n "WiFi手机投屏" wifi_mirroring_app.py
   ```

## 打包后的文件

打包完成后，你会得到：

```
dist/
└── WiFi手机投屏.exe     # 可执行文件（约 30-50MB）

build/                    # 构建临时文件（可删除）
└── ...
```

## 分发应用

将 `dist\WiFi手机投屏.exe` 复制到任意 Windows 电脑即可直接运行，无需安装 Python 或任何依赖。

## 注意事项

1. **杀毒软件误报**：
   某些杀毒软件可能会误报 PyInstaller 打包的程序，这是正常现象。
   - 添加到信任列表
   - 或购买代码签名证书进行签名

2. **Windows 版本**：
   打包的 EXE 只能在相同或更高版本的 Windows 上运行。
   - 在 Windows 10 上打包，可以在 Win10/Win11 运行
   - 建议在最老的目标系统上打包

3. **依赖问题**：
   如果运行时提示缺少 DLL，可以安装 Visual C++ Redistributable：
   https://aka.ms/vs/17/release/vc_redist.x64.exe

## 高级选项

### 添加版本信息

创建 `file_version_info.txt`，然后在打包时添加：

```bash
pyinstaller -F -w --version-file=file_version_info.txt wifi_mirroring_app.py
```

### 添加自定义图标

准备一个 .ico 图标文件：

```bash
pyinstaller -F -w --icon=app.ico wifi_mirroring_app.py
```

### 隐藏导入模块

如果运行时提示 ImportError，添加 hidden-import：

```bash
pyinstaller -F -w --hidden-import=module_name wifi_mirroring_app.py
```

## 测试打包结果

打包完成后，在干净的环境中测试：

1. 复制 `dist\WiFi手机投屏.exe` 到新文件夹
2. 双击运行，检查是否正常启动
3. 测试所有功能按钮
4. 检查日志输出

## 故障排除

### 打包失败

1. 检查 Python 环境：
   ```bash
   python --version
   pip --version
   ```

2. 重新安装 PyInstaller：
   ```bash
   pip uninstall pyinstaller
   pip install pyinstaller
   ```

3. 清理缓存：
   ```bash
   rmdir /s /q build
   rmdir /s /q dist
   del *.spec
   ```

### 运行时错误

1. **缺少 DLL**：安装 Visual C++ Redistributable
2. **PyQt5 错误**：确保 PyQt5 正确安装
3. **权限问题**：以管理员身份运行

## 文件说明

- `build_simple.bat` - 简单打包脚本（推荐）
- `build_exe.bat` - 完整打包脚本
- `wifi_mirroring.spec` - PyInstaller 配置文件
- `file_version_info.txt` - 版本信息文件
- `requirements_gui.txt` - GUI 依赖列表
