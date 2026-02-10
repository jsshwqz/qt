#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的日志管理系统

提供灵活的日志记录、轮转和监控功能
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class LogManager:
    """日志管理器"""
    
    # 日志级别
    LEVEL_DEBUG = logging.DEBUG
    LEVEL_INFO = logging.INFO
    LEVEL_WARNING = logging.WARNING
    LEVEL_ERROR = logging.ERROR
    LEVEL_CRITICAL = logging.CRITICAL
    
    def __init__(self, 
                 log_dir: str = '.',
                 log_file: str = 'app.log',
                 log_level: int = logging.INFO,
                 max_bytes: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5):
        """
        初始化日志管理器
        
        Args:
            log_dir: 日志目录
            log_file: 日志文件名
            log_level: 日志级别
            max_bytes: 日志文件最大大小（字节）
            backup_count: 备份日志文件数量
        """
        self.log_dir = Path(log_dir)
        self.log_file = log_file
        self.log_level = log_level
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        
        # 创建日志目录
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = None
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志系统"""
        self.logger = logging.getLogger('scrcpy')
        self.logger.setLevel(self.log_level)
        
        # 清空已有的处理器
        self.logger.handlers.clear()
        
        # 日志格式
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 文件处理器（带轮转）
        log_path = self.log_dir / self.log_file
        file_handler = logging.handlers.RotatingFileHandler(
            str(log_path),
            maxBytes=self.max_bytes,
            backupCount=self.backup_count
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f'Logging initialized: {log_path}')
    
    def set_level(self, level: int):
        """
        设置日志级别
        
        Args:
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.log_level = level
        if self.logger:
            self.logger.setLevel(level)
            for handler in self.logger.handlers:
                handler.setLevel(level)
            self.logger.info(f'Log level changed to {logging.getLevelName(level)}')
    
    def get_logger(self) -> logging.Logger:
        """获取日志记录器"""
        return self.logger
    
    def debug(self, message: str, *args, **kwargs):
        """记录调试信息"""
        if self.logger:
            self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """记录信息"""
        if self.logger:
            self.logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """记录警告"""
        if self.logger:
            self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """记录错误"""
        if self.logger:
            self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """记录严重错误"""
        if self.logger:
            self.logger.critical(message, *args, **kwargs)
    
    def get_log_file_path(self) -> Path:
        """获取日志文件路径"""
        return self.log_dir / self.log_file
    
    def get_log_file_size(self) -> int:
        """获取日志文件大小（字节）"""
        log_file = self.get_log_file_path()
        if log_file.exists():
            return log_file.stat().st_size
        return 0
    
    def get_log_file_content(self, lines: Optional[int] = None) -> str:
        """
        获取日志文件内容
        
        Args:
            lines: 返回最后 N 行（None 表示全部）
            
        Returns:
            日志内容字符串
        """
        log_file = self.get_log_file_path()
        if not log_file.exists():
            return ''
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                if lines is not None:
                    lines_list = content.split('\n')
                    content = '\n'.join(lines_list[-lines:])
                
                return content
        except Exception as e:
            return f'Failed to read log file: {e}'
    
    def clear_log_file(self):
        """清空日志文件"""
        log_file = self.get_log_file_path()
        if log_file.exists():
            try:
                log_file.unlink()
                self.logger.info('Log file cleared')
            except Exception as e:
                self.logger.error(f'Failed to clear log file: {e}')
    
    def rotate_log(self):
        """手动轮转日志文件"""
        if self.logger:
            for handler in self.logger.handlers:
                if isinstance(handler, logging.handlers.RotatingFileHandler):
                    handler.doRollover()
            self.logger.info('Log file rotated')


# 全局日志管理器实例
_global_log_manager: Optional[LogManager] = None


def get_log_manager(
    log_dir: str = '.',
    log_file: str = 'scrcpy_enhanced.log',
    log_level: int = logging.INFO
) -> LogManager:
    """
    获取全局日志管理器（单例模式）
    
    Args:
        log_dir: 日志目录
        log_file: 日志文件名
        log_level: 日志级别
        
    Returns:
        日志管理器实例
    """
    global _global_log_manager
    
    if _global_log_manager is None:
        _global_log_manager = LogManager(log_dir, log_file, log_level)
    
    return _global_log_manager


def get_logger() -> logging.Logger:
    """获取应用日志记录器"""
    manager = get_log_manager()
    return manager.get_logger()
