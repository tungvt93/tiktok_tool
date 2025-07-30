"""
Performance Monitor Service

Advanced performance monitoring and optimization service for video processing.
"""

import logging
import time
import threading
import psutil
import os
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import json

from ...shared.utils import get_logger, get_performance_logger
from ...shared.config import PerformanceConfig

logger = get_logger(__name__)
perf_logger = get_performance_logger()


@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    memory_available: float
    disk_usage: float
    network_io: Dict[str, float]
    temperature: Optional[float] = None
    gpu_usage: Optional[float] = None
    gpu_memory: Optional[float] = None


@dataclass
class ProcessingMetrics:
    """Video processing performance metrics"""
    job_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    input_size: int
    output_size: int
    effects_count: int
    success: bool
    error_message: Optional[str] = None
    system_metrics: Optional[SystemMetrics] = None


class PerformanceMonitor:
    """Advanced performance monitoring and optimization service"""

    def __init__(self, config: PerformanceConfig):
        """
        Initialize performance monitor.

        Args:
            config: Performance configuration
        """
        self.config = config
        self._is_monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._metrics_history: List[SystemMetrics] = []
        self._processing_history: List[ProcessingMetrics] = []
        self._callbacks: List[Callable[[SystemMetrics], None]] = []
        
        # Performance optimization
        self._optimization_enabled = config.enable_optimization
        self._memory_threshold = config.memory_threshold
        self._cpu_threshold = config.cpu_threshold
        
        # Metrics storage
        self._metrics_file = Path("logs/performance_metrics.json")
        self._metrics_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load historical data
        self._load_historical_metrics()
        
        logger.info(f"PerformanceMonitor initialized with optimization: {self._optimization_enabled}")

    def start_monitoring(self) -> None:
        """Start continuous performance monitoring"""
        if self._is_monitoring:
            logger.warning("Performance monitoring already started")
            return

        self._is_monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="PerformanceMonitor"
        )
        self._monitor_thread.start()
        logger.info("Performance monitoring started")

    def stop_monitoring(self) -> None:
        """Stop performance monitoring"""
        self._is_monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
        logger.info("Performance monitoring stopped")

    def add_callback(self, callback: Callable[[SystemMetrics], None]) -> None:
        """Add callback for metrics updates"""
        self._callbacks.append(callback)

    def get_current_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        return self._collect_system_metrics()

    def get_metrics_history(self, duration_minutes: int = 60) -> List[SystemMetrics]:
        """Get metrics history for specified duration"""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        return [m for m in self._metrics_history if m.timestamp >= cutoff_time]

    def get_processing_stats(self, duration_minutes: int = 60) -> Dict[str, Any]:
        """Get processing statistics for specified duration"""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        recent_jobs = [j for j in self._processing_history if j.start_time >= cutoff_time]
        
        if not recent_jobs:
            return {
                'total_jobs': 0,
                'success_rate': 0.0,
                'average_duration': 0.0,
                'total_processed_size': 0,
                'throughput': 0.0
            }
        
        completed_jobs = [j for j in recent_jobs if j.end_time is not None]
        successful_jobs = [j for j in completed_jobs if j.success]
        
        total_duration = sum(j.duration or 0 for j in completed_jobs)
        total_size = sum(j.output_size for j in completed_jobs)
        
        return {
            'total_jobs': len(recent_jobs),
            'completed_jobs': len(completed_jobs),
            'success_rate': (len(successful_jobs) / len(completed_jobs) * 100) if completed_jobs else 0.0,
            'average_duration': total_duration / len(completed_jobs) if completed_jobs else 0.0,
            'total_processed_size': total_size,
            'throughput': len(completed_jobs) / (duration_minutes / 60) if duration_minutes > 0 else 0.0,
            'effects_distribution': self._get_effects_distribution(recent_jobs)
        }

    def record_processing_job(self, job_id: str, input_size: int, effects_count: int) -> str:
        """Record start of processing job"""
        metrics = ProcessingMetrics(
            job_id=job_id,
            start_time=datetime.now(),
            input_size=input_size,
            effects_count=effects_count,
            output_size=0,
            success=False
        )
        self._processing_history.append(metrics)
        return job_id

    def complete_processing_job(self, job_id: str, output_size: int, success: bool, 
                               error_message: Optional[str] = None) -> None:
        """Record completion of processing job"""
        for job in self._processing_history:
            if job.job_id == job_id:
                job.end_time = datetime.now()
                job.duration = (job.end_time - job.start_time).total_seconds()
                job.output_size = output_size
                job.success = success
                job.error_message = error_message
                job.system_metrics = self.get_current_metrics()
                break

    def get_optimization_recommendations(self) -> List[str]:
        """Get performance optimization recommendations"""
        recommendations = []
        
        # Analyze recent metrics
        recent_metrics = self.get_metrics_history(30)  # Last 30 minutes
        if not recent_metrics:
            return ["No recent metrics available for analysis"]
        
        avg_cpu = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        
        # CPU recommendations
        if avg_cpu > 90:
            recommendations.append("⚠️ High CPU usage detected. Consider reducing concurrent jobs or upgrading CPU.")
        elif avg_cpu < 30:
            recommendations.append("💡 Low CPU usage. Consider increasing concurrent jobs for better throughput.")
        
        # Memory recommendations
        if avg_memory > 90:
            recommendations.append("⚠️ High memory usage detected. Consider reducing batch size or adding more RAM.")
        elif avg_memory < 50:
            recommendations.append("💡 Low memory usage. Consider increasing batch size for better efficiency.")
        
        # Processing recommendations
        stats = self.get_processing_stats(30)
        if stats['success_rate'] < 95:
            recommendations.append("⚠️ Low success rate detected. Check error logs and system stability.")
        
        if stats['average_duration'] > 300:  # 5 minutes
            recommendations.append("⚠️ Long processing times detected. Consider GPU acceleration or optimizing effects.")
        
        # System recommendations
        disk_usage = self._get_disk_usage()
        if disk_usage > 90:
            recommendations.append("⚠️ High disk usage. Clean up temporary files and output directory.")
        
        return recommendations

    def optimize_system(self) -> Dict[str, Any]:
        """Apply automatic system optimizations"""
        optimizations = {}
        
        if not self._optimization_enabled:
            return {"message": "Optimization disabled in configuration"}
        
        current_metrics = self.get_current_metrics()
        
        # Memory optimization
        if current_metrics.memory_usage > self._memory_threshold:
            freed_memory = self._optimize_memory()
            optimizations['memory_freed_mb'] = freed_memory
        
        # CPU optimization
        if current_metrics.cpu_usage > self._cpu_threshold:
            cpu_optimizations = self._optimize_cpu()
            optimizations['cpu_optimizations'] = cpu_optimizations
        
        # Disk optimization
        disk_usage = self._get_disk_usage()
        if disk_usage > 90:
            freed_space = self._cleanup_temp_files()
            optimizations['disk_freed_mb'] = freed_space
        
        return optimizations

    def export_metrics(self, output_path: Path) -> None:
        """Export metrics to JSON file"""
        try:
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'system_metrics': [asdict(m) for m in self._metrics_history[-1000:]],  # Last 1000 metrics
                'processing_metrics': [asdict(m) for m in self._processing_history[-1000:]],  # Last 1000 jobs
                'current_stats': self.get_processing_stats(60),
                'recommendations': self.get_optimization_recommendations()
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Metrics exported to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")

    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        logger.info("Performance monitoring loop started")
        
        while self._is_monitoring:
            try:
                # Collect current metrics
                metrics = self._collect_system_metrics()
                self._metrics_history.append(metrics)
                
                # Keep only recent history (last 24 hours)
                cutoff_time = datetime.now() - timedelta(hours=24)
                self._metrics_history = [m for m in self._metrics_history if m.timestamp >= cutoff_time]
                
                # Notify callbacks
                for callback in self._callbacks:
                    try:
                        callback(metrics)
                    except Exception as e:
                        logger.warning(f"Error in metrics callback: {e}")
                
                # Log performance data
                perf_logger.log_performance_metrics(
                    "system_metrics",
                    {
                        'cpu_usage': metrics.cpu_usage,
                        'memory_usage': metrics.memory_usage,
                        'disk_usage': metrics.disk_usage
                    }
                )
                
                # Apply automatic optimizations if enabled
                if self._optimization_enabled:
                    self._check_and_apply_optimizations(metrics)
                
                # Save metrics periodically
                if len(self._metrics_history) % 60 == 0:  # Every 60 samples (5 minutes)
                    self._save_metrics()
                
                time.sleep(5)  # Sample every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)  # Wait longer on error

    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            memory_available = memory.available / (1024 * 1024)  # MB
            
            # Disk usage
            disk_usage = self._get_disk_usage()
            
            # Network I/O
            network_io = self._get_network_io()
            
            # Temperature (if available)
            temperature = self._get_temperature()
            
            # GPU metrics (if available)
            gpu_usage, gpu_memory = self._get_gpu_metrics()
            
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                memory_available=memory_available,
                disk_usage=disk_usage,
                network_io=network_io,
                temperature=temperature,
                gpu_usage=gpu_usage,
                gpu_memory=gpu_memory
            )
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_usage=0.0,
                memory_usage=0.0,
                memory_available=0.0,
                disk_usage=0.0,
                network_io={'bytes_sent': 0.0, 'bytes_recv': 0.0}
            )

    def _get_disk_usage(self) -> float:
        """Get disk usage percentage"""
        try:
            disk = psutil.disk_usage('/')
            return (disk.used / disk.total) * 100
        except:
            return 0.0

    def _get_network_io(self) -> Dict[str, float]:
        """Get network I/O statistics"""
        try:
            net_io = psutil.net_io_counters()
            return {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv
            }
        except:
            return {'bytes_sent': 0.0, 'bytes_recv': 0.0}

    def _get_temperature(self) -> Optional[float]:
        """Get system temperature if available"""
        try:
            # Try to get CPU temperature (platform specific)
            if hasattr(psutil, 'sensors_temperatures'):
                temps = psutil.sensors_temperatures()
                if temps:
                    # Get first available temperature
                    for name, entries in temps.items():
                        if entries:
                            return entries[0].current
        except:
            pass
        return None

    def _get_gpu_metrics(self) -> tuple[Optional[float], Optional[float]]:
        """Get GPU usage and memory if available"""
        try:
            # Try to get GPU metrics using nvidia-ml-py or similar
            # This is a simplified implementation
            return None, None
        except:
            return None, None

    def _get_effects_distribution(self, jobs: List[ProcessingMetrics]) -> Dict[str, int]:
        """Get distribution of effects used in jobs"""
        distribution = {}
        for job in jobs:
            effects_key = f"{job.effects_count}_effects"
            distribution[effects_key] = distribution.get(effects_key, 0) + 1
        return distribution

    def _optimize_memory(self) -> float:
        """Optimize memory usage"""
        try:
            # Force garbage collection
            import gc
            gc.collect()
            
            # Clear some caches if memory is still high
            current_memory = psutil.virtual_memory().percent
            if current_memory > 90:
                # Clear some metrics history
                if len(self._metrics_history) > 1000:
                    self._metrics_history = self._metrics_history[-500:]
                
                # Clear some processing history
                if len(self._processing_history) > 1000:
                    self._processing_history = self._processing_history[-500:]
            
            return 0.0  # Placeholder for freed memory calculation
            
        except Exception as e:
            logger.error(f"Error optimizing memory: {e}")
            return 0.0

    def _optimize_cpu(self) -> List[str]:
        """Optimize CPU usage"""
        optimizations = []
        
        try:
            # Check for CPU-intensive processes
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    if proc.info['cpu_percent'] > 50:
                        optimizations.append(f"High CPU process: {proc.info['name']} ({proc.info['cpu_percent']:.1f}%)")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            logger.error(f"Error optimizing CPU: {e}")
        
        return optimizations

    def _cleanup_temp_files(self) -> float:
        """Clean up temporary files"""
        try:
            temp_dirs = ['temp', 'output', 'logs']
            freed_space = 0.0
            
            for temp_dir in temp_dirs:
                temp_path = Path(temp_dir)
                if temp_path.exists():
                    # Remove old temporary files (older than 1 hour)
                    cutoff_time = time.time() - 3600
                    for file_path in temp_path.rglob('*'):
                        if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                            try:
                                file_size = file_path.stat().st_size
                                file_path.unlink()
                                freed_space += file_size / (1024 * 1024)  # MB
                            except Exception as e:
                                logger.warning(f"Failed to remove temp file {file_path}: {e}")
            
            return freed_space
            
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")
            return 0.0

    def _check_and_apply_optimizations(self, metrics: SystemMetrics) -> None:
        """Check and apply automatic optimizations"""
        if metrics.memory_usage > self._memory_threshold:
            self._optimize_memory()
        
        if metrics.cpu_usage > self._cpu_threshold:
            self._optimize_cpu()

    def _save_metrics(self) -> None:
        """Save metrics to file"""
        try:
            # Save only recent metrics to avoid large files
            recent_metrics = self._metrics_history[-100:]  # Last 100 metrics
            recent_jobs = self._processing_history[-100:]  # Last 100 jobs
            
            data = {
                'timestamp': datetime.now().isoformat(),
                'system_metrics': [asdict(m) for m in recent_metrics],
                'processing_metrics': [asdict(m) for m in recent_jobs]
            }
            
            with open(self._metrics_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")

    def _load_historical_metrics(self) -> None:
        """Load historical metrics from file"""
        try:
            if self._metrics_file.exists():
                with open(self._metrics_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load system metrics
                if 'system_metrics' in data:
                    for metric_data in data['system_metrics']:
                        metric_data['timestamp'] = datetime.fromisoformat(metric_data['timestamp'])
                        self._metrics_history.append(SystemMetrics(**metric_data))
                
                # Load processing metrics
                if 'processing_metrics' in data:
                    for job_data in data['processing_metrics']:
                        job_data['start_time'] = datetime.fromisoformat(job_data['start_time'])
                        if job_data.get('end_time'):
                            job_data['end_time'] = datetime.fromisoformat(job_data['end_time'])
                        self._processing_history.append(ProcessingMetrics(**job_data))
                
                logger.info(f"Loaded {len(self._metrics_history)} system metrics and {len(self._processing_history)} processing jobs")
                
        except Exception as e:
            logger.warning(f"Failed to load historical metrics: {e}")
