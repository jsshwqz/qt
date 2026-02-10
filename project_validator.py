#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目验证和测试脚本
验证所有模块的功能和兼容性
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# 配置日志和输出编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('project_validation.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ProjectValidator:
    """项目验证器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.validation_results = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'tests': []
        }
    
    def log_test(self, name, status, message=''):
        """记录测试结果"""
        self.validation_results['total_tests'] += 1
        
        result = {
            'name': name,
            'status': status,
            'message': message
        }
        
        self.validation_results['tests'].append(result)
        
        if status == 'PASS':
            self.validation_results['passed'] += 1
            logger.info(f"✓ {name}")
        elif status == 'FAIL':
            self.validation_results['failed'] += 1
            logger.error(f"✗ {name}: {message}")
        elif status == 'WARN':
            self.validation_results['warnings'] += 1
            logger.warning(f"⚠ {name}: {message}")
    
    def test_file_structure(self):
        """测试文件结构"""
        logger.info("Testing file structure...")
        
        required_files = [
            'adb_manager.py',
            'scrcpy_server.py',
            'scrcpy_client_enhanced.py',
            'video_decoder_enhanced.py',
            'control_enhanced.py',
            'build_enhanced.py',
            'adb.exe',
            'scrcpy-server.jar'
        ]
        
        for file_name in required_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                self.log_test(f"File: {file_name}", 'PASS')
            else:
                self.log_test(f"File: {file_name}", 'FAIL', 'File not found')
    
    def test_python_syntax(self):
        """测试 Python 语法"""
        logger.info("Testing Python syntax...")
        
        python_files = [
            'adb_manager.py',
            'scrcpy_server.py',
            'scrcpy_client_enhanced.py',
            'video_decoder_enhanced.py',
            'control_enhanced.py',
            'build_enhanced.py',
            'unified_launcher.py'
        ]
        
        for file_name in python_files:
            file_path = self.project_root / file_name
            if not file_path.exists():
                self.log_test(f"Syntax: {file_name}", 'WARN', 'File not found')
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                compile(code, str(file_path), 'exec')
                self.log_test(f"Syntax: {file_name}", 'PASS')
            except SyntaxError as e:
                self.log_test(f"Syntax: {file_name}", 'FAIL', str(e))
    
    def test_imports(self):
        """测试依赖导入"""
        logger.info("Testing imports...")
        
        dependencies = [
            ('PyQt5', 'PyQt5.QtWidgets'),
            ('numpy', 'numpy'),
            ('struct', 'struct'),
            ('socket', 'socket'),
            ('logging', 'logging'),
        ]
        
        for name, module in dependencies:
            try:
                __import__(module)
                self.log_test(f"Import: {name}", 'PASS')
            except ImportError as e:
                self.log_test(f"Import: {name}", 'WARN', str(e))
    
    def test_module_functionality(self):
        """测试模块功能"""
        logger.info("Testing module functionality...")
        
        # 测试 ADB Manager
        try:
            from adb_manager import AdbServerManager
            adb = AdbServerManager()
            
            if hasattr(adb, 'adb_path') and adb.adb_path:
                self.log_test("Module: AdbServerManager", 'PASS')
            else:
                self.log_test("Module: AdbServerManager", 'WARN', 'adb_path not set')
        except Exception as e:
            self.log_test("Module: AdbServerManager", 'FAIL', str(e))
        
        # 测试坐标转换器
        try:
            from control_enhanced import CoordinateTransformer
            transformer = CoordinateTransformer(1080, 1920, 540, 960)
            
            # 测试转换
            device_x, device_y = transformer.window_to_device(270, 480)
            if device_x == 540 and device_y == 960:
                self.log_test("Module: CoordinateTransformer", 'PASS')
            else:
                self.log_test("Module: CoordinateTransformer", 'WARN',
                            f'Unexpected result: ({device_x}, {device_y})')
        except Exception as e:
            self.log_test("Module: CoordinateTransformer", 'FAIL', str(e))
        
        # 测试触摸事件
        try:
            from control_enhanced import TouchEvent
            event = TouchEvent(TouchEvent.ACTION_DOWN, 540, 960)
            data = event.to_bytes()
            
            if len(data) >= 7:
                self.log_test("Module: TouchEvent", 'PASS')
            else:
                self.log_test("Module: TouchEvent", 'FAIL', 'Byte serialization failed')
        except Exception as e:
            self.log_test("Module: TouchEvent", 'FAIL', str(e))
        
        # 测试视频解码器
        try:
            from video_decoder_enhanced import VideoDecoder, ScrcpyVideoDecoder
            decoder = ScrcpyVideoDecoder(720, 1280)
            
            if decoder.width == 720 and decoder.height == 1280:
                self.log_test("Module: VideoDecoder", 'PASS')
            else:
                self.log_test("Module: VideoDecoder", 'FAIL', 'Resolution mismatch')
        except Exception as e:
            self.log_test("Module: VideoDecoder", 'WARN', str(e))
    
    def test_configuration(self):
        """测试配置文件"""
        logger.info("Testing configuration...")
        
        config_file = self.project_root / 'project_config.json'
        if config_file.exists():
            try:
                import json
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                if 'modules' in config and 'version' in config:
                    self.log_test("Config: project_config.json", 'PASS')
                else:
                    self.log_test("Config: project_config.json", 'WARN', 'Missing keys')
            except Exception as e:
                self.log_test("Config: project_config.json", 'FAIL', str(e))
        else:
            self.log_test("Config: project_config.json", 'WARN', 'File not found')
    
    def test_build_system(self):
        """测试构建系统"""
        logger.info("Testing build system...")
        
        build_script = self.project_root / 'build_enhanced.py'
        if build_script.exists():
            self.log_test("Build: Enhanced build script", 'PASS')
        else:
            self.log_test("Build: Enhanced build script", 'FAIL', 'Script not found')
    
    def generate_report(self):
        """生成验证报告"""
        logger.info("Generating validation report...")
        
        # 计算总体状态
        if self.validation_results['failed'] == 0:
            overall_status = 'SUCCESS'
        elif self.validation_results['failed'] < 5:
            overall_status = 'WARN'
        else:
            overall_status = 'FAILED'
        
        self.validation_results['overall_status'] = overall_status
        
        # 保存报告
        import json
        report_file = self.project_root / 'validation_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.validation_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Report saved: {report_file}")
        
        # 打印摘要
        print("\n" + "=" * 60)
        print("Project Validation Summary")
        print("=" * 60)
        print(f"Total Tests: {self.validation_results['total_tests']}")
        print(f"Passed: {self.validation_results['passed']}")
        print(f"Failed: {self.validation_results['failed']}")
        print(f"Warnings: {self.validation_results['warnings']}")
        print(f"Overall Status: {overall_status}")
        print("=" * 60)
    
    def run(self):
        """运行验证"""
        logger.info("Starting project validation...")
        print()
        
        self.test_file_structure()
        print()
        
        self.test_python_syntax()
        print()
        
        self.test_imports()
        print()
        
        self.test_module_functionality()
        print()
        
        self.test_configuration()
        print()
        
        self.test_build_system()
        print()
        
        self.generate_report()
        
        logger.info("Validation completed")


def main():
    """主函数"""
    try:
        validator = ProjectValidator()
        validator.run()
        return 0
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
