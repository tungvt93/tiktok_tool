#!/usr/bin/env python3
"""
Performance Optimization Script

Automated performance analysis and optimization for TikTok Video Processing Tool.
"""

import sys
import argparse
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """Performance optimization manager"""

    def __init__(self, project_root: Path = None):
        """
        Initialize performance optimizer.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root or Path(__file__).parent.parent
        self.results = {}

    def run_performance_analysis(self) -> Dict[str, Any]:
        """Run comprehensive performance analysis"""
        logger.info("Starting performance analysis...")

        results = {
            'timestamp': time.time(),
            'tests': {}
        }

        # Test video discovery performance
        results['tests']['video_discovery'] = self._test_video_discovery()

        # Test configuration loading performance
        results['tests']['config_loading'] = self._test_config_loading()

        # Test dependency injection performance
        results['tests']['dependency_injection'] = self._test_dependency_injection()

        # Test memory usage
        results['tests']['memory_usage'] = self._test_memory_usage()

        # Test CLI performance
        results['tests']['cli_performance'] = self._test_cli_performance()

        # Generate recommendations
        results['recommendations'] = self._generate_recommendations(results['tests'])

        self.results = results
        logger.info("Performance analysis completed")
        return results

    def _test_video_discovery(self) -> Dict[str, Any]:
        """Test video discovery performance"""
        logger.info("Testing video discovery performance...")

        # Create temporary test environment
        temp_dir = Path(tempfile.mkdtemp())

        try:
            # Create test video files
            video_counts = [10, 50, 100]
            results = {}

            for count in video_counts:
                # Create test videos
                video_dir = temp_dir / f"test_{count}"
                video_dir.mkdir()

                for i in range(count):
                    video_file = video_dir / f"video_{i:03d}.mp4"
                    video_file.write_bytes(b"fake video content" * 1000)

                # Test discovery performance
                start_time = time.time()

                # Import and test
                sys.path.insert(0, str(self.project_root))
                try:
                    from src.shared.config.config_loader import load_config
                    from main import ApplicationFactory
                    from src.application.use_cases.get_videos_use_case import GetVideosUseCase, GetVideosRequest

                    # Change to test directory
                    import os
                    original_cwd = Path.cwd()
                    os.chdir(temp_dir)

                    try:
                        config = load_config()
                        config.paths.input_dir = video_dir

                        factory = ApplicationFactory(config)
                        container = factory.create_container()

                        use_case = container.resolve(GetVideosUseCase)
                        request = GetVideosRequest(directory=video_dir)
                        response = use_case.execute(request)

                        discovery_time = time.time() - start_time

                        results[f"{count}_videos"] = {
                            'count': count,
                            'discovery_time': discovery_time,
                            'videos_per_second': count / discovery_time if discovery_time > 0 else 0,
                            'success': response.success,
                            'found_count': len(response.videos) if response.success else 0
                        }

                    finally:
                        os.chdir(original_cwd)

                except Exception as e:
                    results[f"{count}_videos"] = {
                        'count': count,
                        'error': str(e),
                        'success': False
                    }
                finally:
                    if str(self.project_root) in sys.path:
                        sys.path.remove(str(self.project_root))

            return {
                'test_name': 'video_discovery',
                'results': results,
                'summary': self._summarize_discovery_results(results)
            }

        finally:
            shutil.rmtree(temp_dir)

    def _test_config_loading(self) -> Dict[str, Any]:
        """Test configuration loading performance"""
        logger.info("Testing configuration loading performance...")

        try:
            sys.path.insert(0, str(self.project_root))

            from src.shared.config.config_loader import load_config

            # Test multiple config loads
            load_times = []
            for i in range(10):
                start_time = time.time()
                config = load_config()
                load_time = time.time() - start_time
                load_times.append(load_time)

            return {
                'test_name': 'config_loading',
                'load_times': load_times,
                'avg_load_time': sum(load_times) / len(load_times),
                'min_load_time': min(load_times),
                'max_load_time': max(load_times),
                'total_time': sum(load_times)
            }

        except Exception as e:
            return {
                'test_name': 'config_loading',
                'error': str(e),
                'success': False
            }
        finally:
            if str(self.project_root) in sys.path:
                sys.path.remove(str(self.project_root))

    def _test_dependency_injection(self) -> Dict[str, Any]:
        """Test dependency injection performance"""
        logger.info("Testing dependency injection performance...")

        try:
            sys.path.insert(0, str(self.project_root))

            from src.shared.config.config_loader import load_config
            from main import ApplicationFactory

            config = load_config()

            # Test container creation
            creation_times = []
            for i in range(5):
                start_time = time.time()
                factory = ApplicationFactory(config)
                container = factory.create_container()
                creation_time = time.time() - start_time
                creation_times.append(creation_time)

            # Test service resolution
            factory = ApplicationFactory(config)
            container = factory.create_container()

            resolution_times = {}
            services_to_test = [
                'GetVideosUseCase',
                'ProcessVideoUseCase',
                'VideoService',
                'ProcessingService',
                'EffectService'
            ]

            for service_name in services_to_test:
                try:
                    # Get service class
                    if service_name == 'GetVideosUseCase':
                        from src.application.use_cases.get_videos_use_case import GetVideosUseCase
                        service_class = GetVideosUseCase
                    elif service_name == 'ProcessVideoUseCase':
                        from src.application.use_cases.process_video_use_case import ProcessVideoUseCase
                        service_class = ProcessVideoUseCase
                    elif service_name == 'VideoService':
                        from src.application.services.video_service import VideoService
                        service_class = VideoService
                    elif service_name == 'ProcessingService':
                        from src.application.services.processing_service import ProcessingService
                        service_class = ProcessingService
                    elif service_name == 'EffectService':
                        from src.application.services.effect_service import EffectService
                        service_class = EffectService
                    else:
                        continue

                    start_time = time.time()
                    service = container.resolve(service_class)
                    resolution_time = time.time() - start_time

                    resolution_times[service_name] = {
                        'resolution_time': resolution_time,
                        'success': True
                    }

                except Exception as e:
                    resolution_times[service_name] = {
                        'error': str(e),
                        'success': False
                    }

            return {
                'test_name': 'dependency_injection',
                'container_creation': {
                    'times': creation_times,
                    'avg_time': sum(creation_times) / len(creation_times),
                    'min_time': min(creation_times),
                    'max_time': max(creation_times)
                },
                'service_resolution': resolution_times,
                'summary': {
                    'avg_creation_time': sum(creation_times) / len(creation_times),
                    'successful_resolutions': sum(1 for r in resolution_times.values() if r.get('success', False)),
                    'total_services_tested': len(services_to_test)
                }
            }

        except Exception as e:
            return {
                'test_name': 'dependency_injection',
                'error': str(e),
                'success': False
            }
        finally:
            if str(self.project_root) in sys.path:
                sys.path.remove(str(self.project_root))

    def _test_memory_usage(self) -> Dict[str, Any]:
        """Test memory usage patterns"""
        logger.info("Testing memory usage...")

        try:
            import psutil
            process = psutil.Process()

            # Get initial memory
            initial_memory = process.memory_info().rss

            # Test memory usage during operations
            sys.path.insert(0, str(self.project_root))

            from src.shared.config.config_loader import load_config
            from main import ApplicationFactory

            # Load config
            config = load_config()
            memory_after_config = process.memory_info().rss

            # Create container
            factory = ApplicationFactory(config)
            container = factory.create_container()
            memory_after_container = process.memory_info().rss

            # Resolve services
            from src.application.use_cases.get_videos_use_case import GetVideosUseCase
            use_case = container.resolve(GetVideosUseCase)
            memory_after_resolution = process.memory_info().rss

            return {
                'test_name': 'memory_usage',
                'initial_memory': initial_memory,
                'memory_after_config': memory_after_config,
                'memory_after_container': memory_after_container,
                'memory_after_resolution': memory_after_resolution,
                'memory_deltas': {
                    'config_loading': memory_after_config - initial_memory,
                    'container_creation': memory_after_container - memory_after_config,
                    'service_resolution': memory_after_resolution - memory_after_container,
                    'total_increase': memory_after_resolution - initial_memory
                },
                'memory_mb': {
                    'initial': initial_memory / 1024 / 1024,
                    'final': memory_after_resolution / 1024 / 1024,
                    'increase': (memory_after_resolution - initial_memory) / 1024 / 1024
                }
            }

        except Exception as e:
            return {
                'test_name': 'memory_usage',
                'error': str(e),
                'success': False
            }
        finally:
            if str(self.project_root) in sys.path:
                sys.path.remove(str(self.project_root))

    def _test_cli_performance(self) -> Dict[str, Any]:
        """Test CLI performance"""
        logger.info("Testing CLI performance...")

        try:
            import subprocess

            cli_tests = {
                'help': ['--help'],
                'config_info': ['--config-info'],
                'validate_config': ['--validate-config'],
                'cli_effects': ['--cli', 'effects'],
                'cli_list': ['--cli', 'list']
            }

            results = {}

            for test_name, args in cli_tests.items():
                try:
                    start_time = time.time()
                    result = subprocess.run(
                        [sys.executable, 'main.py'] + args,
                        cwd=self.project_root,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    execution_time = time.time() - start_time

                    results[test_name] = {
                        'execution_time': execution_time,
                        'return_code': result.returncode,
                        'success': result.returncode == 0,
                        'stdout_length': len(result.stdout),
                        'stderr_length': len(result.stderr)
                    }

                except subprocess.TimeoutExpired:
                    results[test_name] = {
                        'error': 'timeout',
                        'success': False
                    }
                except Exception as e:
                    results[test_name] = {
                        'error': str(e),
                        'success': False
                    }

            return {
                'test_name': 'cli_performance',
                'results': results,
                'summary': {
                    'successful_tests': sum(1 for r in results.values() if r.get('success', False)),
                    'total_tests': len(cli_tests),
                    'avg_execution_time': sum(
                        r.get('execution_time', 0)
                        for r in results.values()
                        if 'execution_time' in r
                    ) / len([r for r in results.values() if 'execution_time' in r])
                }
            }

        except Exception as e:
            return {
                'test_name': 'cli_performance',
                'error': str(e),
                'success': False
            }

    def _summarize_discovery_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize video discovery results"""
        successful_tests = [r for r in results.values() if r.get('success', False)]

        if not successful_tests:
            return {'error': 'No successful tests'}

        avg_time = sum(r['discovery_time'] for r in successful_tests) / len(successful_tests)
        avg_throughput = sum(r['videos_per_second'] for r in successful_tests) / len(successful_tests)

        return {
            'successful_tests': len(successful_tests),
            'avg_discovery_time': avg_time,
            'avg_throughput': avg_throughput,
            'performance_rating': self._rate_performance(avg_time, 'discovery')
        }

    def _rate_performance(self, value: float, test_type: str) -> str:
        """Rate performance based on value and test type"""
        if test_type == 'discovery':
            if value < 0.1:
                return 'excellent'
            elif value < 0.5:
                return 'good'
            elif value < 1.0:
                return 'fair'
            else:
                return 'poor'
        elif test_type == 'config':
            if value < 0.01:
                return 'excellent'
            elif value < 0.05:
                return 'good'
            elif value < 0.1:
                return 'fair'
            else:
                return 'poor'
        else:
            return 'unknown'

    def _generate_recommendations(self, test_results: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []

        # Video discovery recommendations
        if 'video_discovery' in test_results:
            discovery = test_results['video_discovery']
            if 'summary' in discovery:
                summary = discovery['summary']
                if summary.get('avg_discovery_time', 0) > 1.0:
                    recommendations.append(
                        "Video discovery is slow - consider implementing parallel file scanning"
                    )
                if summary.get('avg_throughput', 0) < 50:
                    recommendations.append(
                        "Low video discovery throughput - consider optimizing file system operations"
                    )

        # Configuration loading recommendations
        if 'config_loading' in test_results:
            config = test_results['config_loading']
            if config.get('avg_load_time', 0) > 0.1:
                recommendations.append(
                    "Configuration loading is slow - consider caching or optimizing config structure"
                )

        # Dependency injection recommendations
        if 'dependency_injection' in test_results:
            di = test_results['dependency_injection']
            if 'container_creation' in di:
                if di['container_creation'].get('avg_time', 0) > 0.5:
                    recommendations.append(
                        "Dependency injection container creation is slow - consider lazy loading"
                    )

        # Memory usage recommendations
        if 'memory_usage' in test_results:
            memory = test_results['memory_usage']
            if 'memory_mb' in memory:
                if memory['memory_mb'].get('increase', 0) > 100:
                    recommendations.append(
                        "High memory usage increase detected - consider memory optimization"
                    )

        # CLI performance recommendations
        if 'cli_performance' in test_results:
            cli = test_results['cli_performance']
            if 'summary' in cli:
                if cli['summary'].get('avg_execution_time', 0) > 2.0:
                    recommendations.append(
                        "CLI commands are slow - consider optimizing startup time"
                    )

        # General recommendations
        if not recommendations:
            recommendations.append("Performance appears to be within acceptable ranges")

        recommendations.append("Consider enabling profiling in production for ongoing monitoring")
        recommendations.append("Regular performance testing is recommended after code changes")

        return recommendations

    def save_results(self, file_path: Path):
        """Save performance analysis results"""
        with open(file_path, 'w') as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"Performance analysis results saved to {file_path}")

    def print_summary(self):
        """Print performance analysis summary"""
        if not self.results:
            print("No performance analysis results available")
            return

        print("\n" + "=" * 60)
        print("PERFORMANCE ANALYSIS SUMMARY")
        print("=" * 60)

        # Print test results
        for test_name, test_data in self.results.get('tests', {}).items():
            print(f"\n{test_name.upper().replace('_', ' ')}:")

            if 'error' in test_data:
                print(f"  ❌ Error: {test_data['error']}")
                continue

            if test_name == 'video_discovery' and 'summary' in test_data:
                summary = test_data['summary']
                print(f"  ✓ Average discovery time: {summary.get('avg_discovery_time', 0):.3f}s")
                print(f"  ✓ Average throughput: {summary.get('avg_throughput', 0):.1f} videos/sec")
                print(f"  ✓ Performance rating: {summary.get('performance_rating', 'unknown')}")

            elif test_name == 'config_loading':
                print(f"  ✓ Average load time: {test_data.get('avg_load_time', 0):.3f}s")
                print(f"  ✓ Min/Max: {test_data.get('min_load_time', 0):.3f}s / {test_data.get('max_load_time', 0):.3f}s")

            elif test_name == 'dependency_injection' and 'summary' in test_data:
                summary = test_data['summary']
                print(f"  ✓ Average container creation: {summary.get('avg_creation_time', 0):.3f}s")
                print(f"  ✓ Successful service resolutions: {summary.get('successful_resolutions', 0)}/{summary.get('total_services_tested', 0)}")

            elif test_name == 'memory_usage' and 'memory_mb' in test_data:
                memory = test_data['memory_mb']
                print(f"  ✓ Initial memory: {memory.get('initial', 0):.1f}MB")
                print(f"  ✓ Final memory: {memory.get('final', 0):.1f}MB")
                print(f"  ✓ Memory increase: {memory.get('increase', 0):.1f}MB")

            elif test_name == 'cli_performance' and 'summary' in test_data:
                summary = test_data['summary']
                print(f"  ✓ Successful tests: {summary.get('successful_tests', 0)}/{summary.get('total_tests', 0)}")
                print(f"  ✓ Average execution time: {summary.get('avg_execution_time', 0):.3f}s")

        # Print recommendations
        recommendations = self.results.get('recommendations', [])
        if recommendations:
            print(f"\nRECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")

        print("\n" + "=" * 60)


def main():
    """Main performance optimization script entry point"""
    parser = argparse.ArgumentParser(
        description="Analyze and optimize TikTok Video Processing Tool performance"
    )

    parser.add_argument(
        '--output', '-o', type=str, metavar='FILE',
        help='Save results to JSON file'
    )

    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--quick', action='store_true',
        help='Run quick performance tests only'
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create optimizer
    optimizer = PerformanceOptimizer()

    try:
        # Run performance analysis
        results = optimizer.run_performance_analysis()

        # Print summary
        optimizer.print_summary()

        # Save results if requested
        if args.output:
            output_path = Path(args.output)
            optimizer.save_results(output_path)

        # Determine exit code based on results
        has_errors = any(
            'error' in test_data
            for test_data in results.get('tests', {}).values()
        )

        return 1 if has_errors else 0

    except KeyboardInterrupt:
        print("\nPerformance analysis interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Performance analysis failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
