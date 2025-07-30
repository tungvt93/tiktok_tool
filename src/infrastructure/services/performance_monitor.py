"""
Performance Monitoring Service

Service for monitoring application performance and resource usage.
"""

import time
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime, timedelta

from ...shared.utils.logging_config import get_logger, get_performance_logger
from ...shared.utils.performance_profiler import PerformanceProfiler, get_profiler

logger = get_logger(__name__)
perf_logger = get_performance_logger()


@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_available: int
    memory_used: int
    disk_usage_percent: float
    disk_free: int
    network_sent: int
    network_recv: int
    process_count: int
    thread_count: int


@dataclass
class ApplicationMetrics:
    """Application-specific metrics"""
    timestamp: float
    videos_processed: int
    processing_time_total: float
    processing_time_avg: float
    cache_hits: int
    cache_misses: int
    errors_count: int
    active_jobs: int
    queue_size: int


class PerformanceMonitor:
    """Performance monitoring service"""

    def __init__(self, config=None):
        """
        Initialize performance monitor.

        Args:
            config: Application configuration
        """
        self.config = config
        self.profiler = get_profiler()
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Metrics storage
        self._system_metrics: List[SystemMetrics] = []
        self._app_metrics: List[ApplicationMetrics] = []
        self._metrics_lock = threading.Lock()

        # Performance counters
        self._counters = {
            'videos_processed': 0,
            'processing_time_total': 0.0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors_count': 0,
            'active_jobs': 0,
            'queue_size': 0
        }
        self._counters_lock = threading.Lock()

        # System info
        self._process = psutil.Process()
        self._initial_network = psutil.net_io_counters()

        # Alerts
        self._alert_thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_usage_percent': 90.0,
            'processing_time_avg': 30.0,  # seconds
            'error_rate': 0.1  # 10%
        }
        self._alert_callbacks: List[Callable] = []

    def start_monitoring(self, interval: float = 5.0):
        """
        Start performance monitoring.

        Args:
            interval: Monitoring interval in seconds
        """
        if self._monitoring:
            return

        self._monitoring = True
        self._stop_event.clear()

        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()

        # Start profiler monitoring
        self.profiler.start_monitoring()

        logger.info(f"Performance monitoring started (interval: {interval}s)")

    def stop_monitoring(self):
        """Stop performance monitoring"""
        if not self._monitoring:
            return

        self._monitoring = False
        self._stop_event.set()

        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
            self._monitor_thread = None

        # Stop profiler monitoring
        self.profiler.stop_monitoring()

        logger.info("Performance monitoring stopped")

    def _monitor_loop(self, interval: float):
        """Main monitoring loop"""
        while not self._stop_event.wait(interval):
            try:
                self._collect_system_metrics()
                self._collect_app_metrics()
                self._check_alerts()
                self._cleanup_old_metrics()

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

    def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()

            # Disk usage
            disk = psutil.disk_usage('/')

            # Network
            network = psutil.net_io_counters()
            network_sent = network.bytes_sent - self._initial_network.bytes_sent
            network_recv = network.bytes_recv - self._initial_network.bytes_recv

            # Process info
            process_count = len(psutil.pids())
            thread_count = threading.active_count()

            metrics = SystemMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_available=memory.available,
                memory_used=memory.used,
                disk_usage_percent=disk.percent,
                disk_free=disk.free,
                network_sent=network_sent,
                network_recv=network_recv,
                process_count=process_count,
                thread_count=thread_count
            )

            with self._metrics_lock:
                self._system_metrics.append(metrics)

            # Log system metrics
            perf_logger.debug(
                "System metrics collected",
                extra={
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'disk_usage_percent': disk.percent,
                    'thread_count': thread_count
                }
            )

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")

    def _collect_app_metrics(self):
        """Collect application-specific metrics"""
        try:
            with self._counters_lock:
                counters = self._counters.copy()

            # Calculate averages
            processing_time_avg = 0.0
            if counters['videos_processed'] > 0:
                processing_time_avg = counters['processing_time_total'] / counters['videos_processed']

            metrics = ApplicationMetrics(
                timestamp=time.time(),
                videos_processed=counters['videos_processed'],
                processing_time_total=counters['processing_time_total'],
                processing_time_avg=processing_time_avg,
                cache_hits=counters['cache_hits'],
                cache_misses=counters['cache_misses'],
                errors_count=counters['errors_count'],
                active_jobs=counters['active_jobs'],
                queue_size=counters['queue_size']
            )

            with self._metrics_lock:
                self._app_metrics.append(metrics)

            # Log application metrics
            perf_logger.info(
                "Application metrics collected",
                extra={
                    'videos_processed': counters['videos_processed'],
                    'processing_time_avg': processing_time_avg,
                    'cache_hit_rate': self._calculate_cache_hit_rate(),
                    'error_rate': self._calculate_error_rate(),
                    'active_jobs': counters['active_jobs']
                }
            )

        except Exception as e:
            logger.error(f"Error collecting application metrics: {e}")

    def _check_alerts(self):
        """Check for performance alerts"""
        try:
            with self._metrics_lock:
                if not self._system_metrics or not self._app_metrics:
                    return

                latest_system = self._system_metrics[-1]
                latest_app = self._app_metrics[-1]

            alerts = []

            # Check system thresholds
            if latest_system.cpu_percent > self._alert_thresholds['cpu_percent']:
                alerts.append(f"High CPU usage: {latest_system.cpu_percent:.1f}%")

            if latest_system.memory_percent > self._alert_thresholds['memory_percent']:
                alerts.append(f"High memory usage: {latest_system.memory_percent:.1f}%")

            if latest_system.disk_usage_percent > self._alert_thresholds['disk_usage_percent']:
                alerts.append(f"High disk usage: {latest_system.disk_usage_percent:.1f}%")

            # Check application thresholds
            if latest_app.processing_time_avg > self._alert_thresholds['processing_time_avg']:
                alerts.append(f"Slow processing: {latest_app.processing_time_avg:.1f}s average")

            error_rate = self._calculate_error_rate()
            if error_rate > self._alert_thresholds['error_rate']:
                alerts.append(f"High error rate: {error_rate:.1%}")

            # Trigger alerts
            for alert in alerts:
                self._trigger_alert(alert)

        except Exception as e:
            logger.error(f"Error checking alerts: {e}")

    def _trigger_alert(self, message: str):
        """Trigger performance alert"""
        logger.warning(f"Performance Alert: {message}")

        for callback in self._alert_callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

    def _cleanup_old_metrics(self):
        """Clean up old metrics to prevent memory growth"""
        try:
            cutoff_time = time.time() - 3600  # Keep last hour

            with self._metrics_lock:
                self._system_metrics = [
                    m for m in self._system_metrics
                    if m.timestamp > cutoff_time
                ]
                self._app_metrics = [
                    m for m in self._app_metrics
                    if m.timestamp > cutoff_time
                ]

        except Exception as e:
            logger.error(f"Error cleaning up metrics: {e}")

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        with self._counters_lock:
            total_requests = self._counters['cache_hits'] + self._counters['cache_misses']
            if total_requests == 0:
                return 0.0
            return self._counters['cache_hits'] / total_requests

    def _calculate_error_rate(self) -> float:
        """Calculate error rate"""
        with self._counters_lock:
            total_operations = self._counters['videos_processed'] + self._counters['errors_count']
            if total_operations == 0:
                return 0.0
            return self._counters['errors_count'] / total_operations

    # Counter management methods
    def increment_counter(self, counter_name: str, value: int = 1):
        """Increment a performance counter"""
        with self._counters_lock:
            if counter_name in self._counters:
                self._counters[counter_name] += value

    def set_counter(self, counter_name: str, value: int):
        """Set a performance counter value"""
        with self._counters_lock:
            if counter_name in self._counters:
                self._counters[counter_name] = value

    def add_processing_time(self, duration: float):
        """Add processing time to total"""
        with self._counters_lock:
            self._counters['processing_time_total'] += duration

    # Alert management
    def add_alert_callback(self, callback: Callable[[str], None]):
        """Add alert callback function"""
        self._alert_callbacks.append(callback)

    def set_alert_threshold(self, metric: str, threshold: float):
        """Set alert threshold for a metric"""
        if metric in self._alert_thresholds:
            self._alert_thresholds[metric] = threshold

    # Data access methods
    def get_system_metrics(self, duration_minutes: int = 60) -> List[SystemMetrics]:
        """Get system metrics for specified duration"""
        cutoff_time = time.time() - (duration_minutes * 60)

        with self._metrics_lock:
            return [
                m for m in self._system_metrics
                if m.timestamp > cutoff_time
            ]

    def get_app_metrics(self, duration_minutes: int = 60) -> List[ApplicationMetrics]:
        """Get application metrics for specified duration"""
        cutoff_time = time.time() - (duration_minutes * 60)

        with self._metrics_lock:
            return [
                m for m in self._app_metrics
                if m.timestamp > cutoff_time
            ]

    def get_current_status(self) -> Dict[str, Any]:
        """Get current performance status"""
        with self._metrics_lock:
            latest_system = self._system_metrics[-1] if self._system_metrics else None
            latest_app = self._app_metrics[-1] if self._app_metrics else None

        with self._counters_lock:
            counters = self._counters.copy()

        return {
            'monitoring_active': self._monitoring,
            'system_metrics': {
                'cpu_percent': latest_system.cpu_percent if latest_system else 0,
                'memory_percent': latest_system.memory_percent if latest_system else 0,
                'disk_usage_percent': latest_system.disk_usage_percent if latest_system else 0,
                'thread_count': latest_system.thread_count if latest_system else 0
            },
            'application_metrics': {
                'videos_processed': counters['videos_processed'],
                'processing_time_avg': latest_app.processing_time_avg if latest_app else 0,
                'cache_hit_rate': self._calculate_cache_hit_rate(),
                'error_rate': self._calculate_error_rate(),
                'active_jobs': counters['active_jobs'],
                'queue_size': counters['queue_size']
            },
            'profiler_metrics_count': len(self.profiler.get_metrics())
        }

    def export_metrics(self, file_path: Path):
        """Export metrics to JSON file"""
        with self._metrics_lock:
            system_metrics = [
                {
                    'timestamp': m.timestamp,
                    'cpu_percent': m.cpu_percent,
                    'memory_percent': m.memory_percent,
                    'memory_available': m.memory_available,
                    'memory_used': m.memory_used,
                    'disk_usage_percent': m.disk_usage_percent,
                    'disk_free': m.disk_free,
                    'network_sent': m.network_sent,
                    'network_recv': m.network_recv,
                    'process_count': m.process_count,
                    'thread_count': m.thread_count
                }
                for m in self._system_metrics
            ]

            app_metrics = [
                {
                    'timestamp': m.timestamp,
                    'videos_processed': m.videos_processed,
                    'processing_time_total': m.processing_time_total,
                    'processing_time_avg': m.processing_time_avg,
                    'cache_hits': m.cache_hits,
                    'cache_misses': m.cache_misses,
                    'errors_count': m.errors_count,
                    'active_jobs': m.active_jobs,
                    'queue_size': m.queue_size
                }
                for m in self._app_metrics
            ]

        with self._counters_lock:
            counters = self._counters.copy()

        data = {
            'export_timestamp': time.time(),
            'export_date': datetime.now().isoformat(),
            'system_metrics': system_metrics,
            'application_metrics': app_metrics,
            'counters': counters,
            'alert_thresholds': self._alert_thresholds,
            'profiler_summary': self.profiler.get_summary()
        }

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Performance metrics exported to {file_path}")

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        current_status = self.get_current_status()
        profiler_summary = self.profiler.get_summary()

        # Calculate trends
        system_metrics = self.get_system_metrics(60)  # Last hour
        app_metrics = self.get_app_metrics(60)

        cpu_trend = self._calculate_trend([m.cpu_percent for m in system_metrics])
        memory_trend = self._calculate_trend([m.memory_percent for m in system_metrics])

        return {
            'report_timestamp': time.time(),
            'report_date': datetime.now().isoformat(),
            'current_status': current_status,
            'trends': {
                'cpu_trend': cpu_trend,
                'memory_trend': memory_trend
            },
            'profiler_summary': profiler_summary,
            'recommendations': self._generate_recommendations(current_status, profiler_summary)
        }

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from values"""
        if len(values) < 2:
            return "insufficient_data"

        # Simple trend calculation
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]

        if not first_half or not second_half:
            return "insufficient_data"

        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)

        diff_percent = (second_avg - first_avg) / first_avg * 100

        if diff_percent > 10:
            return "increasing"
        elif diff_percent < -10:
            return "decreasing"
        else:
            return "stable"

    def _generate_recommendations(self, status: Dict[str, Any], profiler_summary: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []

        # System recommendations
        sys_metrics = status['system_metrics']
        if sys_metrics['cpu_percent'] > 70:
            recommendations.append("Consider reducing CPU-intensive operations or adding more processing power")

        if sys_metrics['memory_percent'] > 80:
            recommendations.append("Memory usage is high - consider implementing memory optimization")

        # Application recommendations
        app_metrics = status['application_metrics']
        if app_metrics['cache_hit_rate'] < 0.8:
            recommendations.append("Cache hit rate is low - consider improving caching strategy")

        if app_metrics['error_rate'] > 0.05:
            recommendations.append("Error rate is elevated - investigate and fix recurring errors")

        if app_metrics['processing_time_avg'] > 10:
            recommendations.append("Average processing time is high - consider performance optimization")

        # Profiler recommendations
        if profiler_summary:
            total_ops = sum(op['count'] for op in profiler_summary.values())
            if total_ops > 1000:
                recommendations.append("High operation count detected - consider implementing operation batching")

        if not recommendations:
            recommendations.append("Performance appears to be within acceptable ranges")

        return recommendations


# Global monitor instance
_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor
