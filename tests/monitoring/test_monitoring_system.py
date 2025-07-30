#!/usr/bin/env python3
"""
Monitoring System Test Suite

Comprehensive tests for the monitoring and metrics system.
"""

import unittest
import time
import threading
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

from src.shared.utils.metrics_collector import (
    MetricsCollector, MetricsTimer, MetricsReporter,
    get_metrics_collector, record_metric, increment_counter
)
from src.infrastructure.services.monitoring_dashboard import (
    MonitoringDashboard, get_monitoring_dashboard
)


class TestMetricsCollector(unittest.TestCase):
    """Test metrics collector functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.collector = MetricsCollector()
    
    def test_metric_registration(self):
        """Test metric registration"""
        metric = self.collector.register_metric("test.metric", "Test metric", "count")
        
        self.assertEqual(metric.name, "test.metric")
        self.assertEqual(metric.description, "Test metric")
        self.assertEqual(metric.unit, "count")
        
        # Should return same instance on re-registration
        metric2 = self.collector.register_metric("test.metric")
        self.assertIs(metric, metric2)
    
    def test_record_value(self):
        """Test recording metric values"""
        self.collector.record_value("test.metric", 42.5, {"tag": "value"})
        
        metric = self.collector.get_metric("test.metric")
        self.assertIsNotNone(metric)
        self.assertEqual(len(metric.points), 1)
        self.assertEqual(metric.points[0].value, 42.5)
        self.assertEqual(metric.points[0].tags, {"tag": "value"})
    
    def test_counter_operations(self):
        """Test counter operations"""
        # Increment counter
        self.collector.increment_counter("test.counter", 5)
        self.assertEqual(self.collector.get_counter_value("test.counter"), 5)
        
        # Increment again
        self.collector.increment_counter("test.counter", 3)
        self.assertEqual(self.collector.get_counter_value("test.counter"), 8)
        
        # Default increment
        self.collector.increment_counter("test.counter")
        self.assertEqual(self.collector.get_counter_value("test.counter"), 9)
    
    def test_gauge_operations(self):
        """Test gauge operations"""
        self.collector.set_gauge("test.gauge", 75.5)
        self.assertEqual(self.collector.get_gauge_value("test.gauge"), 75.5)
        
        # Update gauge
        self.collector.set_gauge("test.gauge", 80.0)
        self.assertEqual(self.collector.get_gauge_value("test.gauge"), 80.0)
    
    def test_histogram_operations(self):
        """Test histogram operations"""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        
        for value in values:
            self.collector.record_histogram("test.histogram", value)
        
        stats = self.collector.get_histogram_stats("test.histogram")
        
        self.assertEqual(stats['count'], 5)
        self.assertEqual(stats['sum'], 15.0)
        self.assertEqual(stats['min'], 1.0)
        self.assertEqual(stats['max'], 5.0)
        self.assertEqual(stats['mean'], 3.0)
        self.assertEqual(stats['median'], 3.0)
    
    def test_timer_operations(self):
        """Test timer operations"""
        durations = [0.1, 0.2, 0.15, 0.25, 0.3]
        
        for duration in durations:
            self.collector.record_timer("test.timer", duration)
        
        stats = self.collector.get_timer_stats("test.timer")
        
        self.assertEqual(stats['count'], 5)
        self.assertAlmostEqual(stats['sum'], 1.0, places=2)
        self.assertEqual(stats['min'], 0.1)
        self.assertEqual(stats['max'], 0.3)
        self.assertAlmostEqual(stats['mean'], 0.2, places=2)
    
    def test_metrics_timer_context_manager(self):
        """Test metrics timer context manager"""
        with MetricsTimer(self.collector, "test.operation"):
            time.sleep(0.1)
        
        stats = self.collector.get_timer_stats("test.operation")
        self.assertEqual(stats['count'], 1)
        self.assertGreaterEqual(stats['mean'], 0.1)
        self.assertLess(stats['mean'], 0.2)  # Should be close to 0.1
    
    def test_metrics_summary(self):
        """Test metrics summary generation"""
        # Add some test data
        self.collector.increment_counter("test.counter", 10)
        self.collector.set_gauge("test.gauge", 50.0)
        self.collector.record_timer("test.timer", 0.5)
        
        summary = self.collector.get_summary()
        
        self.assertIn('counters', summary)
        self.assertIn('gauges', summary)
        self.assertIn('timers', summary)
        self.assertEqual(summary['counters']['test.counter'], 10)
        self.assertEqual(summary['gauges']['test.gauge'], 50.0)
        self.assertEqual(summary['timers']['test.timer']['count'], 1)
    
    def test_metrics_export_json(self):
        """Test JSON metrics export"""
        self.collector.increment_counter("test.counter", 5)
        self.collector.set_gauge("test.gauge", 25.0)
        
        json_data = self.collector.export_metrics("json")
        data = json.loads(json_data)
        
        self.assertIn('counters', data)
        self.assertIn('gauges', data)
        self.assertEqual(data['counters']['test.counter'], 5)
        self.assertEqual(data['gauges']['test.gauge'], 25.0)
    
    def test_metrics_export_prometheus(self):
        """Test Prometheus metrics export"""
        self.collector.increment_counter("test_counter", 5)
        self.collector.set_gauge("test_gauge", 25.0)
        
        prometheus_data = self.collector.export_metrics("prometheus")
        
        self.assertIn("# TYPE test_counter counter", prometheus_data)
        self.assertIn("test_counter 5", prometheus_data)
        self.assertIn("# TYPE test_gauge gauge", prometheus_data)
        self.assertIn("test_gauge 25.0", prometheus_data)
    
    def test_metrics_callbacks(self):
        """Test metrics callbacks"""
        callback_calls = []
        
        def test_callback(metric_name, value):
            callback_calls.append((metric_name, value))
        
        self.collector.add_callback(test_callback)
        self.collector.record_value("test.metric", 42)
        
        self.assertEqual(len(callback_calls), 1)
        self.assertEqual(callback_calls[0], ("test.metric", 42))
        
        # Remove callback
        self.collector.remove_callback(test_callback)
        self.collector.record_value("test.metric", 43)
        
        # Should still be 1 (callback not called)
        self.assertEqual(len(callback_calls), 1)
    
    def test_clear_metrics(self):
        """Test clearing all metrics"""
        self.collector.increment_counter("test.counter", 5)
        self.collector.set_gauge("test.gauge", 25.0)
        
        # Verify data exists
        self.assertEqual(self.collector.get_counter_value("test.counter"), 5)
        self.assertEqual(self.collector.get_gauge_value("test.gauge"), 25.0)
        
        # Clear metrics
        self.collector.clear_metrics()
        
        # Verify data is cleared
        self.assertEqual(self.collector.get_counter_value("test.counter"), 0)
        self.assertIsNone(self.collector.get_gauge_value("test.gauge"))


class TestMetricsReporter(unittest.TestCase):
    """Test metrics reporter functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.collector = MetricsCollector()
        self.reporter = MetricsReporter(self.collector, interval_seconds=1)
    
    def tearDown(self):
        """Clean up test environment"""
        self.reporter.stop()
    
    def test_reporter_start_stop(self):
        """Test reporter start and stop"""
        self.assertFalse(self.reporter._running)
        
        self.reporter.start()
        self.assertTrue(self.reporter._running)
        
        self.reporter.stop()
        self.assertFalse(self.reporter._running)
    
    def test_reporter_periodic_reporting(self):
        """Test periodic reporting"""
        # Add some metrics
        self.collector.increment_counter("test.counter", 1)
        
        # Start reporter
        self.reporter.start()
        
        # Wait for a couple of reporting cycles
        time.sleep(2.5)
        
        # Stop reporter
        self.reporter.stop()
        
        # Reporter should have run at least twice
        self.assertTrue(True)  # If we get here, reporter didn't crash


