"""
Performance Profiler

Comprehensive performance profiling and monitoring utilities.
"""

import time
import psutil
import threading
import functools
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging
from contextlib import contextmanager
import cProfile
import pstats
from io import StringIO

from .logging_config import get_logger, get_performance_logger

logger = get_logger(__name__)
perf_logger = get_performance_logger()


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    operation_name: str
    start_time: float
    end_time: float
    duration: float
    memory_before: int
    memory_after: int
    memory_peak: int
    cpu_percent: float
    thread_count: int
    additional_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def memory_delta(self) -> int:
        """Memory usage change"""
        return self.memory_after - self.memory_before

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'operation_name': self.operation_name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'memory_before': self.memory_before,
            'memory_after': self.memory_after,
            'memory_peak': self.memory_peak,
            'memory_delta': self.memory_delta,
            'cpu_percent': self.cpu_percent,
            'thread_count': self.thread_count,
            'additional_data': self.additional_data
        }


class PerformanceProfiler:
    """Main performance profiler class"""

    def __init__(self, enabled: bool = True):
        """
        Initialize performance profiler.

        Args:
            enabled: Whether profiling is enabled
        """
        self.enabled = enabled
        self.metrics: List[PerformanceMetrics] = []
        self._lock = threading.Lock()
        self._process = psutil.Process()
        self._monitoring_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        self._memory_samples: List[int] = []

    def start_monitoring(self):
        """Start background monitoring thread"""
        if not self.enabled or self._monitoring_thread:
            return

        self._stop_monitoring.clear()
        self._monitoring_thread = threading.Thread(
            target=self._monitor_system_resources,
            daemon=True
        )
        self._monitoring_thread.start()
        logger.debug("Performance monitoring started")

    def stop_monitoring(self):
        """Stop background monitoring thread"""
        if self._monitoring_thread:
            self._stop_monitoring.set()
            self._monitoring_thread.join(timeout=1.0)
            self._monitoring_thread = None
            logger.debug("Performance monitoring stopped")

    def _monitor_system_resources(self):
        """Background thread to monitor system resources"""
        while not self._stop_monitoring.wait(0.1):  # Sample every 100ms
            try:
                memory_info = self._process.memory_info()
                self._memory_samples.append(memory_info.rss)

                # Keep only last 1000 samples to prevent memory growth
                if len(self._memory_samples) > 1000:
                    self._memory_samples = self._memory_samples[-1000:]

            except Exception as e:
                logger.debug(f"Error monitoring resources: {e}")

    @contextmanager
    def profile_operation(self, operation_name: str, **additional_data):
        """
        Context manager for profiling operations.

        Args:
            operation_name: Name of the operation being profiled
            **additional_data: Additional data to store with metrics
        """
        if not self.enabled:
            yield
            return

        # Start monitoring if not already started
        if not self._monitoring_thread:
            self.start_monitoring()

        # Capture initial state
        start_time = time.time()
        memory_before = self._process.memory_info().rss
        cpu_before = self._process.cpu_percent()
        thread_count = threading.active_count()

        # Clear memory samples for peak detection
        self._memory_samples.clear()

        try:
            yield
        finally:
            # Capture final state
            end_time = time.time()
            memory_after = self._process.memory_info().rss
            cpu_after = self._process.cpu_percent()

            # Calculate peak memory
            memory_peak = max(self._memory_samples) if self._memory_samples else memory_after

            # Create metrics
            metrics = PerformanceMetrics(
                operation_name=operation_name,
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                memory_before=memory_before,
                memory_after=memory_after,
                memory_peak=memory_peak,
                cpu_percent=(cpu_before + cpu_after) / 2,
                thread_count=thread_count,
                additional_data=additional_data
            )

            # Store metrics
            with self._lock:
                self.metrics.append(metrics)

            # Log performance data
            perf_logger.info(
                f"Operation completed: {operation_name}",
                extra={
                    'duration': metrics.duration,
                    'memory_delta': metrics.memory_delta,
                    'memory_peak': metrics.memory_peak,
                    'cpu_percent': metrics.cpu_percent,
                    **additional_data
                }
            )

    def profile_function(self, operation_name: str = None, **additional_data):
        """
        Decorator for profiling functions.

        Args:
            operation_name: Name of the operation (defaults to function name)
            **additional_data: Additional data to store with metrics
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                name = operation_name or f"{func.__module__}.{func.__name__}"
                with self.profile_operation(name, **additional_data):
                    return func(*args, **kwargs)
            return wrapper
        return decorator

    def get_metrics(self, operation_name: str = None) -> List[PerformanceMetrics]:
        """
        Get performance metrics.

        Args:
            operation_name: Filter by operation name (optional)

        Returns:
            List of performance metrics
        """
        with self._lock:
            if operation_name:
                return [m for m in self.metrics if m.operation_name == operation_name]
            return self.metrics.copy()

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics"""
        with self._lock:
            if not self.metrics:
                return {}

            # Group by operation name
            operations = {}
            for metric in self.metrics:
                name = metric.operation_name
                if name not in operations:
                    operations[name] = []
                operations[name].append(metric)

            # Calculate statistics for each operation
            summary = {}
            for name, metrics_list in operations.items():
                durations = [m.duration for m in metrics_list]
                memory_deltas = [m.memory_delta for m in metrics_list]

                summary[name] = {
                    'count': len(metrics_list),
                    'total_duration': sum(durations),
                    'avg_duration': sum(durations) / len(durations),
                    'min_duration': min(durations),
                    'max_duration': max(durations),
                    'avg_memory_delta': sum(memory_deltas) / len(memory_deltas),
                    'max_memory_delta': max(memory_deltas),
                    'min_memory_delta': min(memory_deltas)
                }

            return summary

    def save_metrics(self, file_path: Path):
        """Save metrics to JSON file"""
        with self._lock:
            data = {
                'timestamp': time.time(),
                'metrics': [m.to_dict() for m in self.metrics],
                'summary': self.get_summary()
            }

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Performance metrics saved to {file_path}")

    def clear_metrics(self):
        """Clear all stored metrics"""
        with self._lock:
            self.metrics.clear()
        logger.debug("Performance metrics cleared")


