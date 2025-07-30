"""
Metrics Collector

Comprehensive metrics collection system for monitoring application performance and usage.
"""

import time
import threading
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import json
from pathlib import Path
import statistics

from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: float
    value: Union[int, float]
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp,
            'value': self.value,
            'tags': self.tags
        }


@dataclass
class MetricSeries:
    """Time series of metric points"""
    name: str
    points: deque = field(default_factory=lambda: deque(maxlen=10000))
    description: str = ""
    unit: str = ""
    
    def add_point(self, value: Union[int, float], tags: Dict[str, str] = None):
        """Add a metric point"""
        point = MetricPoint(
            timestamp=time.time(),
            value=value,
            tags=tags or {}
        )
        self.points.append(point)
    
    def get_recent_points(self, duration_seconds: int = 3600) -> List[MetricPoint]:
        """Get points from the last N seconds"""
        cutoff_time = time.time() - duration_seconds
        return [p for p in self.points if p.timestamp >= cutoff_time]
    
    def get_statistics(self, duration_seconds: int = 3600) -> Dict[str, float]:
        """Get statistical summary of recent points"""
        recent_points = self.get_recent_points(duration_seconds)
        
        if not recent_points:
            return {}
        
        values = [p.value for p in recent_points]
        
        return {
            'count': len(values),
            'sum': sum(values),
            'min': min(values),
            'max': max(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'stdev': statistics.stdev(values) if len(values) > 1 else 0.0
        }


class MetricsCollector:
    """Central metrics collection system"""
    
    def __init__(self):
        """Initialize metrics collector"""
        self._metrics: Dict[str, MetricSeries] = {}
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._timers: Dict[str, List[float]] = defaultdict(list)
        
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[str, Any], None]] = []
        
        # Built-in metrics
        self._initialize_builtin_metrics()
    
    def _initialize_builtin_metrics(self):
        """Initialize built-in system metrics"""
        self.register_metric("system.cpu_usage", "CPU usage percentage", "percent")
        self.register_metric("system.memory_usage", "Memory usage in MB", "MB")
        self.register_metric("system.disk_usage", "Disk usage percentage", "percent")
        
        self.register_metric("app.videos_processed", "Number of videos processed", "count")
        self.register_metric("app.processing_time", "Video processing time", "seconds")
        self.register_metric("app.errors", "Number of errors", "count")
        self.register_metric("app.cache_hits", "Cache hit count", "count")
        self.register_metric("app.cache_misses", "Cache miss count", "count")
    
    def register_metric(self, name: str, description: str = "", unit: str = "") -> MetricSeries:
        """Register a new metric series"""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = MetricSeries(
                    name=name,
                    description=description,
                    unit=unit
                )
                logger.debug(f"Registered metric: {name}")
            return self._metrics[name]
    
    def record_value(self, metric_name: str, value: Union[int, float], tags: Dict[str, str] = None):
        """Record a metric value"""
        with self._lock:
            if metric_name not in self._metrics:
                self.register_metric(metric_name)
            
            self._metrics[metric_name].add_point(value, tags)
            
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(metric_name, value)
                except Exception as e:
                    logger.error(f"Error in metrics callback: {e}")
    
    def increment_counter(self, counter_name: str, value: int = 1, tags: Dict[str, str] = None):
        """Increment a counter metric"""
        with self._lock:
            self._counters[counter_name] += value
            self.record_value(counter_name, self._counters[counter_name], tags)
    
    def set_gauge(self, gauge_name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric value"""
        with self._lock:
            self._gauges[gauge_name] = value
            self.record_value(gauge_name, value, tags)
    
    def record_histogram(self, histogram_name: str, value: float, tags: Dict[str, str] = None):
        """Record a value in a histogram"""
        with self._lock:
            self._histograms[histogram_name].append(value)
            # Keep only recent values (last 1000)
            if len(self._histograms[histogram_name]) > 1000:
                self._histograms[histogram_name] = self._histograms[histogram_name][-1000:]
            
            self.record_value(histogram_name, value, tags)
    
    def record_timer(self, timer_name: str, duration: float, tags: Dict[str, str] = None):
        """Record a timer duration"""
        with self._lock:
            self._timers[timer_name].append(duration)
            # Keep only recent values (last 1000)
            if len(self._timers[timer_name]) > 1000:
                self._timers[timer_name] = self._timers[timer_name][-1000:]
            
            self.record_value(f"{timer_name}.duration", duration, tags)
    
    def get_metric(self, metric_name: str) -> Optional[MetricSeries]:
        """Get a metric series by name"""
        with self._lock:
            return self._metrics.get(metric_name)
    
    def get_all_metrics(self) -> Dict[str, MetricSeries]:
        """Get all metric series"""
        with self._lock:
            return self._metrics.copy()
    
    def get_counter_value(self, counter_name: str) -> int:
        """Get current counter value"""
        with self._lock:
            return self._counters.get(counter_name, 0)
    
    def get_gauge_value(self, gauge_name: str) -> Optional[float]:
        """Get current gauge value"""
        with self._lock:
            return self._gauges.get(gauge_name)
    
    def get_histogram_stats(self, histogram_name: str) -> Dict[str, float]:
        """Get histogram statistics"""
        with self._lock:
            values = self._histograms.get(histogram_name, [])
            
            if not values:
                return {}
            
            return {
                'count': len(values),
                'sum': sum(values),
                'min': min(values),
                'max': max(values),
                'mean': statistics.mean(values),
                'median': statistics.median(values),
                'p95': statistics.quantiles(values, n=20)[18] if len(values) >= 20 else max(values),
                'p99': statistics.quantiles(values, n=100)[98] if len(values) >= 100 else max(values),
                'stdev': statistics.stdev(values) if len(values) > 1 else 0.0
            }
    
    def get_timer_stats(self, timer_name: str) -> Dict[str, float]:
        """Get timer statistics"""
        return self.get_histogram_stats(timer_name)
    
    def add_callback(self, callback: Callable[[str, Any], None]):
        """Add a callback for metric updates"""
        with self._lock:
            self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[str, Any], None]):
        """Remove a callback"""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def get_summary(self, duration_seconds: int = 3600) -> Dict[str, Any]:
        """Get metrics summary for the specified duration"""
        with self._lock:
            summary = {
                'timestamp': time.time(),
                'duration_seconds': duration_seconds,
                'metrics': {},
                'counters': self._counters.copy(),
                'gauges': self._gauges.copy(),
                'histograms': {},
                'timers': {}
            }
            
            # Get metric statistics
            for name, metric in self._metrics.items():
                stats = metric.get_statistics(duration_seconds)
                if stats:
                    summary['metrics'][name] = {
                        'description': metric.description,
                        'unit': metric.unit,
                        'stats': stats
                    }
            
            # Get histogram statistics
            for name in self._histograms:
                stats = self.get_histogram_stats(name)
                if stats:
                    summary['histograms'][name] = stats
            
            # Get timer statistics
            for name in self._timers:
                stats = self.get_timer_stats(name)
                if stats:
                    summary['timers'][name] = stats
            
            return summary
    
    def export_metrics(self, format_type: str = "json") -> str:
        """Export metrics in specified format"""
        summary = self.get_summary()
        
        if format_type.lower() == "json":
            return json.dumps(summary, indent=2)
        elif format_type.lower() == "prometheus":
            return self._export_prometheus_format(summary)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def _export_prometheus_format(self, summary: Dict[str, Any]) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        # Export counters
        for name, value in summary['counters'].items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        
        # Export gauges
        for name, value in summary['gauges'].items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        
        # Export histogram summaries
        for name, stats in summary['histograms'].items():
            lines.append(f"# TYPE {name} histogram")
            lines.append(f"{name}_count {stats['count']}")
            lines.append(f"{name}_sum {stats['sum']}")
            lines.append(f"{name}_min {stats['min']}")
            lines.append(f"{name}_max {stats['max']}")
            lines.append(f"{name}_mean {stats['mean']}")
        
        return "\n".join(lines)
    
    def save_metrics(self, file_path: Path):
        """Save metrics to file"""
        summary = self.get_summary()
        
        with open(file_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Metrics saved to {file_path}")
    
    def clear_metrics(self):
        """Clear all metrics data"""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._timers.clear()
            self._initialize_builtin_metrics()
        
        logger.info("All metrics cleared")


class MetricsTimer:
    """Context manager for timing operations"""
    
    def __init__(self, collector: MetricsCollector, timer_name: str, tags: Dict[str, str] = None):
        """Initialize timer"""
        self.collector = collector
        self.timer_name = timer_name
        self.tags = tags or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.collector.record_timer(self.timer_name, duration, self.tags)


class MetricsReporter:
    """Periodic metrics reporter"""
    
    def __init__(self, collector: MetricsCollector, interval_seconds: int = 60):
        """Initialize reporter"""
        self.collector = collector
        self.interval_seconds = interval_seconds
        self._running = False
        self._thread = None
        self._stop_event = threading.Event()
    
    def start(self):
        """Start periodic reporting"""
        if self._running:
            return
        
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._report_loop, daemon=True)
        self._thread.start()
        
        logger.info(f"Metrics reporter started (interval: {self.interval_seconds}s)")
    
    def stop(self):
        """Stop periodic reporting"""
        if not self._running:
            return
        
        self._running = False
        self._stop_event.set()
        
        if self._thread:
            self._thread.join(timeout=5.0)
        
        logger.info("Metrics reporter stopped")
    
    def _report_loop(self):
        """Main reporting loop"""
        while self._running and not self._stop_event.is_set():
            try:
                self._generate_report()
            except Exception as e:
                logger.error(f"Error generating metrics report: {e}")
            
            # Wait for next interval
            self._stop_event.wait(self.interval_seconds)
    
    def _generate_report(self):
        """Generate and log metrics report"""
        summary = self.collector.get_summary(duration_seconds=self.interval_seconds)
        
        # Log key metrics
        if summary['counters']:
            logger.info(f"Counters: {summary['counters']}")
        
        if summary['gauges']:
            logger.info(f"Gauges: {summary['gauges']}")
        
        # Log performance metrics
        for name, stats in summary['timers'].items():
            if stats['count'] > 0:
                logger.info(
                    f"Timer {name}: {stats['count']} ops, "
                    f"avg={stats['mean']:.3f}s, "
                    f"p95={stats.get('p95', 0):.3f}s"
                )


# Global metrics collector instance
_global_collector: Optional[MetricsCollector] = None
_global_reporter: Optional[MetricsReporter] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance"""
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector


def get_metrics_reporter() -> MetricsReporter:
    """Get global metrics reporter instance"""
    global _global_reporter
    if _global_reporter is None:
        _global_reporter = MetricsReporter(get_metrics_collector())
    return _global_reporter


def record_metric(metric_name: str, value: Union[int, float], tags: Dict[str, str] = None):
    """Convenience function to record a metric"""
    get_metrics_collector().record_value(metric_name, value, tags)


def increment_counter(counter_name: str, value: int = 1, tags: Dict[str, str] = None):
    """Convenience function to increment a counter"""
    get_metrics_collector().increment_counter(counter_name, value, tags)


def set_gauge(gauge_name: str, value: float, tags: Dict[str, str] = None):
    """Convenience function to set a gauge"""
    get_metrics_collector().set_gauge(gauge_name, value, tags)


def record_timer(timer_name: str, duration: float, tags: Dict[str, str] = None):
    """Convenience function to record a timer"""
    get_metrics_collector().record_timer(timer_name, duration, tags)


def time_operation(timer_name: str, tags: Dict[str, str] = None):
    """Convenience function to create a timer context manager"""
    return MetricsTimer(get_metrics_collector(), timer_name, tags)


def start_metrics_reporting(interval_seconds: int = 60):
    """Start global metrics reporting"""
    get_metrics_reporter().start()


def stop_metrics_reporting():
    """Stop global metrics reporting"""
    global _global_reporter
    if _global_reporter:
        _global_reporter.stop()


def get_metrics_summary() -> Dict[str, Any]:
    """Get current metrics summary"""
    return get_metrics_collector().get_summary()