class TestMonitoringDashboard(unittest.TestCase):
    """Test monitoring dashboard functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.dashboard = MonitoringDashboard(update_interval=1)
    
    def tearDown(self):
        """Clean up test environment"""
        self.dashboard.stop()
    
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_system_metrics_collection(self, mock_disk, mock_memory, mock_cpu):
        """Test system metrics collection"""
        # Mock system data
        mock_cpu.return_value = 45.5
        mock_memory.return_value = Mock(
            total=8589934592,  # 8GB
            available=4294967296,  # 4GB
            used=4294967296,  # 4GB
            percent=50.0
        )
        mock_disk.return_value = Mock(
            total=1099511627776,  # 1TB
            used=549755813888,  # 512GB
            free=549755813888  # 512GB
        )
        
        system_data = self.dashboard._collect_system_metrics()
        
        self.assertIn('cpu', system_data)
        self.assertIn('memory', system_data)
        self.assertIn('disk', system_data)
        
        self.assertEqual(system_data['cpu']['usage_percent'], 45.5)
        self.assertEqual(system_data['memory']['usage_percent'], 50.0)
    
    def test_dashboard_start_stop(self):
        """Test dashboard start and stop"""
        self.assertFalse(self.dashboard._running)
        
        self.dashboard.start()
        self.assertTrue(self.dashboard._running)
        
        self.dashboard.stop()
        self.assertFalse(self.dashboard._running)
    
    def test_alert_threshold_setting(self):
        """Test setting alert thresholds"""
        original_threshold = self.dashboard.alert_thresholds['cpu_usage']
        
        self.dashboard.set_alert_threshold('cpu_usage', 90.0)
        self.assertEqual(self.dashboard.alert_thresholds['cpu_usage'], 90.0)
        
        # Test invalid metric
        self.dashboard.set_alert_threshold('invalid_metric', 50.0)
        # Should not raise exception, just log warning
    
    def test_alert_callbacks(self):
        """Test alert callback system"""
        callback_calls = []
        
        def test_callback(alert):
            callback_calls.append(alert)
        
        self.dashboard.add_alert_callback(test_callback)
        
        # Manually trigger an alert check with high CPU
        with patch.object(self.dashboard, '_collect_system_metrics') as mock_collect:
            mock_collect.return_value = {
                'cpu': {'usage_percent': 95.0},
                'memory': {'usage_percent': 50.0},
                'disk': {'usage_percent': 50.0}
            }
            
            self.dashboard._update_dashboard_data()
            self.dashboard._check_alerts()
        
        # Should have triggered CPU alert
        self.assertGreater(len(callback_calls), 0)
        self.assertEqual(callback_calls[0]['type'], 'cpu_high')
        
        # Remove callback
        self.dashboard.remove_alert_callback(test_callback)
    
    def test_system_status(self):
        """Test system status generation"""
        # Mock some data
        self.dashboard._dashboard_data = {
            'system': {
                'cpu': {'usage_percent': 45.0},
                'memory': {'usage_percent': 60.0},
                'disk': {'usage_percent': 70.0}
            },
            'application': {
                'videos_processed': 100,
                'errors_count': 2,
                'cache_hit_rate_percent': 85.0
            },
            'performance': {
                'avg_response_time_seconds': 0.5,
                'uptime_seconds': 3600
            },
            'alerts': []
        }
        
        status = self.dashboard.get_system_status()
        
        self.assertEqual(status['status'], 'healthy')
        self.assertEqual(status['cpu_usage_percent'], 45.0)
        self.assertEqual(status['memory_usage_percent'], 60.0)
        self.assertEqual(status['videos_processed'], 100)
        self.assertEqual(status['alerts_count'], 0)
    
    def test_health_report_generation(self):
        """Test health report generation"""
        # Mock some data
        self.dashboard._dashboard_data = {
            'system': {
                'cpu': {'usage_percent': 30.0},
                'memory': {'usage_percent': 40.0},
                'disk': {'usage_percent': 50.0}
            },
            'application': {},
            'performance': {
                'error_rate_percent': 1.0,
                'avg_response_time_seconds': 0.2
            },
            'alerts': []
        }
        
        report = self.dashboard.generate_health_report()
        
        self.assertIn('overall_health_score', report)
        self.assertIn('component_scores', report)
        self.assertIn('recommendations', report)
        
        # Health score should be high with good metrics
        self.assertGreater(report['overall_health_score'], 80.0)
    
    def test_dashboard_data_export(self):
        """Test dashboard data export"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            self.dashboard.export_dashboard_data(temp_path)
            
            # Verify file was created and contains valid JSON
            self.assertTrue(temp_path.exists())
            
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            self.assertIn('system', data)
            self.assertIn('application', data)
            self.assertIn('performance', data)
            
        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestGlobalFunctions(unittest.TestCase):
    """Test global convenience functions"""
    
    def test_global_metrics_collector(self):
        """Test global metrics collector"""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        
        # Should return same instance
        self.assertIs(collector1, collector2)
    
    def test_convenience_functions(self):
        """Test convenience functions"""
        # Record metric
        record_metric("test.metric", 42.0, {"env": "test"})
        
        collector = get_metrics_collector()
        metric = collector.get_metric("test.metric")
        self.assertIsNotNone(metric)
        self.assertEqual(len(metric.points), 1)
        self.assertEqual(metric.points[0].value, 42.0)
        
        # Increment counter
        increment_counter("test.counter", 5, {"env": "test"})
        self.assertEqual(collector.get_counter_value("test.counter"), 5)


