"""
错误处理和重连机制
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable, Type, Tuple
from dataclasses import dataclass, field
from enum import Enum
import traceback
import functools

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """错误类别"""
    NETWORK = "network"
    PROTOCOL = "protocol"
    ENCODING = "encoding"
    DECODING = "decoding"
    DEVICE = "device"
    SYSTEM = "system"
    CONFIG = "config"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"

@dataclass
class ErrorInfo:
    """错误信息"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    exception: Optional[Exception] = None
    traceback: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    resolved: bool = False

class ReconnectStrategy(Enum):
    """重连策略"""
    IMMEDIATE = "immediate"
    LINEAR_BACKOFF = "linear_backoff"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    FIXED_INTERVAL = "fixed_interval"
    ADAPTIVE = "adaptive"

@dataclass
class ReconnectConfig:
    """重连配置"""
    strategy: ReconnectStrategy = ReconnectStrategy.EXPONENTIAL_BACKOFF
    max_attempts: int = 5
    base_delay: float = 1.0  # 秒
    max_delay: float = 60.0  # 秒
    backoff_multiplier: float = 2.0
    jitter: bool = True  # 添加随机抖动
    
    # 超时配置
    connect_timeout: float = 10.0
    operation_timeout: float = 30.0
    
    # 重连条件
    retry_on_timeout: bool = True
    retry_on_connection_error: bool = True
    retry_on_network_error: bool = True
    retry_on_device_error: bool = False

class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.log_errors = config.get("log_errors", True)
        self.collect_stats = config.get("collect_stats", True)
        
        # 错误历史
        self.error_history: List[ErrorInfo] = []
        self.max_history = config.get("max_history", 1000)
        
        # 错误统计
        self.error_stats: Dict[str, int] = {}
        self.category_stats: Dict[ErrorCategory, int] = {}
        self.severity_stats: Dict[ErrorSeverity, int] = {}
        
        # 回调函数
        self.error_callbacks: List[Callable[[ErrorInfo], None]] = []
        
        # 错误分类规则
        self.classification_rules = config.get("classification_rules", {})
    
    def handle_error(self, error: Exception, category: ErrorCategory = ErrorCategory.UNKNOWN,
                     severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                     context: Dict[str, Any] = None) -> ErrorInfo:
        """处理错误"""
        if not self.enabled:
            return None
        
        # 创建错误信息
        error_id = f"err_{int(time.time() * 1000)}_{id(error)}"
        error_info = ErrorInfo(
            error_id=error_id,
            category=category,
            severity=severity,
            message=str(error),
            exception=error,
            traceback=traceback.format_exc() if self.log_errors else None,
            context=context or {}
        )
        
        # 分类错误
        error_info.category = self._classify_error(error, category)
        error_info.severity = self._classify_severity(error, severity)
        
        # 更新统计
        self._update_stats(error_info)
        
        # 添加到历史
        self._add_to_history(error_info)
        
        # 记录日志
        if self.log_errors:
            self._log_error(error_info)
        
        # 触发回调
        self._trigger_callbacks(error_info)
        
        return error_info
    
    def _classify_error(self, error: Exception, default_category: ErrorCategory) -> ErrorCategory:
        """错误分类"""
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # 使用分类规则
        if error_type in self.classification_rules:
            return ErrorCategory(self.classification_rules[error_type])
        
        # 基于错误类型的分类
        if isinstance(error, (ConnectionError, ConnectionRefusedError, 
                             ConnectionResetError, ConnectionAbortedError)):
            return ErrorCategory.NETWORK
        elif isinstance(error, (TimeoutError, asyncio.TimeoutError)):
            return ErrorCategory.TIMEOUT
        elif isinstance(error, (OSError, IOError)):
            if "network" in error_message or "socket" in error_message:
                return ErrorCategory.NETWORK
            elif "device" in error_message or "permission" in error_message:
                return ErrorCategory.DEVICE
            else:
                return ErrorCategory.SYSTEM
        elif "protocol" in error_message or "rtsp" in error_message or "rtp" in error_message:
            return ErrorCategory.PROTOCOL
        elif "encode" in error_message or "decode" in error_message:
            if "encode" in error_message:
                return ErrorCategory.ENCODING
            else:
                return ErrorCategory.DECODING
        
        return default_category
    
    def _classify_severity(self, error: Exception, default_severity: ErrorSeverity) -> ErrorSeverity:
        """错误严重程度分类"""
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # 致命错误
        if "critical" in error_message or "fatal" in error_message:
            return ErrorSeverity.CRITICAL
        
        # 高严重程度
        if error_type in ["ConnectionError", "PermissionError", "FileNotFoundError"]:
            return ErrorSeverity.HIGH
        
        # 中等严重程度
        if error_type in ["TimeoutError", "ValueError", "KeyError"]:
            return ErrorSeverity.MEDIUM
        
        return default_severity
    
    def _update_stats(self, error_info: ErrorInfo):
        """更新错误统计"""
        if not self.collect_stats:
            return
        
        # 按错误类型统计
        error_type = type(error_info.exception).__name__ if error_info.exception else "Unknown"
        self.error_stats[error_type] = self.error_stats.get(error_type, 0) + 1
        
        # 按类别统计
        self.category_stats[error_info.category] = self.category_stats.get(error_info.category, 0) + 1
        
        # 按严重程度统计
        self.severity_stats[error_info.severity] = self.severity_stats.get(error_info.severity, 0) + 1
    
    def _add_to_history(self, error_info: ErrorInfo):
        """添加到错误历史"""
        self.error_history.append(error_info)
        
        # 限制历史长度
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
    
    def _log_error(self, error_info: ErrorInfo):
        """记录错误日志"""
        log_level = {
            ErrorSeverity.LOW: logging.DEBUG,
            ErrorSeverity.MEDIUM: logging.INFO,
            ErrorSeverity.HIGH: logging.WARNING,
            ErrorSeverity.CRITICAL: logging.ERROR
        }.get(error_info.severity, logging.ERROR)
        
        logger.log(
            log_level,
            f"[{error_info.error_id}] {error_info.category.value.upper()}: {error_info.message}",
            extra={
                "error_id": error_info.error_id,
                "category": error_info.category.value,
                "severity": error_info.severity.value,
                "context": error_info.context
            }
        )
        
        if error_info.traceback:
            logger.debug(f"Traceback for {error_info.error_id}:\n{error_info.traceback}")
    
    def _trigger_callbacks(self, error_info: ErrorInfo):
        """触发错误回调"""
        for callback in self.error_callbacks:
            try:
                callback(error_info)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
    
    def register_callback(self, callback: Callable[[ErrorInfo], None]):
        """注册错误回调"""
        self.error_callbacks.append(callback)
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        return {
            "total_errors": len(self.error_history),
            "by_type": self.error_stats,
            "by_category": {k.value: v for k, v in self.category_stats.items()},
            "by_severity": {k.value: v for k, v in self.severity_stats.items()},
            "recent_errors": len([e for e in self.error_history 
                                if time.time() - e.timestamp < 3600])  # 最近1小时
        }
    
    def get_recent_errors(self, limit: int = 10) -> List[ErrorInfo]:
        """获取最近的错误"""
        return sorted(self.error_history, 
                     key=lambda e: e.timestamp, 
                     reverse=True)[:limit]

