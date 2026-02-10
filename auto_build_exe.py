#!/usr/bin/env python3
"""
一键打包脚本 - 自动生成 EXE 文件
支持 scrcpy_client 和 wifi_mirroring
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path
import json

class PyInstallerBuilder:
    def __init__(self, script_name, exe_name, output_dir="dist"):
        self.script_name = script_name
        self.exe_name = exe_name
        self.output_dir = output_dir
        self.project_root = Path.cwd()
        
    def check_dependencies(self):
        """检查必要的依赖"""
        print(f"\n🔍 检查依赖...")
        
        required_modules = ['PyQt5', 'pyinstaller']
        missing = []
        
        for module in required_modules:
            try:
                __import__(module.lower().replace('-', '_'))
                print(f"  ✓ {module}")
            except ImportError:
                missing.append(module)
                print(f"  ✗ {module}")
        
        if missing:
            print(f"\n❌ 缺少以下模块: {', '.join(missing)}")
            print(f"请运行: pip install {' '.join(missing)}")
            return False
        
        return True
    
    def check_script(self):
        """检查源文件是否存在"""
        if not Path(self.script_name).exists():
            print(f"❌ 源文件不存在: {self.script_name}")
            return False
        print(f"✓ 源文件存在: {self.script_name}")
        return True
    
    def build(self):
        """构建 EXE"""
        print(f"\n🔨 开始打包: {self.script_name}")
        print(f"   目标 EXE: {self.exe_name}")
        
        # PyInstaller 命令
        cmd = [
            sys.executable,
            "-m", "PyInstaller",
            "--onefile",
            "--windowed",
            "--name", self.exe_name,
            "--distpath", self.output_dir,
            "--specpath", "build_specs",
            "--buildpath", "build_temp",
            "--noconfirm",
            "--log-level", "INFO"
        ]
        
        # 添加附加数据
        if Path("scrcpy-server.jar").exists():
            cmd.extend(["--add-data", "scrcpy-server.jar:."])
        
        if Path("adb.exe").exists():
            cmd.extend(["--add-data", "adb.exe:."])
        
        # 隐藏导入
        cmd.extend([
            "--hidden-import=PyQt5.QtCore",
            "--hidden-import=PyQt5.QtGui",
            "--hidden-import=PyQt5.QtWidgets"
        ])
        
        # 添加源文件
        cmd.append(self.script_name)
        
        # 执行打包
        print(f"📦 执行命令: {' '.join(cmd[:5])}...")
        
        try:
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            
            if result.returncode == 0:
                exe_path = Path(self.output_dir) / f"{self.exe_name}.exe"
                if exe_path.exists():
                    size_mb = exe_path.stat().st_size / (1024 * 1024)
                    print(f"✅ 打包成功！")
                    print(f"   文件: {exe_path}")
                    print(f"   大小: {size_mb:.1f} MB")
                    return True
            
            print(f"❌ 打包失败!")
            if result.stderr:
                print(f"错误信息:\n{result.stderr}")
            return False
            
        except Exception as e:
            print(f"❌ 执行出错: {e}")
            return False
    
    def cleanup(self):
        """清理临时文件"""
        print(f"\n🧹 清理临时文件...")
        
        dirs_to_clean = ["build_temp", "build_specs"]
        for dir_name in dirs_to_clean:
            if Path(dir_name).exists():
                try:
                    shutil.rmtree(dir_name)
                    print(f"  ✓ 删除 {dir_name}")
                except:
                    pass


def print_header():
    """打印标题"""
    print("""
    ╔════════════════════════════════════════════╗
    ║        PyInstaller 一键打包工具            ║
    ║     Scrcpy Client & WiFi Mirroring       ║
    ╚════════════════════════════════════════════╝
    """)


def main():
    """主程序"""
    print_header()
    
    # 构建列表
    builds = [
        {
            'name': 'Scrcpy Client (稳定版 v2)',
            'script': 'scrcpy_client_stable_v2.py',
            'exe': 'ScrcpyClient_Stable_v2'
        },
        {
            'name': 'WiFi 投屏 (改进版 v2)',
            'script': 'wifi_mirroring_v2.py',
            'exe': 'WiFiMirroring_v2'
        }
    ]
    
    # 显示选项
    print("📋 可用的构建选项:\n")
    for i, build in enumerate(builds, 1):
        print(f"  {i}. {build['name']}")
    print(f"  0. 全部构建")
    print(f"  q. 退出")
    
    choice = input("\n请选择 (0/1/2/q): ").strip().lower()
    
    selected = []
    
    if choice == 'q':
        print("退出")
        return
    elif choice == '0':
        selected = builds
    elif choice in ['1', '2']:
        idx = int(choice) - 1
        if 0 <= idx < len(builds):
            selected = [builds[idx]]
        else:
            print("❌ 选择无效")
            return
    else:
        print("❌ 选择无效")
        return
    
    # 执行构建
    os.makedirs("dist", exist_ok=True)
    
    results = []
    for build in selected:
        print(f"\n{'='*50}")
        builder = PyInstallerBuilder(build['script'], build['exe'])
        
        # 检查
        if not builder.check_dependencies():
            results.append((build['name'], False, "缺少依赖"))
            continue
        
        if not builder.check_script():
            results.append((build['name'], False, "源文件不存在"))
            continue
        
        # 构建
        if builder.build():
            results.append((build['name'], True, None))
            builder.cleanup()
        else:
            results.append((build['name'], False, "构建失败"))
    
    # 显示结果
    print(f"\n{'='*50}")
    print("📊 构建结果:\n")
    
    for name, success, error in results:
        if success:
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name}")
            if error:
                print(f"     ({error})")
    
    print(f"\n✨ 所有 EXE 文件位于: {Path('dist').absolute()}")
    print(f"\n🚀 使用方法:")
    print(f"   双击 EXE 文件即可运行")
    print(f"   无需安装 Python 和依赖")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏸️  用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
