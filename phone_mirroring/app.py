#!/usr/bin/env python3
"""
WiFi手机投屏应用启动入口
"""

import sys
import asyncio
import logging
from PyQt5.QtWidgets import QApplication
import qasync

from phone_mirroring.gui import get_app

def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def main():
    """主函数"""
    setup_logging()
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setApplicationName("WiFi投屏")
    
    # 集成asyncio事件循环
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # 创建主窗口
    from phone_mirroring.gui import get_app
    window = get_app()()
    window.show()
    
    # 运行事件循环
    with loop:
        sys.exit(loop.run_forever())

if __name__ == "__main__":
    main()