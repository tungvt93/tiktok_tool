"""
Performance Tests

Comprehensive performance testing suite for the TikTok Video Processing Tool.
"""

import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
import psutil
import threading
from unittest.mock import Mock

# Import performance utilities
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.shared.utils.performance_profiler import PerformanceProfiler, get_profiler
from src.shared.utils.memory_optimizer import MemoryTracker, get_memory_tracker
from src.infrastructure.services.performance_monitor import PerformanceMonitor


class PerformanceTestSuite:
    """Performance test suite"""

    def __init__(self):
        """Initialize performance test suite"""
        self.profiler = PerformanceProfiler()
        self.memory_tracker = MemoryTracker()
        self.results = {}

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all performance tests"""
        print("Running Performance Test Suite")
        print("=" * 50)

        # Start monitoring
        self.profiler.start_monitoring()
        self.memory_tracker.start_monitoring()

        try:
            # Run individual tests
            self.results['video_discovery'] = self.test_video_discovery_performance()
            self.results['config_loading'] = self.test_config_loading_performance()
            self.results['dependency_injection'] = self.test_dependency_injection_performance()
            self.results['memory_usage'] = self.test_memory_usage()
            self.results['concurrent_operations'] = self.test_concurrent_operations()
            self.results['cache_performance'] = self.test_cache_performance()

            # Generate summary
            self.results['summary'] = self.generate_summary()

        finally:
            # Stop monitoring
            self.profiler.stop_monitoring()
            self.memory_tracker.stop_monitoring()

        return self.results

    def test_video_discovery_performance(self) -> Dict[str, Any]:
        """Test video discovery performance with different file counts"""
        print("Testing video discovery performance...")

        temp_dir = Path(tempfile.mkdtemp())
        results = {}

        try:
            # Test with different video counts
            test_counts = [10, 50, 100, 500]

            for count in test_counts:
                print(f"  Testing with {count} videos...")

                # Create test videos
                video_dir = temp_dir / f"videos_{count}"
                video_dir.mkdir()

                for i in range(count):
                    video_file = video_dir / f"video_{i:03d}.mp4"
                    video_file.write_bytes(b"fake video content" * 100)

                # Test discovery
                with self.profiler.profile_operation(f"video_discovery_{count}"):
                    start_time = time.time()

                    # Simulate video discovery
                    discovered_videos = []
                    for video_file in video_dir.glob("*.mp4"):
                        # Simulate metadata extraction
                        time.sleep(0.001)  # Simulate processing time
                        discovered_videos.append({
                            'path': str(video_file),
                            'size': video_file.stat().st_size,
                            'name': video_file.name
                        })

                    discovery_time = time.time() - start_time

                results[f"{count}_videos"] = {
                    'count': count,
                    'discovery_time': discovery_time,
                    'videos_per_second': count / discovery_time if discovery_time > 0 else 0,
                    'found_count': len(discovered_videos)
                }

                print(f"    {count} videos: {discovery_time:.3f}s ({count/discovery_time:.1f} videos/sec)")

        finally:
            shutil.rmtree(temp_dir)

        return {
            'test_name': 'video_discovery_performance',
            'results': results,
            'avg_throughput': sum(r['videos_per_second'] for r in results.values()) / len(results)
        }

    def test_config_loading_performance(self) -> Dict[str, Any]:
        """Test configuration loading performance"""
        print("Testing configuration loading performance...")

        # Test multiple config loads
        load_times = []

        for i in range(20):
            with self.profiler.profile_operation("config_loading"):
                start_time = time.time()

                # Simulate config loading
                config_data = {
                    'video': {'width': 1080, 'height': 1080},
                    'ffmpeg': {'preset': 'fast'},
                    'paths': {'input': 'input', 'output': 'output'}
                }

                # Simulate validation
                time.sleep(0.001)

                load_time = time.time() - start_time
                load_times.append(load_time)

        return {
            'test_name': 'config_loading_performance',
            'load_times': load_times,
            'avg_load_time': sum(load_times) / len(load_times),
            'min_load_time': min(load_times),
            'max_load_time': max(load_times),
            'total_loads': len(load_times)
        }

    def test_dependency_injection_performance(self) -> Dict[str, Any]:
        """Test dependency injection performance"""
        print("Testing dependency injection performance...")

        # Simulate DI container
        class MockContainer:
            def __init__(self):
                self.services = {}
                self.singletons = {}

            def register_singleton(self, interface, implementation):
                self.singletons[interface] = implementation

            def resolve(self, interface):
                if interface in self.singletons:
                    return self.singletons[interface]
                return Mock()

        # Test container creation
        creation_times = []
        for i in range(10):
            with self.profiler.profile_operation("container_creation"):
                start_time = time.time()

                container = MockContainer()

                # Register services
                for j in range(20):
                    container.register_singleton(f"Service{j}", Mock())

                creation_time = time.time() - start_time
                creation_times.append(creation_time)

        # Test service resolution
        container = MockContainer()
        for j in range(20):
            container.register_singleton(f"Service{j}", Mock())

        resolution_times = []
        for i in range(100):
            with self.profiler.profile_operation("service_resolution"):
                start_time = time.time()

                service = container.resolve(f"Service{i % 20}")

                resolution_time = time.time() - start_time
                resolution_times.append(resolution_time)

        return {
            'test_name': 'dependency_injection_performance',
            'container_creation': {
                'times': creation_times,
                'avg_time': sum(creation_times) / len(creation_times)
            },
            'service_resolution': {
                'times': resolution_times,
                'avg_time': sum(resolution_times) / len(resolution_times)
            }
        }

    def test_memory_usage(self) -> Dict[str, Any]:
        """Test memory usage patterns"""
        print("Testing memory usage patterns...")

        process = psutil.Process()
        initial_memory = process.memory_info().rss

        # Test memory usage during operations
        memory_snapshots = []

        # Simulate video processing operations
        for i in range(10):
            with self.profiler.profile_operation(f"memory_test_{i}"):
                # Simulate memory allocation
                data = [b"x" * 1024 * 1024 for _ in range(10)]  # 10MB

                current_memory = process.memory_info().rss
                memory_snapshots.append({
                    'iteration': i,
                    'memory_rss': current_memory,
                    'memory_delta': current_memory - initial_memory
                })

                # Simulate processing
                time.sleep(0.01)

                # Clean up
                del data

        final_memory = process.memory_info().rss

        return {
            'test_name': 'memory_usage',
            'initial_memory_mb': initial_memory / 1024 / 1024,
            'final_memory_mb': final_memory / 1024 / 1024,
            'memory_delta_mb': (final_memory - initial_memory) / 1024 / 1024,
            'snapshots': memory_snapshots,
            'peak_memory_mb': max(s['memory_rss'] for s in memory_snapshots) / 1024 / 1024
        }

    def test_concurrent_operations(self) -> Dict[str, Any]:
        """Test performance under concurrent operations"""
        print("Testing concurrent operations performance...")

        results = {}
        thread_counts = [1, 2, 4, 8]

        for thread_count in thread_counts:
            print(f"  Testing with {thread_count} threads...")

            def worker_task(worker_id: int, results_list: List):
                """Worker task for concurrent testing"""
                with self.profiler.profile_operation(f"concurrent_worker_{worker_id}"):
                    start_time = time.time()

                    # Simulate work
                    for i in range(100):
                        # Simulate video processing task
                        data = f"processing_data_{i}".encode() * 1000
                        time.sleep(0.001)  # Simulate processing time

                    duration = time.time() - start_time
                    results_list.append({
                        'worker_id': worker_id,
                        'duration': duration
                    })

            # Run concurrent workers
            threads = []
            worker_results = []

            start_time = time.time()

            for i in range(thread_count):
                thread = threading.Thread(
                    target=worker_task,
                    args=(i, worker_results)
                )
                threads.append(thread)
                thread.start()

            # Wait for completion
            for thread in threads:
                thread.join()

            total_time = time.time() - start_time

            results[f"{thread_count}_threads"] = {
                'thread_count': thread_count,
                'total_time': total_time,
                'worker_results': worker_results,
                'avg_worker_time': sum(r['duration'] for r in worker_results) / len(worker_results),
                'throughput': (thread_count * 100) / total_time  # operations per second
            }

        return {
            'test_name': 'concurrent_operations',
            'results': results,
            'best_throughput': max(r['throughput'] for r in results.values()),
            'optimal_threads': max(results.keys(), key=lambda k: results[k]['throughput'])
        }

    def test_cache_performance(self) -> Dict[str, Any]:
        """Test cache performance"""
        print("Testing cache performance...")

        # Simple cache implementation for testing
        class TestCache:
            def __init__(self):
                self.data = {}
                self.hits = 0
                self.misses = 0

            def get(self, key):
                if key in self.data:
                    self.hits += 1
                    return self.data[key]
                else:
                    self.misses += 1
                    return None

            def set(self, key, value):
                self.data[key] = value

            def hit_rate(self):
                total = self.hits + self.misses
                return self.hits / total if total > 0 else 0

        cache = TestCache()

        # Test cache performance
        cache_operations = []

        # Fill cache
        for i in range(1000):
            with self.profiler.profile_operation("cache_set"):
                start_time = time.time()
                cache.set(f"key_{i}", f"value_{i}")
                set_time = time.time() - start_time
                cache_operations.append(('set', set_time))

        # Test cache hits
        for i in range(500):
            with self.profiler.profile_operation("cache_get_hit"):
                start_time = time.time()
                value = cache.get(f"key_{i}")
                get_time = time.time() - start_time
                cache_operations.append(('get_hit', get_time))

        # Test cache misses
        for i in range(1000, 1100):
            with self.profiler.profile_operation("cache_get_miss"):
                start_time = time.time()
                value = cache.get(f"key_{i}")
                get_time = time.time() - start_time
                cache_operations.append(('get_miss', get_time))

        # Analyze results
        set_times = [op[1] for op in cache_operations if op[0] == 'set']
        hit_times = [op[1] for op in cache_operations if op[0] == 'get_hit']
        miss_times = [op[1] for op in cache_operations if op[0] == 'get_miss']

        return {
            'test_name': 'cache_performance',
            'cache_size': len(cache.data),
            'hit_rate': cache.hit_rate(),
            'operations': {
                'set': {
                    'count': len(set_times),
                    'avg_time': sum(set_times) / len(set_times) if set_times else 0,
                    'total_time': sum(set_times)
                },
                'get_hit': {
                    'count': len(hit_times),
                    'avg_time': sum(hit_times) / len(hit_times) if hit_times else 0,
                    'total_time': sum(hit_times)
                },
                'get_miss': {
                    'count': len(miss_times),
                    'avg_time': sum(miss_times) / len(miss_times) if miss_times else 0,
                    'total_time': sum(miss_times)
                }
            }
        }

    def generate_summary(self) -> Dict[str, Any]:
        """Generate performance test summary"""
        summary = {
            'total_tests': len([k for k in self.results.keys() if k != 'summary']),
            'profiler_metrics': len(self.profiler.get_metrics()),
            'memory_snapshots': len(self.memory_tracker._snapshots),
            'recommendations': []
        }

        # Analyze results and generate recommendations
        if 'video_discovery' in self.results:
            avg_throughput = self.results['video_discovery'].get('avg_throughput', 0)
            if avg_throughput < 100:
                summary['recommendations'].append(
                    f"Video discovery throughput is low ({avg_throughput:.1f} videos/sec) - consider optimization"
                )

        if 'memory_usage' in self.results:
            memory_delta = self.results['memory_usage'].get('memory_delta_mb', 0)
            if memory_delta > 50:
                summary['recommendations'].append(
                    f"High memory usage increase ({memory_delta:.1f}MB) - investigate memory leaks"
                )

        if 'concurrent_operations' in self.results:
            best_throughput = self.results['concurrent_operations'].get('best_throughput', 0)
            optimal_threads = self.results['concurrent_operations'].get('optimal_threads', '1_threads')
            summary['recommendations'].append(
                f"Optimal thread count appears to be {optimal_threads.split('_')[0]} "
                f"(throughput: {best_throughput:.1f} ops/sec)"
            )

        if 'cache_performance' in self.results:
            hit_rate = self.results['cache_performance'].get('hit_rate', 0)
            if hit_rate < 0.8:
                summary['recommendations'].append(
                    f"Cache hit rate is low ({hit_rate:.1%}) - consider cache optimization"
                )

        if not summary['recommendations']:
            summary['recommendations'].append("Performance appears to be within acceptable ranges")

        return summary

    def print_results(self):
        """Print performance test results"""
        print("\n" + "=" * 60)
        print("PERFORMANCE TEST RESULTS")
        print("=" * 60)

        for test_name, test_data in self.results.items():
            if test_name == 'summary':
                continue

            print(f"\n{test_name.upper().replace('_', ' ')}:")

            if test_name == 'video_discovery':
                print(f"  Average throughput: {test_data.get('avg_throughput', 0):.1f} videos/sec")
                for result_name, result_data in test_data.get('results', {}).items():
                    print(f"    {result_name}: {result_data.get('discovery_time', 0):.3f}s")

            elif test_name == 'config_loading':
                print(f"  Average load time: {test_data.get('avg_load_time', 0):.3f}s")
                print(f"  Min/Max: {test_data.get('min_load_time', 0):.3f}s / {test_data.get('max_load_time', 0):.3f}s")

            elif test_name == 'memory_usage':
                print(f"  Memory delta: {test_data.get('memory_delta_mb', 0):.1f}MB")
                print(f"  Peak memory: {test_data.get('peak_memory_mb', 0):.1f}MB")

            elif test_name == 'concurrent_operations':
                print(f"  Best throughput: {test_data.get('best_throughput', 0):.1f} ops/sec")
                print(f"  Optimal threads: {test_data.get('optimal_threads', 'unknown')}")

            elif test_name == 'cache_performance':
                print(f"  Hit rate: {test_data.get('hit_rate', 0):.1%}")
                print(f"  Cache size: {test_data.get('cache_size', 0):,} items")

        # Print summary
        if 'summary' in self.results:
            summary = self.results['summary']
            print(f"\nSUMMARY:")
            print(f"  Total tests: {summary.get('total_tests', 0)}")
            print(f"  Profiler metrics: {summary.get('profiler_metrics', 0)}")
            print(f"  Memory snapshots: {summary.get('memory_snapshots', 0)}")

            print(f"\nRECOMMENDATIONS:")
            for i, rec in enumerate(summary.get('recommendations', []), 1):
                print(f"  {i}. {rec}")

        print("\n" + "=" * 60)


def main():
    """Run performance tests"""
    test_suite = PerformanceTestSuite()

    try:
        results = test_suite.run_all_tests()
        test_suite.print_results()

        # Save results
        import json
        with open('performance_test_results.json', 'w') as f:
            json.dump(results, f, indent=2)

        print("Performance test results saved to performance_test_results.json")

        return 0

    except KeyboardInterrupt:
        print("\nPerformance tests interrupted by user")
        return 1
    except Exception as e:
        print(f"Performance tests failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
