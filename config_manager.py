#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目配置管理系统

提供灵活的配置加载、验证和管理功能
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        'device': {
            'auto_detect': True,
            'connection_timeout': 10,
            'reconnect_interval': 2,
            'max_reconnect_attempts': 5,
        },
        'video': {
            'bitrate': 8000000,
            'fps': 30,
            'resolution': '1080x1920',
            'codec': 'h264',
        },
        'network': {
            'local_port': 27183,
            'remote_port': 27183,
            'buffer_size': 65536,
            'socket_timeout': 5.0,
        },
        'ui': {
            'window_width': 1200,
            'window_height': 800,
            'fullscreen': False,
            'show_fps': True,
            'theme': 'dark',
        },
        'logging': {
            'level': 'INFO',
            'file': 'scrcpy_enhanced.log',
            'max_size': 10485760,  # 10MB
            'backup_count': 5,
        },
        'performance': {
            'frame_buffer_size': 30,
            'enable_hardware_acceleration': True,
            'thread_pool_size': 4,
        }
    }
    
    def __init__(self, config_file: str = 'config.json'):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = Path(config_file)
        self.config = self.DEFAULT_CONFIG.copy()
        self._deep_copy_config()
        
        # 加载配置文件
        if self.config_file.exists():
            self.load_config()
        else:
            # 创建默认配置文件
            self.save_config()
        
        logger.info(f'ConfigManager initialized with {self.config_file}')
    
    def _deep_copy_config(self):
        """深复制配置"""
        self.config = json.loads(json.dumps(self.DEFAULT_CONFIG))
    
    def load_config(self):
        """
        加载配置文件
        
        Returns:
            bool: 加载成功返回 True
        """
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            
            # 深度合并配置
            self._merge_config(self.config, user_config)
            logger.info(f'Config loaded from {self.config_file}')
            return True
        except json.JSONDecodeError as e:
            logger.error(f'Failed to parse config file: {e}')
            return False
        except Exception as e:
            logger.error(f'Failed to load config: {e}')
            return False
    
    def save_config(self):
        """
        保存配置文件
        
        Returns:
            bool: 保存成功返回 True
        """
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.info(f'Config saved to {self.config_file}')
            return True
        except Exception as e:
            logger.error(f'Failed to save config: {e}')
            return False
    
    @staticmethod
    def _merge_config(target: Dict[str, Any], source: Dict[str, Any]):
        """
        深度合并配置
        
        Args:
            target: 目标配置（将被修改）
            source: 源配置
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                ConfigManager._merge_config(target[key], value)
            else:
                target[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号分隔的路径）
        
        Args:
            key: 配置键（如 'device.connection_timeout'）
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            logger.warning(f'Config key not found: {key}, using default: {default}')
            return default
    
    def set(self, key: str, value: Any):
        """
        设置配置值（支持点号分隔的路径）
        
        Args:
            key: 配置键（如 'device.connection_timeout'）
            value: 新值
        """
        keys = key.split('.')
        target = self.config
        
        try:
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target[k]
            target[keys[-1]] = value
            logger.info(f'Config set: {key} = {value}')
        except (KeyError, TypeError) as e:
            logger.error(f'Failed to set config {key}: {e}')
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取配置段
        
        Args:
            section: 段名称（如 'device'）
            
        Returns:
            配置段字典
        """
        if section in self.config:
            return self.config[section].copy()
        logger.warning(f'Config section not found: {section}')
        return {}
    
    def reset_to_default(self):
        """重置为默认配置"""
        self._deep_copy_config()
        logger.info('Config reset to default')
    
    def validate(self) -> bool:
        """
        验证配置
        
        Returns:
            bool: 配置有效返回 True
        """
        try:
            # 检查必要的键
            required_sections = ['device', 'video', 'network', 'ui', 'logging']
            for section in required_sections:
                if section not in self.config:
                    logger.error(f'Missing required config section: {section}')
                    return False
            
            # 验证具体值
            if self.get('network.socket_timeout', 5.0) <= 0:
                logger.error('Invalid socket_timeout')
                return False
            
            logger.info('Config validation passed')
            return True
        except Exception as e:
            logger.error(f'Config validation failed: {e}')
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """获取完整配置字典"""
        return self.config.copy()
    
    def __repr__(self):
        """返回配置的字符串表示"""
        return json.dumps(self.config, indent=2, ensure_ascii=False)


# 全局配置管理器实例
_global_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_file: str = 'config.json') -> ConfigManager:
    """
    获取全局配置管理器（单例模式）
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        配置管理器实例
    """
    global _global_config_manager
    
    if _global_config_manager is None:
        _global_config_manager = ConfigManager(config_file)
    
    return _global_config_manager


def get_config(key: str, default: Any = None) -> Any:
    """获取配置值"""
    manager = get_config_manager()
    return manager.get(key, default)


def set_config(key: str, value: Any):
    """设置配置值"""
    manager = get_config_manager()
    manager.set(key, value)
