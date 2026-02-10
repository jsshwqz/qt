#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的异常处理框架

定义项目中使用的所有自定义异常和错误处理工具
"""

import logging
import traceback
from typing import Optional, Type

logger = logging.getLogger(__name__)


class ScrcpyException(Exception):
    """项目基础异常类"""
    
    def __init__(self, message: str, error_code: str = 'UNKNOWN', details: Optional[dict] = None):
        """
        初始化异常
        
        Args:
            message: 错误消息
            error_code: 错误代码
            details: 额外的错误详情字典
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        logger.error(f'ScrcpyException [{error_code}]: {message}')
    
    def __str__(self):
        """返回错误消息字符串"""
        if self.details:
            detail_str = ', '.join(f'{k}={v}' for k, v in self.details.items())
            return f'{self.message} ({detail_str})'
        return self.message
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'details': self.details
        }


class AdbException(ScrcpyException):
    """ADB 相关异常"""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, error_code='ADB_ERROR', details=details)


class DeviceNotFoundException(AdbException):
    """设备未找到异常"""
    
    def __init__(self, device_id: str = 'unknown'):
        super().__init__(
            f'Device not found: {device_id}',
            error_code='DEVICE_NOT_FOUND',
            details={'device_id': device_id}
        )


class DeviceConnectionException(ScrcpyException):
    """设备连接异常"""
    
    def __init__(self, message: str, device_id: Optional[str] = None):
        details = {}
        if device_id:
            details['device_id'] = device_id
        super().__init__(message, error_code='CONNECTION_FAILED', details=details)


class VideoDecodingException(ScrcpyException):
    """视频解码异常"""
    
    def __init__(self, message: str, frame_num: Optional[int] = None):
        details = {}
        if frame_num is not None:
            details['frame_number'] = frame_num
        super().__init__(message, error_code='VIDEO_DECODE_ERROR', details=details)


class PortForwardingException(ScrcpyException):
    """端口转发异常"""
    
    def __init__(self, message: str, port: Optional[int] = None):
        details = {}
        if port is not None:
            details['port'] = port
        super().__init__(message, error_code='PORT_FORWARD_ERROR', details=details)


class TimeoutException(ScrcpyException):
    """超时异常"""
    
    def __init__(self, message: str, timeout_seconds: Optional[float] = None):
        details = {}
        if timeout_seconds is not None:
            details['timeout_seconds'] = timeout_seconds
        super().__init__(message, error_code='TIMEOUT', details=details)


class ConfigurationException(ScrcpyException):
    """配置异常"""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {}
        if config_key:
            details['config_key'] = config_key
        super().__init__(message, error_code='CONFIG_ERROR', details=details)


class ErrorHandler:
    """统一的错误处理工具"""
    
    def __init__(self):
        """初始化错误处理器"""
        self.errors = []
        self.warnings = []
    
    @staticmethod
    def handle_exception(exc: Exception, 
                        context: str = '',
                        reraise: bool = False) -> Optional[str]:
        """
        处理异常
        
        Args:
            exc: 异常对象
            context: 上下文描述
            reraise: 是否重新抛出异常
            
        Returns:
            错误信息字符串（如果 reraise=False）
        """
        error_msg = f'{context}: {str(exc)}' if context else str(exc)
        
        if isinstance(exc, ScrcpyException):
            logger.error(f'ScrcpyException: {exc.to_dict()}')
        else:
            logger.error(f'Exception: {error_msg}')
            logger.debug(traceback.format_exc())
        
        if reraise:
            raise
        return error_msg
    
    def add_error(self, message: str, error_code: str = 'UNKNOWN'):
        """
        添加错误
        
        Args:
            message: 错误消息
            error_code: 错误代码
        """
        error = {
            'message': message,
            'error_code': error_code,
            'timestamp': logging.Formatter().formatTime(logging.LogRecord(
                name='', level=0, pathname='', lineno=0,
                msg='', args=(), exc_info=None
            ))
        }
        self.errors.append(error)
        logger.error(f'[{error_code}] {message}')
    
    def add_warning(self, message: str):
        """
        添加警告
        
        Args:
            message: 警告消息
        """
        self.warnings.append(message)
        logger.warning(message)
    
    def get_errors(self):
        """获取所有错误"""
        return self.errors.copy()
    
    def get_warnings(self):
        """获取所有警告"""
        return self.warnings.copy()
    
    def clear(self):
        """清空所有错误和警告"""
        self.errors.clear()
        self.warnings.clear()
    
    def has_errors(self):
        """检查是否有错误"""
        return len(self.errors) > 0
    
    def has_warnings(self):
        """检查是否有警告"""
        return len(self.warnings) > 0


# 全局错误处理器
global_error_handler = ErrorHandler()


def wrap_exception(func):
    """
    异常包装装饰器
    
    自动捕获和日志记录函数中的异常
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ScrcpyException:
            raise
        except Exception as e:
            logger.error(f'Error in {func.__name__}: {e}')
            logger.debug(traceback.format_exc())
            raise ScrcpyException(
                f'Error in {func.__name__}: {str(e)}',
                error_code='FUNCTION_ERROR',
                details={'function': func.__name__}
            )
    return wrapper