class CodeProfiler:
    """Code profiler using cProfile"""

    def __init__(self):
        """Initialize code profiler"""
        self.profiler: Optional[cProfile.Profile] = None
        self.enabled = False

    def start(self):
        """Start code profiling"""
        if self.profiler:
            self.stop()

        self.profiler = cProfile.Profile()
        self.profiler.enable()
        self.enabled = True
        logger.debug("Code profiling started")

    def stop(self) -> Optional[str]:
        """
        Stop code profiling and return results.

        Returns:
            Profiling results as string
        """
        if not self.profiler or not self.enabled:
            return None

        self.profiler.disable()
        self.enabled = False

        # Generate report
        stats_stream = StringIO()
        stats = pstats.Stats(self.profiler, stream=stats_stream)
        stats.sort_stats('cumulative')
        stats.print_stats(50)  # Top 50 functions

        result = stats_stream.getvalue()
        logger.debug("Code profiling stopped")
        return result

    @contextmanager
    def profile_code(self):
        """Context manager for code profiling"""
        self.start()
        try:
            yield
        finally:
            result = self.stop()
            if result:
                logger.info("Code profiling results:\n" + result)


class MemoryProfiler:
    """Memory usage profiler"""

    def __init__(self):
        """Initialize memory profiler"""
        self._process = psutil.Process()
        self._snapshots: List[Dict[str, Any]] = []

    def take_snapshot(self, label: str = None) -> Dict[str, Any]:
        """
        Take a memory snapshot.

        Args:
            label: Optional label for the snapshot

        Returns:
            Memory snapshot data
        """
        memory_info = self._process.memory_info()
        memory_percent = self._process.memory_percent()

        snapshot = {
            'timestamp': time.time(),
            'label': label or f"snapshot_{len(self._snapshots)}",
            'rss': memory_info.rss,
            'vms': memory_info.vms,
            'percent': memory_percent,
            'available': psutil.virtual_memory().available,
            'total': psutil.virtual_memory().total
        }

        self._snapshots.append(snapshot)
        return snapshot

    def get_memory_growth(self) -> List[Dict[str, Any]]:
        """Get memory growth between snapshots"""
        if len(self._snapshots) < 2:
            return []

        growth = []
        for i in range(1, len(self._snapshots)):
            prev = self._snapshots[i-1]
            curr = self._snapshots[i]

            growth.append({
                'from_label': prev['label'],
                'to_label': curr['label'],
                'rss_delta': curr['rss'] - prev['rss'],
                'vms_delta': curr['vms'] - prev['vms'],
                'percent_delta': curr['percent'] - prev['percent'],
                'time_delta': curr['timestamp'] - prev['timestamp']
            })

        return growth

    def get_peak_memory(self) -> Dict[str, Any]:
        """Get peak memory usage"""
        if not self._snapshots:
            return {}

        peak_rss = max(self._snapshots, key=lambda x: x['rss'])
        peak_vms = max(self._snapshots, key=lambda x: x['vms'])
        peak_percent = max(self._snapshots, key=lambda x: x['percent'])

        return {
            'peak_rss': peak_rss,
            'peak_vms': peak_vms,
            'peak_percent': peak_percent
        }


