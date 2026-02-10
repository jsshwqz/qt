# WiFi 手机投屏 - 打包为 EXE 完整指南

## 环境准备

确保已安装：
- Python 3.8 或更高版本
- pip（Python包管理器）

验证安装：
```bash
python --version
pip --version
```

## 方法1：使用批处理脚本（最简单）

1. 双击运行 `BUILD_EXE.bat`
2. 等待 3-5 分钟
3. 生成的文件会出现在 `dist\WiFi_Mirroring.exe`

## 方法2：手动命令行打包

### 步骤1：打开命令提示符

在项目文件夹地址栏输入 `cmd` 并按回车

### 步骤2：安装依赖

```bash
pip install pyinstaller pyqt5 qasync
```

### 步骤3：执行打包

```bash
python -m PyInstaller --onefile --windowed --name "WiFi_Mirroring" wifi_mirroring_app.py
```

参数说明：
- `--onefile`：打包为单个EXE文件
- `--windowed`：GUI应用，不显示控制台
- `--name`：输出文件名

### 步骤4：等待完成

打包过程约需 3-5 分钟，完成后会显示：
```
Building EXE completed successfully
```

### 步骤5：找到生成的文件

生成的文件位置：
- `dist\WiFi_Mirroring.exe` （主文件）
- 可以复制到桌面或其他位置使用

## 方法3：使用详细配置打包

如果需要更多控制，使用spec文件：

```bash
python -m PyInstaller wifi_mirroring.spec
```

## 减小文件体积

生成的EXE约 30-50MB，可以通过以下方式减小：

### 使用UPX压缩（自动）
PyInstaller会自动使用UPX（如果已安装）

### 排除不需要的模块
```bash
python -m PyInstaller --onefile --windowed \
    --exclude-module matplotlib \
    --exclude-module numpy \
    --exclude-module pandas \
    --exclude-module scipy \
    --exclude-module PIL \
    --name "WiFi_Mirroring" \
    wifi_mirroring_app.py
```

### 使用虚拟环境打包（推荐）

创建干净的虚拟环境：
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate

# 安装最小依赖
pip install pyinstaller pyqt5 qasync

# 打包
python -m PyInstaller --onefile --windowed --name "WiFi_Mirroring" wifi_mirroring_app.py

# 退出虚拟环境
deactivate
```

## 常见问题

### 问题1：提示 "python 不是内部或外部命令"

**解决：** 将Python添加到系统PATH
1. 右键"此电脑" -> 属性 -> 高级系统设置
2. 环境变量 -> 系统变量 -> Path
3. 添加 Python 安装路径（如 `C:\Users\Administrator\AppData\Local\Programs\Python\Python313`）
4. 添加 Python Scripts 路径（如 `C:\Users\Administrator\AppData\Local\Programs\Python\Python313\Scripts`）

### 问题2：打包失败，提示缺少模块

**解决：** 添加 hidden-import
```bash
python -m PyInstaller --onefile --windowed \
    --hidden-import PyQt5.QtWidgets \
    --hidden-import PyQt5.QtCore \
    --hidden-import PyQt5.QtGui \
    --hidden-import qasync \
    --name "WiFi_Mirroring" \
    wifi_mirroring_app.py
```

### 问题3：生成的EXE文件太大

**解决：** 
1. 使用虚拟环境打包（只安装必要依赖）
2. 排除不需要的模块（见上文）
3. 安装UPX压缩工具

### 问题4：运行时提示缺少DLL

**解决：** 安装 Visual C++ Redistributable
- 下载地址：https://aka.ms/vs/17/release/vc_redist.x64.exe
- 下载并安装 vc_redist.x64.exe

### 问题5：杀毒软件报毒

**解决：** 
1. PyInstaller打包的程序有时会被误报
2. 将文件添加到杀毒软件白名单
3. 或购买代码签名证书进行签名

## 测试打包结果

打包完成后，测试步骤：

1. **复制到干净环境**
   - 将 `dist\WiFi_Mirroring.exe` 复制到新文件夹
   - 确保该文件夹没有Python或其他依赖

2. **双击运行**
   - 应该能正常启动GUI界面
   - 不提示缺少DLL或模块

3. **测试功能**
   - 点击"启动服务器"
   - 查看是否正常显示RTSP地址
   - 用手机VLC测试连接

## 分发应用

打包成功的 `WiFi_Mirroring.exe` 可以：
- 复制到任何Windows电脑直接运行
- 不需要安装Python
- 不需要安装依赖
- 支持 Windows 10/11

## 文件清单

打包完成后，项目目录结构：
```
E:\Program Files\qt\
├── wifi_mirroring_app.py          # 源代码
├── BUILD_EXE.bat                   # 打包脚本（已修复）
├── dist/
│   └── WiFi_Mirroring.exe          # 生成的可执行文件 ⭐
├── build/                          # 构建临时文件（可删除）
├── wifi_mirroring.spec             # 配置文件
└── PACKAGING_README.md             # 本文件
```

## 下一步

1. 在资源管理器中进入 `E:\Program Files\qt`
2. 双击 `BUILD_EXE.bat` 或手动执行打包命令
3. 等待打包完成
4. 在 `dist\WiFi_Mirroring.exe` 找到生成的文件
5. 双击测试运行

祝你打包成功！
