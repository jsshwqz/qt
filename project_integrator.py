#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目整合脚本
整合 Scrcpy, WiFi Mirroring 和 Phone Mirroring 三个项目
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProjectIntegrator:
    """项目整合器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.integration_report = {
            'timestamp': datetime.now().isoformat(),
            'status': 'success',
            'modules': [],
            'issues': [],
            'warnings': []
        }
    
    def check_project_structure(self):
        """检查项目结构"""
        logger.info("Checking project structure...")
        
        required_files = [
            'scrcpy_client_enhanced.py',
            'adb_manager.py',
            'scrcpy_server.py',
            'video_decoder_enhanced.py',
            'build_enhanced.py'
        ]
        
        optional_files = [
            'wifi_mirroring_final.py',
            'phone_mirroring/app_main.py'
        ]
        
        for file_name in required_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                logger.info(f"✓ {file_name}")
                self.integration_report['modules'].append(file_name)
            else:
                logger.warning(f"✗ {file_name} missing")
                self.integration_report['issues'].append(f"Missing: {file_name}")
        
        for file_name in optional_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                logger.info(f"✓ {file_name}")
            else:
                logger.warning(f"⊘ {file_name} not found (optional)")
                self.integration_report['warnings'].append(f"Missing: {file_name}")
    
    def generate_unified_launcher(self):
        """生成统一启动器"""
        logger.info("Generating unified launcher...")
        
        launcher_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Native Mirroring Pro - Unified Launcher
统一启动器，支持多种投屏方式
"""

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTabWidget
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont

class UnifiedLauncher(QMainWindow):
    """统一启动界面"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Native Mirroring Pro - Launcher')
        self.setGeometry(100, 100, 600, 400)
        self.setup_ui()
    
    def setup_ui(self):
        """设置界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 标题
        title = QLabel('Native Mirroring Pro')
        title_font = QFont('Arial', 20, QFont.Bold)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # 选项
        options_layout = QHBoxLayout()
        
        # Scrcpy 客户端
        btn_scrcpy = QPushButton('USB Mirroring\\n(Scrcpy)')
        btn_scrcpy.setMinimumHeight(80)
        btn_scrcpy.clicked.connect(self.launch_scrcpy)
        options_layout.addWidget(btn_scrcpy)
        
        # WiFi 投屏
        btn_wifi = QPushButton('WiFi Mirroring\\n(Network)')
        btn_wifi.setMinimumHeight(80)
        btn_wifi.clicked.connect(self.launch_wifi)
        options_layout.addWidget(btn_wifi)
        
        # 详细信息
        btn_info = QPushButton('Device Info\\n(ADB)')
        btn_info.setMinimumHeight(80)
        btn_info.clicked.connect(self.show_device_info)
        options_layout.addWidget(btn_info)
        
        layout.addLayout(options_layout)
        
        # 状态栏
        self.status_label = QLabel('Ready')
        layout.addWidget(self.status_label)
    
    def launch_scrcpy(self):
        """启动 Scrcpy"""
        self.status_label.setText('Launching Scrcpy Client...')
        try:
            from scrcpy_client_enhanced import ScrcpyClientGUI
            self.scrcpy_window = ScrcpyClientGUI()
            self.scrcpy_window.show()
            self.hide()
        except Exception as e:
            self.status_label.setText(f'Error: {str(e)}')
    
    def launch_wifi(self):
        """启动 WiFi 投屏"""
        self.status_label.setText('Launching WiFi Mirroring...')
        try:
            from wifi_mirroring_final import WiFiMirroringApp
            self.wifi_window = WiFiMirroringApp()
            self.wifi_window.show()
            self.hide()
        except Exception as e:
            self.status_label.setText(f'Error: {str(e)}')
    
    def show_device_info(self):
        """显示设备信息"""
        self.status_label.setText('Loading device information...')
        try:
            from adb_manager import AdbServerManager
            adb = AdbServerManager()
            adb.start_server()
            devices = adb.list_devices()
            self.status_label.setText(f'Found {len(devices)} device(s)')
        except Exception as e:
            self.status_label.setText(f'Error: {str(e)}')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    launcher = UnifiedLauncher()
    launcher.show()
    sys.exit(app.exec_())
'''
        
        launcher_file = self.project_root / 'unified_launcher.py'
        with open(launcher_file, 'w', encoding='utf-8') as f:
            f.write(launcher_code)
        
        logger.info(f"✓ Unified launcher created: {launcher_file}")
        self.integration_report['modules'].append('unified_launcher.py')
    
    def check_dependencies(self):
        """检查依赖"""
        logger.info("Checking dependencies...")
        
        dependencies = {
            'PyQt5': 'GUI framework',
            'cv2': 'Video processing',
            'numpy': 'Array processing',
            'adb': 'Android Debug Bridge'
        }
        
        for module, description in dependencies.items():
            try:
                __import__(module)
                logger.info(f"✓ {module}: {description}")
            except ImportError:
                msg = f"Missing: {module} ({description})"
                logger.warning(msg)
                self.integration_report['warnings'].append(msg)
    
    def generate_config(self):
        """生成配置文件"""
        logger.info("Generating configuration...")
        
        config = {
            'version': '1.0.0',
            'timestamp': datetime.now().isoformat(),
            'modules': {
                'scrcpy': {
                    'name': 'USB Mirroring',
                    'file': 'scrcpy_client_enhanced.py',
                    'enabled': True
                },
                'wifi_mirroring': {
                    'name': 'WiFi Mirroring',
                    'file': 'wifi_mirroring_final.py',
                    'enabled': False
                },
                'phone_mirroring': {
                    'name': 'Phone Mirroring',
                    'file': 'phone_mirroring/app_main.py',
                    'enabled': False
                }
            },
            'settings': {
                'default_resolution': '720x1280',
                'frame_rate': 30,
                'bitrate': 8000000
            }
        }
        
        config_file = self.project_root / 'project_config.json'
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Configuration saved: {config_file}")
    
    def generate_report(self):
        """生成集成报告"""
        logger.info("Generating integration report...")
        
        report_file = self.project_root / 'integration_report.json'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.integration_report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Report saved: {report_file}")
        
        # 打印摘要
        print()
        print("=" * 60)
        print("Integration Report Summary")
        print("=" * 60)
        print(f"Status: {self.integration_report['status']}")
        print(f"Modules: {len(self.integration_report['modules'])}")
        
        if self.integration_report['warnings']:
            print(f"Warnings: {len(self.integration_report['warnings'])}")
            for warning in self.integration_report['warnings']:
                print(f"  - {warning}")
        
        if self.integration_report['issues']:
            print(f"Issues: {len(self.integration_report['issues'])}")
            for issue in self.integration_report['issues']:
                print(f"  - {issue}")
            self.integration_report['status'] = 'failed'
        
        print("=" * 60)
        print()
    
    def run(self):
        """运行整合"""
        logger.info("Starting project integration...")
        print()
        
        self.check_project_structure()
        print()
        
        self.check_dependencies()
        print()
        
        self.generate_unified_launcher()
        self.generate_config()
        self.generate_report()
        
        logger.info("Integration completed")


def main():
    """主函数"""
    try:
        integrator = ProjectIntegrator()
        integrator.run()
        return 0
    except Exception as e:
        logger.error(f"Integration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
