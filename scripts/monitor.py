#!/usr/bin/env python3
"""
Monitoring CLI Tool

Command-line interface for monitoring system and application metrics.
"""

import sys
import time
import json
import argparse
from pathlib import Path
from typing import Dict, Any
import signal
import threading

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure.services.monitoring_dashboard import get_monitoring_dashboard
from src.shared.utils.metrics_collector import get_metrics_collector, start_metrics_reporting
from src.shared.utils.logging_config import setup_logging

# Setup logging
import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

class MonitoringCLI:
    """Command-line monitoring interface"""
    
    def __init__(self):
        """Initialize monitoring CLI"""
        self.dashboard = get_monitoring_dashboard()
        self.metrics_collector = get_metrics_collector()
        self._running = False
        self._stop_event = threading.Event()
    
    def start_monitoring(self, interval: int = 5, duration: int = None):
        """Start real-time monitoring"""
        print("Starting monitoring dashboard...")
        
        # Start dashboard
        self.dashboard.start()
        start_metrics_reporting(interval)
        
        self._running = True
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            start_time = time.time()
            
            while self._running:
                # Clear screen
                print("\033[2J\033[H", end="")
                
                # Display monitoring data
                self._display_dashboard()
                
                # Check duration limit
                if duration and (time.time() - start_time) >= duration:
                    break
                
                # Wait for next update
                if self._stop_event.wait(interval):
                    break
                
        except KeyboardInterrupt:
            pass
        finally:
            self._cleanup()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\nShutting down monitoring...")
        self._running = False
        self._stop_event.set()
    
    def _cleanup(self):
        """Cleanup resources"""
        self.dashboard.stop()
        print("Monitoring stopped.")
    
    def _display_dashboard(self):
        """Display monitoring dashboard"""
        status = self.dashboard.get_system_status()
        data = self.dashboard.get_dashboard_data()
        
        # Header
        print("=" * 80)
        print(f"TikTok Video Tool - System Monitor")
        print(f"Status: {status['status'].upper()}")
        print(f"Last Updated: {status.get('last_updated', 'N/A')}")
        print("=" * 80)
        
        # System metrics
        print("\n📊 SYSTEM METRICS")
        print("-" * 40)
        system = data.get('system', {})
        
        if 'cpu' in system:
            cpu = system['cpu']
            print(f"CPU Usage:     {cpu.get('usage_percent', 0):6.1f}% ({cpu.get('count', 0)} cores)")
        
        if 'memory' in system:
            memory = system['memory']
            print(f"Memory Usage:  {memory.get('usage_percent', 0):6.1f}% ({memory.get('used_mb', 0):,.0f} MB used)")
        
        if 'disk' in system:
            disk = system['disk']
            print(f"Disk Usage:    {disk.get('usage_percent', 0):6.1f}% ({disk.get('used_gb', 0):,.1f} GB used)")
        
        if 'process' in system:
            process = system['process']
            print(f"Process CPU:   {process.get('cpu_percent', 0):6.1f}%")
            print(f"Process Memory:{process.get('memory_rss_mb', 0):6.1f} MB")
        
        # Application metrics
        print("\n🎬 APPLICATION METRICS")
        print("-" * 40)
        app = data.get('application', {})
        
        print(f"Videos Processed: {app.get('videos_processed', 0):,}")
        print(f"Errors:           {app.get('errors_count', 0):,}")
        print(f"Cache Hit Rate:   {app.get('cache_hit_rate_percent', 0):6.1f}%")
        print(f"Active Metrics:   {app.get('active_metrics', 0):,}")
        
        # Performance metrics
        print("\n⚡ PERFORMANCE METRICS")
        print("-" * 40)
        perf = data.get('performance', {})
        
        print(f"Avg Response Time: {perf.get('avg_response_time_seconds', 0):6.3f}s")
        print(f"Error Rate:        {perf.get('error_rate_percent', 0):6.2f}%")
        print(f"Throughput:        {perf.get('throughput_ops_per_second', 0):6.2f} ops/s")
        print(f"Uptime:            {self._format_uptime(perf.get('uptime_seconds', 0))}")
        
        # Alerts
        alerts = data.get('alerts', [])
        if alerts:
            print("\n🚨 ACTIVE ALERTS")
            print("-" * 40)
            for alert in alerts[-5:]:  # Show last 5 alerts
                severity_icon = "🔴" if alert['severity'] == 'critical' else "🟡"
                print(f"{severity_icon} {alert['message']}")
        else:
            print("\n✅ NO ACTIVE ALERTS")
        
        # Footer
        print("\n" + "=" * 80)
        print("Press Ctrl+C to stop monitoring")
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.0f}m {seconds%60:.0f}s"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours:.0f}h {minutes:.0f}m"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days:.0f}d {hours:.0f}h"
    
    def show_status(self):
        """Show current system status"""
        status = self.dashboard.get_system_status()
        
        print("System Status Summary")
        print("=" * 40)
        print(f"Overall Status: {status['status'].upper()}")
        print(f"CPU Usage:      {status['cpu_usage_percent']:.1f}%")
        print(f"Memory Usage:   {status['memory_usage_percent']:.1f}%")
        print(f"Disk Usage:     {status['disk_usage_percent']:.1f}%")
        print(f"Videos Processed: {status['videos_processed']:,}")
        print(f"Error Count:    {status['error_count']:,}")
        print(f"Cache Hit Rate: {status['cache_hit_rate_percent']:.1f}%")
        print(f"Avg Response:   {status['avg_response_time_seconds']:.3f}s")
        print(f"Active Alerts:  {status['alerts_count']}")
        print(f"Uptime:         {self._format_uptime(status['uptime_seconds'])}")
    
    def show_metrics(self, duration: int = 3600):
        """Show metrics summary"""
        summary = self.metrics_collector.get_summary(duration)
        
        print(f"Metrics Summary (Last {duration//60} minutes)")
        print("=" * 50)
        
        # Counters
        if summary.get('counters'):
            print("\nCounters:")
            for name, value in summary['counters'].items():
                print(f"  {name}: {value:,}")
        
        # Gauges
        if summary.get('gauges'):
            print("\nGauges:")
            for name, value in summary['gauges'].items():
                print(f"  {name}: {value:.2f}")
        
        # Timers
        if summary.get('timers'):
            print("\nTimers:")
            for name, stats in summary['timers'].items():
                if stats.get('count', 0) > 0:
                    print(f"  {name}:")
                    print(f"    Count: {stats['count']:,}")
                    print(f"    Mean:  {stats['mean']:.3f}s")
                    print(f"    Min:   {stats['min']:.3f}s")
                    print(f"    Max:   {stats['max']:.3f}s")
                    if 'p95' in stats:
                        print(f"    P95:   {stats['p95']:.3f}s")
    
    def show_health_report(self):
        """Show comprehensive health report"""
        report = self.dashboard.generate_health_report()
        
        print("System Health Report")
        print("=" * 50)
        print(f"Overall Health Score: {report['overall_health_score']:.1f}/100")
        print(f"Report Time: {report['report_timestamp']}")
        
        print("\nComponent Scores:")
        for component, score in report['component_scores'].items():
            status_icon = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"
            print(f"  {status_icon} {component.title()}: {score:.1f}/100")
        
        print("\nRecommendations:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"  {i}. {rec}")
    
    def export_data(self, output_file: str, format_type: str = "json"):
        """Export monitoring data"""
        output_path = Path(output_file)
        
        if format_type.lower() == "json":
            data = self.dashboard.get_dashboard_data()
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
        elif format_type.lower() == "metrics":
            metrics_data = self.metrics_collector.export_metrics("json")
            with open(output_path, 'w') as f:
                f.write(metrics_data)
        elif format_type.lower() == "prometheus":
            metrics_data = self.metrics_collector.export_metrics("prometheus")
            with open(output_path, 'w') as f:
                f.write(metrics_data)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
        
        print(f"Data exported to {output_path}")
    
    def test_alerts(self):
        """Test alert system"""
        print("Testing alert system...")
        
        # Add test alert callback
        def test_callback(alert):
            print(f"ALERT RECEIVED: {alert['message']} (Severity: {alert['severity']})")
        
        self.dashboard.add_alert_callback(test_callback)
        
        # Temporarily lower thresholds to trigger alerts
        original_thresholds = self.dashboard.alert_thresholds.copy()
        
        self.dashboard.set_alert_threshold('cpu_usage', 0.1)
        self.dashboard.set_alert_threshold('memory_usage', 0.1)
        
        # Start monitoring briefly
        self.dashboard.start()
        time.sleep(10)
        self.dashboard.stop()
        
        # Restore original thresholds
        self.dashboard.alert_thresholds = original_thresholds
        
        print("Alert test completed.")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="TikTok Video Tool Monitoring CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s monitor                    # Start real-time monitoring
  %(prog)s monitor --interval 10      # Monitor with 10s intervals
  %(prog)s status                     # Show current status
  %(prog)s metrics                    # Show metrics summary
  %(prog)s health                     # Show health report
  %(prog)s export data.json           # Export data to JSON
  %(prog)s export metrics.txt --format prometheus  # Export to Prometheus format
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Start real-time monitoring')
    monitor_parser.add_argument(
        '--interval', '-i', type=int, default=5,
        help='Update interval in seconds (default: 5)'
    )
    monitor_parser.add_argument(
        '--duration', '-d', type=int,
        help='Monitoring duration in seconds (default: unlimited)'
    )
    
    # Status command
    subparsers.add_parser('status', help='Show current system status')
    
    # Metrics command
    metrics_parser = subparsers.add_parser('metrics', help='Show metrics summary')
    metrics_parser.add_argument(
        '--duration', '-d', type=int, default=3600,
        help='Duration in seconds for metrics summary (default: 3600)'
    )
    
    # Health command
    subparsers.add_parser('health', help='Show comprehensive health report')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export monitoring data')
    export_parser.add_argument('output', help='Output file path')
    export_parser.add_argument(
        '--format', '-f', choices=['json', 'metrics', 'prometheus'],
        default='json', help='Export format (default: json)'
    )
    
    # Test command
    subparsers.add_parser('test-alerts', help='Test alert system')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Create CLI instance
    cli = MonitoringCLI()
    
    try:
        if args.command == 'monitor':
            cli.start_monitoring(args.interval, args.duration)
        elif args.command == 'status':
            cli.show_status()
        elif args.command == 'metrics':
            cli.show_metrics(args.duration)
        elif args.command == 'health':
            cli.show_health_report()
        elif args.command == 'export':
            cli.export_data(args.output, args.format)
        elif args.command == 'test-alerts':
            cli.test_alerts()
        
        return 0
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())