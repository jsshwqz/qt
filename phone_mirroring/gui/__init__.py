"""
WiFi投屏GUI模块
"""

# 延迟导入，避免循环依赖
def get_app():
    from .main_window import WiFiMirroringApp
    return WiFiMirroringApp

# 导出
__all__ = ['get_app']
