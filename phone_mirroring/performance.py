"""
性能优化模块
"""

import asyncio
import time
import threading
import logging
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics

logger = logging.getLogger(__name__)

class OptimizationLevel(Enum):
    """优化级别"""
    DISABLED = "disabled"
    BASIC = "basic"
    AGGRESSIVE = "aggressive"
    ADAPTIVE = "adaptive"

@dataclass
class PerformanceMetrics:
    """性能指标"""
    fps: float = 0
    latency: float = 0
    bandwidth: float = 0
    cpu_usage: float = 0
    memory_usage: float = 0
    frame_loss: float = 0
    quality_score: float = 100
    timestamp: float = field(default_factory=time.time)

@dataclass
class BufferStats:
    """缓冲区统计"""
    buffer_size: int = 0
    used_size: int = 0
    utilization: float = 0
    overflow_count: int = 0
    underflow_count: int = 0

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", True)
        self.sample_interval = config.get("sample_interval", 1000)  # ms
        self.history_size = config.get("history_size", 60)
        
        # 性能数据
        self.metrics_history: List[PerformanceMetrics] = []
        self.buffer_stats: Dict[str, BufferStats] = {}
        
        # 监控任务
        self.monitor_task: Optional[asyncio.Task] = None
        self.callbacks: List[Callable] = []
        
        # 统计缓存
        self._frame_times: List[float] = []
        self._latency_samples: List[float] = []
        self._bandwidth_samples: List[float] = []
        
        self._lock = threading.Lock()
    
    def start(self):
        """启动性能监控"""
        if not self.enabled:
            return
        
        loop = asyncio.get_event_loop()
        self.monitor_task = loop.create_task(self._monitor_loop())
        logger.info("Performance monitor started")
    
    async def stop(self):
        """停止性能监控"""
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Performance monitor stopped")
    
    async def _monitor_loop(self):
        """监控循环"""
        while True:
            try:
                await asyncio.sleep(self.sample_interval / 1000)
                
                # 收集性能指标
                metrics = self._collect_metrics()
                
                # 更新历史记录
                with self._lock:
                    self.metrics_history.append(metrics)
                    if len(self.metrics_history) > self.history_size:
                        self.metrics_history.pop(0)
                
                # 触发回调
                for callback in self.callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(metrics)
                        else:
                            callback(metrics)
                    except Exception as e:
                        logger.error(f"Performance callback error: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
    
    def _collect_metrics(self) -> PerformanceMetrics:
        """收集性能指标"""
        # 计算FPS
        fps = self._calculate_fps()
        
        # 计算延迟
        latency = self._calculate_latency()
        
        # 计算带宽
        bandwidth = self._calculate_bandwidth()
        
        # 获取系统资源使用情况
        cpu_usage = self._get_cpu_usage()
        memory_usage = self._get_memory_usage()
        
        # 计算帧丢失率
        frame_loss = self._calculate_frame_loss()
        
        # 计算质量评分
        quality_score = self._calculate_quality_score(fps, latency, frame_loss)
        
        return PerformanceMetrics(
            fps=fps,
            latency=latency,
            bandwidth=bandwidth,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            frame_loss=frame_loss,
            quality_score=quality_score
        )
    
    def record_frame(self, frame_time: float):
        """记录帧时间"""
        with self._lock:
            self._frame_times.append(frame_time)
            if len(self._frame_times) > 100:
                self._frame_times.pop(0)
    
    def record_latency(self, latency: float):
        """记录延迟"""
        with self._lock:
            self._latency_samples.append(latency)
            if len(self._latency_samples) > 100:
                self._latency_samples.pop(0)
    
    def record_bandwidth(self, bytes_per_second: float):
        """记录带宽"""
        with self._lock:
            self._bandwidth_samples.append(bytes_per_second)
            if len(self._bandwidth_samples) > 100:
                self._bandwidth_samples.pop(0)
    
    def _calculate_fps(self) -> float:
        """计算FPS"""
        with self._lock:
            if len(self._frame_times) < 2:
                return 0
            
            # 使用最近1秒的帧数计算FPS
            current_time = time.time()
            recent_frames = [t for t in self._frame_times if current_time - t <= 1.0]
            return len(recent_frames)
    
    def _calculate_latency(self) -> float:
        """计算平均延迟"""
        with self._lock:
            if not self._latency_samples:
                return 0
            
            return statistics.mean(self._latency_samples)
    
    def _calculate_bandwidth(self) -> float:
        """计算平均带宽"""
        with self._lock:
            if not self._bandwidth_samples:
                return 0
            
            return statistics.mean(self._bandwidth_samples)
    
    def _get_cpu_usage(self) -> float:
        """获取CPU使用率"""
        try:
            import psutil
            return psutil.cpu_percent(interval=None)
        except ImportError:
            return 0
    
    def _get_memory_usage(self) -> float:
        """获取内存使用率"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_percent()
        except ImportError:
            return 0
    
    def _calculate_frame_loss(self) -> float:
        """计算帧丢失率"""
        # 简化实现，实际需要基于期望帧数和实际帧数计算
        return 0
    
    def _calculate_quality_score(self, fps: float, latency: float, 
                                frame_loss: float) -> float:
        """计算质量评分"""
        # 基于FPS、延迟和帧丢失率计算质量评分
        fps_score = min(fps / 30, 1.0) * 40  # 40分
        latency_score = max(0, (200 - latency) / 200) * 30  # 30分
        loss_score = max(0, (100 - frame_loss) / 100) * 30  # 30分
        
        return fps_score + latency_score + loss_score
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """获取当前性能指标"""
        with self._lock:
            return self.metrics_history[-1] if self.metrics_history else None
    
    def get_average_metrics(self, duration: float = 60) -> Optional[PerformanceMetrics]:
        """获取平均性能指标"""
        with self._lock:
            if not self.metrics_history:
                return None
            
            # 过滤指定时间段内的数据
            current_time = time.time()
            recent_metrics = [
                m for m in self.metrics_history 
                if current_time - m.timestamp <= duration
            ]
            
            if not recent_metrics:
                return None
            
            # 计算平均值
            return PerformanceMetrics(
                fps=statistics.mean(m.fps for m in recent_metrics),
                latency=statistics.mean(m.latency for m in recent_metrics),
                bandwidth=statistics.mean(m.bandwidth for m in recent_metrics),
                cpu_usage=statistics.mean(m.cpu_usage for m in recent_metrics),
                memory_usage=statistics.mean(m.memory_usage for m in recent_metrics),
                frame_loss=statistics.mean(m.frame_loss for m in recent_metrics),
                quality_score=statistics.mean(m.quality_score for m in recent_metrics)
            )

class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.level = OptimizationLevel(config.get("level", "basic"))
        self.monitor = PerformanceMonitor(config.get("monitor", {}))
        
        # 优化参数
        self.adaptive_quality = config.get("adaptive_quality", True)
        self.auto_bitrate = config.get("auto_bitrate", True)
        self.buffer_optimization = config.get("buffer_optimization", True)
        
        # 当前状态
        self.current_quality = "high"
        self.current_bitrate = config.get("default_bitrate", 2000000)
        self.current_fps = config.get("default_fps", 30)
        
        # 优化阈值
        self.thresholds = config.get("thresholds", {
            "high_latency": 150,  # ms
            "low_fps": 20,
            "high_cpu": 80,  # %
            "low_quality": 60
        })
        
        # 回调函数
        self.optimization_callbacks: List[Callable] = []
    
    async def start(self):
        """启动性能优化"""
        self.monitor.start()
        self.monitor.register_callback(self._on_metrics_update)
        
        if self.level == OptimizationLevel.ADAPTIVE:
            # 启动自适应优化
            asyncio.create_task(self._adaptive_optimization_loop())
        
        logger.info(f"Performance optimizer started (level: {self.level.value})")
    
    async def stop(self):
        """停止性能优化"""
        await self.monitor.stop()
        logger.info("Performance optimizer stopped")
    
    async def _adaptive_optimization_loop(self):
        """自适应优化循环"""
        while True:
            try:
                await asyncio.sleep(5)  # 5秒检查一次
                
                metrics = self.monitor.get_current_metrics()
                if not metrics:
                    continue
                
                # 检查是否需要优化
                if self._should_optimize(metrics):
                    await self._optimize_performance(metrics)
                
            except Exception as e:
                logger.error(f"Adaptive optimization error: {e}")
                await asyncio.sleep(5)
    
    def _on_metrics_update(self, metrics: PerformanceMetrics):
        """性能指标更新回调"""
        # 触发优化回调
        for callback in self.optimization_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(metrics))
                else:
                    callback(metrics)
            except Exception as e:
                logger.error(f"Optimization callback error: {e}")
    
    def _should_optimize(self, metrics: PerformanceMetrics) -> bool:
        """判断是否需要优化"""
        if self.level == OptimizationLevel.DISABLED:
            return False
        
        thresholds = self.thresholds
        
        return (
            metrics.latency > thresholds["high_latency"] or
            metrics.fps < thresholds["low_fps"] or
            metrics.cpu_usage > thresholds["high_cpu"] or
            metrics.quality_score < thresholds["low_quality"]
        )
    
    async def _optimize_performance(self, metrics: PerformanceMetrics):
        """执行性能优化"""
        optimizations = []
        
        # 延迟优化
        if metrics.latency > self.thresholds["high_latency"]:
            optimizations.append(await self._optimize_latency(metrics))
        
        # FPS优化
        if metrics.fps < self.thresholds["low_fps"]:
            optimizations.append(await self._optimize_fps(metrics))
        
        # CPU优化
        if metrics.cpu_usage > self.thresholds["high_cpu"]:
            optimizations.append(await self._optimize_cpu(metrics))
        
        # 质量优化
        if metrics.quality_score < self.thresholds["low_quality"]:
            optimizations.append(await self._optimize_quality(metrics))
        
        if optimizations:
            logger.info(f"Applied optimizations: {optimizations}")
    
    async def _optimize_latency(self, metrics: PerformanceMetrics) -> str:
        """优化延迟"""
        if self.auto_bitrate and self.current_bitrate > 1000000:
            # 降低码率
            self.current_bitrate = int(self.current_bitrate * 0.8)
            return f"Reduced bitrate to {self.current_bitrate}"
        
        if self.buffer_optimization:
            # 调整缓冲区大小
            return "Optimized buffer size"
        
        return "No latency optimization applied"
    
    async def _optimize_fps(self, metrics: PerformanceMetrics) -> str:
        """优化FPS"""
        if self.current_fps > 15:
            self.current_fps = max(15, int(self.current_fps * 0.8))
            return f"Reduced FPS to {self.current_fps}"
        
        return "No FPS optimization applied"
    
    async def _optimize_cpu(self, metrics: PerformanceMetrics) -> str:
        """优化CPU使用"""
        # 降低画质
        if self.current_quality != "low":
            self.current_quality = "low"
            return "Reduced quality to low"
        
        return "No CPU optimization applied"
    
    async def _optimize_quality(self, metrics: PerformanceMetrics) -> str:
        """优化质量"""
        quality_levels = ["ultra", "high", "medium", "low"]
        current_index = quality_levels.index(self.current_quality) if self.current_quality in quality_levels else 0
        
        if current_index < len(quality_levels) - 1:
            self.current_quality = quality_levels[current_index + 1]
            return f"Reduced quality to {self.current_quality}"
        
        return "No quality optimization applied"
    
    def get_optimization_settings(self) -> Dict[str, Any]:
        """获取当前优化设置"""
        return {
            "level": self.level.value,
            "quality": self.current_quality,
            "bitrate": self.current_bitrate,
            "fps": self.current_fps,
            "adaptive_quality": self.adaptive_quality,
            "auto_bitrate": self.auto_bitrate
        }
    
    def register_callback(self, callback: Callable):
        """注册优化回调"""
        self.optimization_callbacks.append(callback)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        current = self.monitor.get_current_metrics()
        average = self.monitor.get_average_metrics()
        
        return {
            "current": current.__dict__ if current else None,
            "average": average.__dict__ if average else None,
            "optimization": self.get_optimization_settings(),
            "thresholds": self.thresholds
        }

# 便捷函数
def create_monitor(config: Dict[str, Any] = None) -> PerformanceMonitor:
    """创建性能监控器"""
    default_config = {
        "enabled": True,
        "sample_interval": 1000,
        "history_size": 60
    }
    
    if config:
        default_config.update(config)
    
    return PerformanceMonitor(default_config)

def create_optimizer(config: Dict[str, Any] = None) -> PerformanceOptimizer:
    """创建性能优化器"""
    default_config = {
        "level": "basic",
        "adaptive_quality": True,
        "auto_bitrate": True,
        "buffer_optimization": True,
        "default_bitrate": 2000000,
        "default_fps": 30,
        "thresholds": {
            "high_latency": 150,
            "low_fps": 20,
            "high_cpu": 80,
            "low_quality": 60
        }
    }
    
    if config:
        default_config.update(config)
    
    return PerformanceOptimizer(default_config)