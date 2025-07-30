"""
Monitoring Dashboard

Real-time monitoring dashboard for system and application metrics.
"""

import time
import threading
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
import psutil
import os

from src.shared.utils.logging_config import get_logger
from src.shared.utils.metrics_collector import get_metrics_collector, MetricsCollector
from src.infrastructure.services.performance_monitor import PerformanceMonitor

logger = get_logger(__name__)


class MonitoringDashboard:
    """Real-time monitoring dashboard"""
    
    def __init__(self, update_interval: int = 5):
        """Initialize monitoring dashboard"""
        self.update_interval = update_interval
        self.metrics_collector = get_metrics_collector()
        self.performance_monitor = PerformanceMonitor()
        
        self._running = False
        self._thread = None
        self._stop_event = threading.Event()
        
        # Dashboard data
        self._dashboard_data = {
            'system': {},
            'application': {},
            'performance': {},
            'alerts': [],
            'last_updated': None
        }
        
        # Alert thresholds
        self.alert_thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'error_rate': 5.0,
            'response_time': 2.0
        }
        
        # Alert callbacks
        self._alert_callbacks: List[Callable[[Dict[str, Any]], None]] = []
    
    def start(self):
        """Start the monitoring dashboard"""
        if self._running:
            return
        
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
        logger.info(f"Monitoring dashboard started (update interval: {self.update_interval}s)")
    
    def stop(self):
        """Stop the monitoring dashboard"""
        if not self._running:
            return
        
        self._running = False
        self._stop_event.set()
        
        if self._thread:
            self._thread.join(timeout=10.0)
        
        logger.info("Monitoring dashboard stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running and not self._stop_event.is_set():
            try:
                self._update_dashboard_data()
                self._check_alerts()
            except Exception as e:
                logger.error(f"Error updating dashboard: {e}")
            
            # Wait for next update
            self._stop_event.wait(self.update_interval)
    
    def _update_dashboard_data(self):
        """Update dashboard data with current metrics"""
        # System metrics
        system_data = self._collect_system_metrics()
        
        # Application metrics
        app_data = self._collect_application_metrics()
        
        # Performance metrics
        perf_data = self._collect_performance_metrics()
        
        # Update dashboard data
        self._dashboard_data.update({
            'system': system_data,
            'application': app_data,
            'performance': perf_data,
            'last_updated': datetime.now().isoformat()
        })
        
        # Record metrics
        self._record_dashboard_metrics(system_data, app_data, perf_data)
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system-level metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk metrics
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Network metrics
            network_io = psutil.net_io_counters()
            
            # Process metrics
            process = psutil.Process(os.getpid())
            process_memory = process.memory_info()
            process_cpu = process.cpu_percent()
            
            return {
                'cpu': {
                    'usage_percent': cpu_percent,
                    'count': cpu_count,
                    'frequency_mhz': cpu_freq.current if cpu_freq else None
                },
                'memory': {
                    'total_mb': memory.total / 1024 / 1024,
                    'available_mb': memory.available / 1024 / 1024,
                    'used_mb': memory.used / 1024 / 1024,
                    'usage_percent': memory.percent,
                    'swap_total_mb': swap.total / 1024 / 1024,
                    'swap_used_mb': swap.used / 1024 / 1024,
                    'swap_percent': swap.percent
                },
                'disk': {
                    'total_gb': disk_usage.total / 1024 / 1024 / 1024,
                    'used_gb': disk_usage.used / 1024 / 1024 / 1024,
                    'free_gb': disk_usage.free / 1024 / 1024 / 1024,
                    'usage_percent': (disk_usage.used / disk_usage.total) * 100,
                    'read_bytes': disk_io.read_bytes if disk_io else 0,
                    'write_bytes': disk_io.write_bytes if disk_io else 0
                },
                'network': {
                    'bytes_sent': network_io.bytes_sent,
                    'bytes_recv': network_io.bytes_recv,
                    'packets_sent': network_io.packets_sent,
                    'packets_recv': network_io.packets_recv
                },
                'process': {
                    'cpu_percent': process_cpu,
                    'memory_rss_mb': process_memory.rss / 1024 / 1024,
                    'memory_vms_mb': process_memory.vms / 1024 / 1024,
                    'pid': process.pid,
                    'threads': process.num_threads()
                }
            }
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {}
    
    def _collect_application_metrics(self) -> Dict[str, Any]:
        """Collect application-specific metrics"""
        try:
            metrics_summary = self.metrics_collector.get_summary(duration_seconds=300)  # Last 5 minutes
            
            # Extract key application metrics
            videos_processed = self.metrics_collector.get_counter_value('app.videos_processed')
            errors_count = self.metrics_collector.get_counter_value('app.errors')
            cache_hits = self.metrics_collector.get_counter_value('app.cache_hits')
            cache_misses = self.metrics_collector.get_counter_value('app.cache_misses')
            
            # Calculate rates
            cache_hit_rate = 0.0
            if cache_hits + cache_misses > 0:
                cache_hit_rate = (cache_hits / (cache_hits + cache_misses)) * 100
            
            # Processing time statistics
            processing_time_stats = self.metrics_collector.get_timer_stats('app.processing_time')
            
            return {
                'videos_processed': videos_processed,
                'errors_count': errors_count,
                'cache_hits': cache_hits,
                'cache_misses': cache_misses,
                'cache_hit_rate_percent': cache_hit_rate,
                'processing_time': processing_time_stats,
                'active_metrics': len(metrics_summary.get('metrics', {})),
                'total_counters': len(metrics_summary.get('counters', {})),
                'total_gauges': len(metrics_summary.get('gauges', {}))
            }
        except Exception as e:
            logger.error(f"Error collecting application metrics: {e}")
            return {}
    
    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect performance metrics"""
        try:
            # Get performance monitor data
            perf_summary = self.performance_monitor.get_performance_summary()
            
            # Get recent performance data
            recent_metrics = self.metrics_collector.get_summary(duration_seconds=60)  # Last minute
            
            # Calculate performance indicators
            avg_response_time = 0.0
            error_rate = 0.0
            throughput = 0.0
            
            if 'timers' in recent_metrics:
                for timer_name, stats in recent_metrics['timers'].items():
                    if 'processing' in timer_name.lower() and stats.get('count', 0) > 0:
                        avg_response_time = stats.get('mean', 0.0)
                        throughput = stats.get('count', 0) / 60.0  # ops per second
                        break
            
            if recent_metrics.get('counters', {}).get('app.errors', 0) > 0:
                total_ops = sum(recent_metrics.get('counters', {}).values())
                if total_ops > 0:
                    error_rate = (recent_metrics['counters']['app.errors'] / total_ops) * 100
            
            return {
                'avg_response_time_seconds': avg_response_time,
                'error_rate_percent': error_rate,
                'throughput_ops_per_second': throughput,
                'performance_summary': perf_summary,
                'uptime_seconds': time.time() - self.performance_monitor.start_time
            }
        except Exception as e:
            logger.error(f"Error collecting performance metrics: {e}")
            return {}
    
    def _record_dashboard_metrics(self, system_data: Dict, app_data: Dict, perf_data: Dict):
        """Record dashboard metrics to metrics collector"""
        try:
            # Record system metrics
            if 'cpu' in system_data:
                self.metrics_collector.set_gauge('system.cpu_usage', system_data['cpu']['usage_percent'])
            
            if 'memory' in system_data:
                self.metrics_collector.set_gauge('system.memory_usage', system_data['memory']['usage_percent'])
            
            if 'disk' in system_data:
                self.metrics_collector.set_gauge('system.disk_usage', system_data['disk']['usage_percent'])
            
            # Record application metrics
            if 'cache_hit_rate_percent' in app_data:
                self.metrics_collector.set_gauge('app.cache_hit_rate', app_data['cache_hit_rate_percent'])
            
            # Record performance metrics
            if 'avg_response_time_seconds' in perf_data:
                self.metrics_collector.set_gauge('app.avg_response_time', perf_data['avg_response_time_seconds'])
            
            if 'error_rate_percent' in perf_data:
                self.metrics_collector.set_gauge('app.error_rate', perf_data['error_rate_percent'])
            
        except Exception as e:
            logger.error(f"Error recording dashboard metrics: {e}")
    
    def _check_alerts(self):
        """Check for alert conditions"""
        try:
            alerts = []
            current_time = datetime.now()
            
            system_data = self._dashboard_data.get('system', {})
            app_data = self._dashboard_data.get('application', {})
            perf_data = self._dashboard_data.get('performance', {})
            
            # CPU usage alert
            cpu_usage = system_data.get('cpu', {}).get('usage_percent', 0)
            if cpu_usage > self.alert_thresholds['cpu_usage']:
                alerts.append({
                    'type': 'cpu_high',
                    'severity': 'warning',
                    'message': f'High CPU usage: {cpu_usage:.1f}%',
                    'value': cpu_usage,
                    'threshold': self.alert_thresholds['cpu_usage'],
                    'timestamp': current_time.isoformat()
                })
            
            # Memory usage alert
            memory_usage = system_data.get('memory', {}).get('usage_percent', 0)
            if memory_usage > self.alert_thresholds['memory_usage']:
                alerts.append({
                    'type': 'memory_high',
                    'severity': 'warning',
                    'message': f'High memory usage: {memory_usage:.1f}%',
                    'value': memory_usage,
                    'threshold': self.alert_thresholds['memory_usage'],
                    'timestamp': current_time.isoformat()
                })
            
            # Disk usage alert
            disk_usage = system_data.get('disk', {}).get('usage_percent', 0)
            if disk_usage > self.alert_thresholds['disk_usage']:
                alerts.append({
                    'type': 'disk_high',
                    'severity': 'critical',
                    'message': f'High disk usage: {disk_usage:.1f}%',
                    'value': disk_usage,
                    'threshold': self.alert_thresholds['disk_usage'],
                    'timestamp': current_time.isoformat()
                })
            
            # Error rate alert
            error_rate = perf_data.get('error_rate_percent', 0)
            if error_rate > self.alert_thresholds['error_rate']:
                alerts.append({
                    'type': 'error_rate_high',
                    'severity': 'critical',
                    'message': f'High error rate: {error_rate:.1f}%',
                    'value': error_rate,
                    'threshold': self.alert_thresholds['error_rate'],
                    'timestamp': current_time.isoformat()
                })
            
            # Response time alert
            response_time = perf_data.get('avg_response_time_seconds', 0)
            if response_time > self.alert_thresholds['response_time']:
                alerts.append({
                    'type': 'response_time_high',
                    'severity': 'warning',
                    'message': f'High response time: {response_time:.2f}s',
                    'value': response_time,
                    'threshold': self.alert_thresholds['response_time'],
                    'timestamp': current_time.isoformat()
                })
            
            # Update alerts in dashboard data
            self._dashboard_data['alerts'] = alerts
            
            # Notify alert callbacks
            for alert in alerts:
                for callback in self._alert_callbacks:
                    try:
                        callback(alert)
                    except Exception as e:
                        logger.error(f"Error in alert callback: {e}")
            
            # Log critical alerts
            for alert in alerts:
                if alert['severity'] == 'critical':
                    logger.warning(f"ALERT: {alert['message']}")
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data"""
        return self._dashboard_data.copy()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status summary"""
        data = self.get_dashboard_data()
        
        system = data.get('system', {})
        app = data.get('application', {})
        perf = data.get('performance', {})
        alerts = data.get('alerts', [])
        
        # Determine overall status
        critical_alerts = [a for a in alerts if a['severity'] == 'critical']
        warning_alerts = [a for a in alerts if a['severity'] == 'warning']
        
        if critical_alerts:
            status = 'critical'
        elif warning_alerts:
            status = 'warning'
        else:
            status = 'healthy'
        
        return {
            'status': status,
            'uptime_seconds': perf.get('uptime_seconds', 0),
            'cpu_usage_percent': system.get('cpu', {}).get('usage_percent', 0),
            'memory_usage_percent': system.get('memory', {}).get('usage_percent', 0),
            'disk_usage_percent': system.get('disk', {}).get('usage_percent', 0),
            'videos_processed': app.get('videos_processed', 0),
            'error_count': app.get('errors_count', 0),
            'cache_hit_rate_percent': app.get('cache_hit_rate_percent', 0),
            'avg_response_time_seconds': perf.get('avg_response_time_seconds', 0),
            'alerts_count': len(alerts),
            'critical_alerts_count': len(critical_alerts),
            'warning_alerts_count': len(warning_alerts),
            'last_updated': data.get('last_updated')
        }
    
    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add alert callback"""
        self._alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Remove alert callback"""
        if callback in self._alert_callbacks:
            self._alert_callbacks.remove(callback)
    
    def set_alert_threshold(self, metric: str, threshold: float):
        """Set alert threshold for a metric"""
        if metric in self.alert_thresholds:
            self.alert_thresholds[metric] = threshold
            logger.info(f"Alert threshold for {metric} set to {threshold}")
        else:
            logger.warning(f"Unknown metric for alert threshold: {metric}")
    
    def export_dashboard_data(self, file_path: Path):
        """Export dashboard data to file"""
        data = self.get_dashboard_data()
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Dashboard data exported to {file_path}")
    
    def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        status = self.get_system_status()
        data = self.get_dashboard_data()
        
        # Calculate health scores
        cpu_score = max(0, 100 - status['cpu_usage_percent'])
        memory_score = max(0, 100 - status['memory_usage_percent'])
        disk_score = max(0, 100 - status['disk_usage_percent'])
        
        # Error rate score (inverse)
        error_rate = data.get('performance', {}).get('error_rate_percent', 0)
        error_score = max(0, 100 - (error_rate * 10))  # Scale error rate
        
        # Response time score
        response_time = status['avg_response_time_seconds']
        response_score = max(0, 100 - (response_time * 50))  # Scale response time
        
        # Overall health score
        health_score = (cpu_score + memory_score + disk_score + error_score + response_score) / 5
        
        return {
            'overall_health_score': health_score,
            'component_scores': {
                'cpu': cpu_score,
                'memory': memory_score,
                'disk': disk_score,
                'error_rate': error_score,
                'response_time': response_score
            },
            'system_status': status,
            'recommendations': self._generate_health_recommendations(status, data),
            'report_timestamp': datetime.now().isoformat()
        }
    
    def _generate_health_recommendations(self, status: Dict, data: Dict) -> List[str]:
        """Generate health recommendations"""
        recommendations = []
        
        # CPU recommendations
        if status['cpu_usage_percent'] > 80:
            recommendations.append("Consider optimizing CPU-intensive operations or scaling resources")
        
        # Memory recommendations
        if status['memory_usage_percent'] > 85:
            recommendations.append("Monitor memory usage and consider memory optimization")
        
        # Disk recommendations
        if status['disk_usage_percent'] > 90:
            recommendations.append("Clean up disk space or expand storage capacity")
        
        # Error rate recommendations
        error_rate = data.get('performance', {}).get('error_rate_percent', 0)
        if error_rate > 5:
            recommendations.append("Investigate and fix sources of errors")
        
        # Response time recommendations
        if status['avg_response_time_seconds'] > 2:
            recommendations.append("Optimize application performance to reduce response times")
        
        # Cache recommendations
        if status['cache_hit_rate_percent'] < 80:
            recommendations.append("Improve cache efficiency to reduce processing overhead")
        
        if not recommendations:
            recommendations.append("System is operating within normal parameters")
        
        return recommendations


# Global dashboard instance
_global_dashboard: Optional[MonitoringDashboard] = None


def get_monitoring_dashboard() -> MonitoringDashboard:
    """Get global monitoring dashboard instance"""
    global _global_dashboard
    if _global_dashboard is None:
        _global_dashboard = MonitoringDashboard()
    return _global_dashboard


def start_monitoring():
    """Start global monitoring"""
    get_monitoring_dashboard().start()


def stop_monitoring():
    """Stop global monitoring"""
    global _global_dashboard
    if _global_dashboard:
        _global_dashboard.stop()


def get_system_status() -> Dict[str, Any]:
    """Get current system status"""
    return get_monitoring_dashboard().get_system_status()


def get_health_report() -> Dict[str, Any]:
    """Get comprehensive health report"""
    return get_monitoring_dashboard().generate_health_report()