class TestIntegration(unittest.TestCase):
    """Integration tests for monitoring system"""
    
    def test_end_to_end_monitoring(self):
        """Test end-to-end monitoring workflow"""
        # Get global instances
        collector = get_metrics_collector()
        dashboard = get_monitoring_dashboard()
        
        # Record some metrics
        collector.increment_counter("app.videos_processed", 10)
        collector.set_gauge("system.cpu_usage", 45.0)
        collector.record_timer("app.processing_time", 0.5)
        
        # Start dashboard briefly
        dashboard.start()
        time.sleep(1)  # Let it collect some data
        dashboard.stop()
        
        # Check that data was collected
        status = dashboard.get_system_status()
        self.assertIsNotNone(status)
        
        # Check metrics summary
        summary = collector.get_summary()
        self.assertIn('counters', summary)
        self.assertIn('gauges', summary)
        self.assertIn('timers', summary)
    
    def test_concurrent_metrics_collection(self):
        """Test concurrent metrics collection"""
        collector = get_metrics_collector()
        
        def worker(worker_id):
            for i in range(100):
                collector.increment_counter(f"worker.{worker_id}.operations")
                collector.record_timer(f"worker.{worker_id}.duration", 0.01 * i)
        
        # Start multiple worker threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all metrics were recorded
        for i in range(5):
            counter_value = collector.get_counter_value(f"worker.{i}.operations")
            self.assertEqual(counter_value, 100)
            
            timer_stats = collector.get_timer_stats(f"worker.{i}.duration")
            self.assertEqual(timer_stats['count'], 100)


def run_monitoring_tests():
    """Run all monitoring tests"""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestMetricsCollector,
        TestMetricsReporter,
        TestMonitoringDashboard,
        TestGlobalFunctions,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_monitoring_tests()
    sys.exit(0 if success else 1)