class ReconnectManager:
    """重连管理器"""
    
    def __init__(self, config: ReconnectConfig):
        self.config = config
        self.reconnect_attempts: Dict[str, int] = {}
        self.last_attempt_time: Dict[str, float] = {}
        self.successful_connections: Dict[str, float] = {}
        
        # 回调函数
        self.reconnect_callbacks: List[Callable[[str, int], None]] = []
    
    async def try_reconnect(self, connection_id: str, 
                           connect_func: Callable) -> bool:
        """尝试重连"""
        if connection_id not in self.reconnect_attempts:
            self.reconnect_attempts[connection_id] = 0
        
        attempt = self.reconnect_attempts[connection_id]
        
        # 检查是否超过最大尝试次数
        if attempt >= self.config.max_attempts:
            logger.error(f"Max reconnect attempts reached for {connection_id}")
            return False
        
        # 计算延迟
        delay = self._calculate_delay(connection_id, attempt)
        
        if delay > 0:
            logger.info(f"Waiting {delay:.2f}s before reconnect attempt {attempt + 1} for {connection_id}")
            await asyncio.sleep(delay)
        
        # 尝试连接
        self.reconnect_attempts[connection_id] = attempt + 1
        self.last_attempt_time[connection_id] = time.time()
        
        try:
            success = await asyncio.wait_for(
                connect_func(),
                timeout=self.config.connect_timeout
            )
            
            if success:
                # 连接成功，重置计数器
                self.successful_connections[connection_id] = time.time()
                self.reconnect_attempts[connection_id] = 0
                logger.info(f"Successfully reconnected to {connection_id}")
                
                # 触发回调
                for callback in self.reconnect_callbacks:
                    try:
                        callback(connection_id, attempt + 1)
                    except Exception as e:
                        logger.error(f"Error in reconnect callback: {e}")
                
                return True
            else:
                logger.warning(f"Reconnect attempt {attempt + 1} failed for {connection_id}")
                return False
                
        except asyncio.TimeoutError:
            logger.error(f"Reconnect timeout for {connection_id}")
            return False
        except Exception as e:
            logger.error(f"Reconnect error for {connection_id}: {e}")
            return False
    
    def _calculate_delay(self, connection_id: str, attempt: int) -> float:
        """计算重连延迟"""
        if self.config.strategy == ReconnectStrategy.IMMEDIATE:
            return 0
        elif self.config.strategy == ReconnectStrategy.FIXED_INTERVAL:
            delay = self.config.base_delay
        elif self.config.strategy == ReconnectStrategy.LINEAR_BACKOFF:
            delay = self.config.base_delay * attempt
        elif self.config.strategy == ReconnectStrategy.EXPONENTIAL_BACKOFF:
            delay = self.config.base_delay * (self.config.backoff_multiplier ** attempt)
        else:  # ADAPTIVE
            # 自适应策略：基于成功率调整延迟
            delay = self._calculate_adaptive_delay(connection_id, attempt)
        
        # 应用最大延迟限制
        delay = min(delay, self.config.max_delay)
        
        # 添加抖动
        if self.config.jitter:
            import random
            jitter = random.uniform(0.8, 1.2)
            delay *= jitter
        
        return max(0, delay)
    
    def _calculate_adaptive_delay(self, connection_id: str, attempt: int) -> float:
        """计算自适应延迟"""
        # 基于历史成功率调整延迟
        if connection_id in self.successful_connections:
            # 如果最近成功过，使用较短延迟
            time_since_success = time.time() - self.successful_connections[connection_id]
            if time_since_success < 300:  # 5分钟内成功过
                return self.config.base_delay * 0.5
            elif time_since_success < 1800:  # 30分钟内成功过
                return self.config.base_delay
        
        # 否则使用指数退避
        return self.config.base_delay * (self.config.backoff_multiplier ** attempt)
    
    def reset_reconnect_stats(self, connection_id: str):
        """重置重连统计"""
        if connection_id in self.reconnect_attempts:
            del self.reconnect_attempts[connection_id]
        if connection_id in self.last_attempt_time:
            del self.last_attempt_time[connection_id]
    
    def register_callback(self, callback: Callable[[str, int], None]):
        """注册重连回调"""
        self.reconnect_callbacks.append(callback)
    
    def get_reconnect_stats(self) -> Dict[str, Any]:
        """获取重连统计"""
        return {
            "active_connections": len(self.successful_connections),
            "reconnecting_connections": len(self.reconnect_attempts),
            "attempts_by_connection": self.reconnect_attempts.copy()
        }