class PerformanceOptimizer:
    """Performance optimization utilities"""

    def __init__(self, profiler: PerformanceProfiler):
        """
        Initialize performance optimizer.

        Args:
            profiler: Performance profiler instance
        """
        self.profiler = profiler

    def analyze_bottlenecks(self) -> Dict[str, Any]:
        """Analyze performance bottlenecks"""
        summary = self.profiler.get_summary()
        if not summary:
            return {}

        # Find slowest operations
        slowest_ops = sorted(
            summary.items(),
            key=lambda x: x[1]['avg_duration'],
            reverse=True
        )

        # Find memory-intensive operations
        memory_intensive = sorted(
            summary.items(),
            key=lambda x: x[1]['avg_memory_delta'],
            reverse=True
        )

        # Find most frequent operations
        most_frequent = sorted(
            summary.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )

        return {
            'slowest_operations': slowest_ops[:5],
            'memory_intensive_operations': memory_intensive[:5],
            'most_frequent_operations': most_frequent[:5],
            'total_operations': len(summary),
            'total_time': sum(op['total_duration'] for op in summary.values())
        }

    def suggest_optimizations(self) -> List[str]:
        """Suggest performance optimizations"""
        analysis = self.analyze_bottlenecks()
        suggestions = []

        if not analysis:
            return ["No performance data available for analysis"]

        # Analyze slowest operations
        if analysis['slowest_operations']:
            slowest = analysis['slowest_operations'][0]
            if slowest[1]['avg_duration'] > 1.0:
                suggestions.append(
                    f"Consider optimizing '{slowest[0]}' - average duration: {slowest[1]['avg_duration']:.2f}s"
                )

        # Analyze memory usage
        if analysis['memory_intensive_operations']:
            memory_heavy = analysis['memory_intensive_operations'][0]
            if memory_heavy[1]['avg_memory_delta'] > 100 * 1024 * 1024:  # 100MB
                suggestions.append(
                    f"Consider reducing memory usage in '{memory_heavy[0]}' - "
                    f"average memory delta: {memory_heavy[1]['avg_memory_delta'] / 1024 / 1024:.1f}MB"
                )

        # Analyze frequency
        if analysis['most_frequent_operations']:
            frequent = analysis['most_frequent_operations'][0]
            if frequent[1]['count'] > 100:
                suggestions.append(
                    f"Consider caching results for '{frequent[0]}' - called {frequent[1]['count']} times"
                )

        # General suggestions
        if analysis['total_time'] > 10.0:
            suggestions.append("Consider implementing parallel processing for long-running operations")

        if not suggestions:
            suggestions.append("Performance appears to be within acceptable ranges")

        return suggestions


# Global profiler instance
_global_profiler: Optional[PerformanceProfiler] = None


def get_profiler() -> PerformanceProfiler:
    """Get global profiler instance"""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = PerformanceProfiler()
    return _global_profiler


def profile_operation(operation_name: str, **additional_data):
    """Convenience function for profiling operations"""
    return get_profiler().profile_operation(operation_name, **additional_data)


def profile_function(operation_name: str = None, **additional_data):
    """Convenience decorator for profiling functions"""
    return get_profiler().profile_function(operation_name, **additional_data)


def enable_profiling():
    """Enable global profiling"""
    profiler = get_profiler()
    profiler.enabled = True
    profiler.start_monitoring()


def disable_profiling():
    """Disable global profiling"""
    profiler = get_profiler()
    profiler.enabled = False
    profiler.stop_monitoring()


def get_performance_report() -> Dict[str, Any]:
    """Get comprehensive performance report"""
    profiler = get_profiler()
    optimizer = PerformanceOptimizer(profiler)

    return {
        'summary': profiler.get_summary(),
        'bottlenecks': optimizer.analyze_bottlenecks(),
        'suggestions': optimizer.suggest_optimizations(),
        'total_metrics': len(profiler.get_metrics())
    }