def with_error_handling(category: ErrorCategory = ErrorCategory.UNKNOWN,
                       severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                       reraise: bool = True):
    """错误处理装饰器"""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_handler = getattr(args[0], 'error_handler', None)
                if error_handler:
                    error_handler.handle_error(
                        e, category=category, severity=severity,
                        context={"function": func.__name__, "args": args, "kwargs": kwargs}
                    )
                
                if reraise:
                    raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler = getattr(args[0], 'error_handler', None)
                if error_handler:
                    error_handler.handle_error(
                        e, category=category, severity=severity,
                        context={"function": func.__name__, "args": args, "kwargs": kwargs}
                    )
                
                if reraise:
                    raise
        
        # 返回对应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def with_reconnect(reconnect_config: ReconnectConfig = None):
    """重连装饰器"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取连接ID
            connection_id = kwargs.get('connection_id') or f"{func.__name__}_{id(args)}"
            
            # 获取重连管理器
            reconnect_manager = getattr(args[0], 'reconnect_manager', None)
            if not reconnect_manager:
                # 如果没有重连管理器，直接调用原函数
                return await func(*args, **kwargs)
            
            # 尝试连接
            async def attempt_connect():
                return await func(*args, **kwargs)
            
            return await reconnect_manager.try_reconnect(connection_id, attempt_connect)
        
        return wrapper
    
    return decorator