"""
Main Application Entry Point

Bootstrap application with dependency injection and clean architecture.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional, List
import logging

from src.shared.config.config_loader import load_config
from src.shared.config.dependency_injection import create_container
from src.shared.utils.logging_config import setup_logging
from src.shared.utils.logging_config import get_logger
from src.shared.exceptions.base_exceptions import VideoProcessingException

# Import type hints for better code documentation
from src.application.services.video_service import VideoService
from src.application.services.processing_service import ProcessingService
from src.application.services.effect_service import EffectService
from src.application.use_cases.get_videos_use_case import GetVideosUseCase
from src.application.use_cases.process_video_use_case import ProcessVideoUseCase
from src.application.use_cases.create_processing_job_use_case import CreateProcessingJobUseCase
from src.infrastructure.services.ffmpeg_service import FFmpegService
from src.infrastructure.repositories.file_repository import FileRepository
from src.infrastructure.repositories.video_repository import VideoRepository

logger = get_logger(__name__)


class ApplicationFactory:
    """Factory for creating application instances with proper dependency injection"""

    def __init__(self, config):
        """
        Initialize application factory.

        Args:
            config: Application configuration
        """
        self.config = config
        self.container = None

    def create_container(self):
        """Create and configure dependency injection container"""
        if self.container is not None:
            return self.container

        self.container = create_container(self.config)
        self._register_infrastructure_services()
        self._register_application_services()
        self._register_use_cases()

        logger.info("Dependency injection container configured successfully")
        return self.container

    def _register_infrastructure_services(self):
        """Register infrastructure layer services"""
        from src.infrastructure.services.cache_service import CacheService
        from src.infrastructure.services.ffmpeg_service import FFmpegService
        from src.infrastructure.repositories.file_repository import FileRepository
        from src.infrastructure.repositories.video_repository import VideoRepository
        from src.infrastructure.processors import (
            SlideEffectProcessor, CircleEffectProcessor,
            FadeEffectProcessor, GIFProcessor, GIFOverlayProcessor
        )

        # Register core infrastructure services
        self.container.register_singleton(CacheService, CacheService(self.config.performance))
        self.container.register_singleton(FileRepository, FileRepository(self.config.paths))
        self.container.register_singleton(FFmpegService, FFmpegService(self.config.video, self.config.ffmpeg))

        # Register video repository with dependencies
        def create_video_repository():
            file_repo = self.container.resolve(FileRepository)
            cache_service = self.container.resolve(CacheService)
            return VideoRepository(file_repo, cache_service)

        self.container.register_factory(VideoRepository, create_video_repository)

        # Register effect processors
        effect_processors = [
            SlideEffectProcessor(self.config.ffmpeg),
            CircleEffectProcessor(self.config.ffmpeg),
            FadeEffectProcessor(self.config.ffmpeg),
            GIFProcessor(self.config.paths),
            GIFOverlayProcessor(self.config.ffmpeg, self.config.paths)
        ]

        # Store effect processors for later use
        self.container.register_singleton(list, effect_processors)

    def _register_application_services(self):
        """Register application layer services"""
        from src.application.services.video_service import VideoService
        from src.application.services.processing_service import ProcessingService
        from src.application.services.effect_service import EffectService

        def create_video_service():
            video_repo = self.container.resolve(VideoRepository)
            file_repo = self.container.resolve(FileRepository)
            video_processor = self.container.resolve(FFmpegService)
            return VideoService(video_repo, file_repo, video_processor, self.config)

        def create_processing_service():
            video_processor = self.container.resolve(FFmpegService)
            return ProcessingService(video_processor, self.config)

        def create_effect_service():
            effect_processors = self.container.resolve(list)
            return EffectService(effect_processors, self.config)

        self.container.register_factory(VideoService, create_video_service)
        self.container.register_factory(ProcessingService, create_processing_service)
        self.container.register_factory(EffectService, create_effect_service)

    def _register_use_cases(self):
        """Register use case layer"""
        from src.application.use_cases.get_videos_use_case import GetVideosUseCase
        from src.application.use_cases.process_video_use_case import ProcessVideoUseCase
        from src.application.use_cases.create_processing_job_use_case import CreateProcessingJobUseCase

        def create_get_videos_use_case():
            video_repo = self.container.resolve(VideoRepository)
            file_repo = self.container.resolve(FileRepository)
            return GetVideosUseCase(video_repo, file_repo, self.config)

        def create_process_video_use_case():
            video_processor = self.container.resolve(FFmpegService)
            video_repo = self.container.resolve(VideoRepository)
            return ProcessVideoUseCase(video_processor, video_repo, self.config)

        def create_processing_job_use_case():
            video_repo = self.container.resolve(VideoRepository)
            return CreateProcessingJobUseCase(video_repo, self.config)

        self.container.register_factory(GetVideosUseCase, create_get_videos_use_case)
        self.container.register_factory(ProcessVideoUseCase, create_process_video_use_case)
        self.container.register_factory(CreateProcessingJobUseCase, create_processing_job_use_case)

    def create_gui_application(self):
        """Create GUI application instance"""
        container = self.create_container()

        try:
            import tkinter as tk
            from src.presentation.gui.main_window import MainWindowView, MainWindowPresenter

            # Create main window
            root = tk.Tk()
            view = MainWindowView(root)

            # Create presenter with dependencies
            video_service = container.resolve(VideoService)
            processing_service = container.resolve(ProcessingService)
            effect_service = container.resolve(EffectService)
            get_videos_use_case = container.resolve(GetVideosUseCase)
            process_video_use_case = container.resolve(ProcessVideoUseCase)

            presenter = MainWindowPresenter(
                view, video_service, processing_service, effect_service,
                get_videos_use_case, process_video_use_case, self.config
            )

            return GUIApplication(root, presenter, processing_service)

        except ImportError:
            raise VideoProcessingException("GUI dependencies not available. Please install tkinter.")

    def create_cli_application(self):
        """Create CLI application instance"""
        container = self.create_container()

        from src.presentation.cli.cli_app import CLIApp

        process_video_use_case = container.resolve(ProcessVideoUseCase)
        get_videos_use_case = container.resolve(GetVideosUseCase)
        return CLIApp(process_video_use_case, get_videos_use_case)


class GUIApplication:
    """GUI application wrapper"""

    def __init__(self, root, presenter, processing_service):
        """
        Initialize GUI application.

        Args:
            root: Tkinter root window
            presenter: Main window presenter
            processing_service: Processing service for cleanup
        """
        self.root = root
        self.presenter = presenter
        self.processing_service = processing_service

    def run(self) -> int:
        """Run the GUI application"""
        try:
            self.presenter.initialize()
            logger.info("Starting GUI application")
            self.root.mainloop()
            return 0
        except Exception as e:
            logger.error(f"Error running GUI: {e}")
            return 1
        finally:
            self._cleanup()

    def _cleanup(self):
        """Cleanup resources"""
        try:
            if hasattr(self.presenter, 'dispose'):
                self.presenter.dispose()
            if hasattr(self.processing_service, 'stop_processing'):
                self.processing_service.stop_processing()
            logger.info("Application cleanup completed")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")


class CLIApplication:
    """CLI application wrapper"""

    def __init__(self, cli_app):
        """
        Initialize CLI application.

        Args:
            cli_app: CLI application instance
        """
        self.cli_app = cli_app

    def run(self, args) -> int:
        """Run the CLI application"""
        try:
            return self.cli_app.run(args)
        except Exception as e:
            logger.error(f"Error running CLI: {e}")
            return 1


def run_gui_mode(factory: ApplicationFactory) -> int:
    """Run application in GUI mode"""
    try:
        gui_app = factory.create_gui_application()
        return gui_app.run()
    except VideoProcessingException as e:
        logger.error(f"GUI application error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected GUI error: {e}")
        return 1


def run_cli_mode(factory: ApplicationFactory, args) -> int:
    """Run application in CLI mode"""
    try:
        cli_app = factory.create_cli_application()
        cli_wrapper = CLIApplication(cli_app)
        return cli_wrapper.run(args)
    except VideoProcessingException as e:
        logger.error(f"CLI application error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected CLI error: {e}")
        if args.debug:
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        return 1


def create_cli_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        description="TikTok Video Processing Tool - Clean Architecture Edition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run GUI mode
  %(prog)s --cli process video.mp4 bg.mp4    # Process single video
  %(prog)s --config custom.json               # Use custom config
  %(prog)s --log-level DEBUG                  # Set log level
  %(prog)s --create-config                    # Create default config file
  %(prog)s --validate-config                  # Validate current config
        """
    )

    # Mode selection
    parser.add_argument(
        '--cli', action='store_true',
        help='Run in CLI mode instead of GUI'
    )

    # Configuration options
    parser.add_argument(
        '--config', type=str, metavar='FILE',
        help='Path to configuration file'
    )

    parser.add_argument(
        '--create-config', action='store_true',
        help='Create default configuration file and exit'
    )

    parser.add_argument(
        '--validate-config', action='store_true',
        help='Validate configuration and exit'
    )

    parser.add_argument(
        '--config-info', action='store_true',
        help='Show configuration information and exit'
    )

    # Logging options
    parser.add_argument(
        '--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO', help='Set logging level'
    )

    parser.add_argument(
        '--log-file', type=str, metavar='FILE',
        help='Log to file instead of console'
    )

    # Development options
    parser.add_argument(
        '--profile', action='store_true',
        help='Enable performance profiling'
    )

    parser.add_argument(
        '--debug', action='store_true',
        help='Enable debug mode (implies --log-level DEBUG)'
    )

    # CLI subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Process command
    process_parser = subparsers.add_parser('process', help='Process videos')
    process_parser.add_argument('input_video', help='Input video file')
    process_parser.add_argument('background_video', help='Background video file')
    process_parser.add_argument('-o', '--output', help='Output video file')
    process_parser.add_argument('-e', '--effect', help='Effect type to apply')
    process_parser.add_argument('-d', '--duration', type=float, default=2.0,
                               help='Effect duration in seconds')
    process_parser.add_argument('--dry-run', action='store_true',
                               help='Show what would be done without processing')

    # List command
    list_parser = subparsers.add_parser('list', help='List available videos')
    list_parser.add_argument('-d', '--directory', help='Directory to scan')
    list_parser.add_argument('-r', '--recursive', action='store_true',
                            help='Scan recursively')
    list_parser.add_argument('--format', choices=['table', 'json', 'csv'],
                            default='table', help='Output format')

    # Effects command
    effects_parser = subparsers.add_parser('effects', help='List available effects')
    effects_parser.add_argument('--format', choices=['table', 'json'],
                               default='table', help='Output format')

    # Config command
    config_parser = subparsers.add_parser('config', help='Configuration management')
    config_subparsers = config_parser.add_subparsers(dest='config_command')

    config_subparsers.add_parser('show', help='Show current configuration')
    config_subparsers.add_parser('validate', help='Validate configuration')
    config_subparsers.add_parser('create', help='Create default configuration')

    preset_parser = config_subparsers.add_parser('preset', help='Apply configuration preset')
    preset_parser.add_argument('preset_name', choices=['fast', 'balanced', 'quality'],
                              help='Preset to apply')

    return parser


def handle_config_commands(args) -> Optional[int]:
    """Handle configuration-related commands that don't require full app startup"""
    from src.shared.config.config_loader import get_config_loader

    if args.create_config:
        try:
            config_path = Path(args.config) if args.config else None
            loader = get_config_loader(config_path)
            created_path = loader.create_default_config_file(config_path)
            print(f"✓ Created default configuration file: {created_path}")
            return 0
        except Exception as e:
            print(f"✗ Failed to create configuration file: {e}")
            return 1

    if args.validate_config or args.config_info:
        try:
            config_path = Path(args.config) if args.config else None
            config = load_config(config_path)

            if args.validate_config:
                validation_errors = config.validate()
                if validation_errors:
                    print("Configuration validation errors:")
                    for error in validation_errors:
                        print(f"  ✗ {error}")
                    return 1
                else:
                    print("✓ Configuration is valid")
                    return 0

            if args.config_info:
                loader = get_config_loader(config_path)
                info = loader.get_config_info()

                print("Configuration Information:")
                print(f"  Version: {info['config_version']}")
                print(f"  Created: {info['created_at'] or 'Unknown'}")
                print(f"  Updated: {info['updated_at'] or 'Unknown'}")
                print(f"  Valid: {'Yes' if info['is_valid'] else 'No'}")

                if info['validation_errors']:
                    print("  Validation Errors:")
                    for error in info['validation_errors']:
                        print(f"    - {error}")

                print("  Configuration Sources:")
                for source in info['config_sources']:
                    if source['type'] == 'environment':
                        print(f"    Environment Variables: {source['count']} set")
                    else:
                        status = "✓" if source['exists'] and source['readable'] else "✗"
                        print(f"    {status} {source['path']} ({source['type']})")

                return 0

        except Exception as e:
            print(f"✗ Configuration error: {e}")
            return 1

    return None


def setup_application_config(args):
    """Setup application configuration with command line overrides"""
    # Load base configuration
    config_path = Path(args.config) if args.config else None
    config = load_config(config_path)

    # Apply command line overrides
    if args.debug:
        config.ui.log_level = 'DEBUG'
        args.log_level = 'DEBUG'
    elif args.log_level:
        config.ui.log_level = args.log_level

    # Setup logging
    if args.log_file:
        # Custom logging setup for file output
        logging.basicConfig(
            level=getattr(logging, config.ui.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=args.log_file,
            filemode='a'
        )
    else:
        setup_logging(config)

    return config


def main():
    """Main application entry point"""
    parser = create_cli_parser()
    args = parser.parse_args()

    # Handle configuration commands that don't require full app startup
    config_result = handle_config_commands(args)
    if config_result is not None:
        return config_result

    try:
        # Setup configuration
        config = setup_application_config(args)
        logger.info("TikTok Video Processing Tool starting")
        logger.debug(f"Command line arguments: {vars(args)}")

        # Validate configuration
        validation_errors = config.validate()
        if validation_errors:
            logger.warning(f"Configuration warnings: {validation_errors}")
            if not args.cli:
                # In GUI mode, show warnings but continue
                for error in validation_errors:
                    logger.warning(f"Config warning: {error}")
            else:
                # In CLI mode, be more strict
                print("Configuration warnings detected:")
                for error in validation_errors:
                    print(f"  ⚠ {error}")

        # Ensure directories exist
        config.ensure_directories()

        # Create application factory
        factory = ApplicationFactory(config)

        # Enable profiling if requested
        if args.profile:
            import cProfile
            import pstats
            from io import StringIO

            profiler = cProfile.Profile()
            profiler.enable()

        # Run appropriate mode
        try:
            if args.cli:
                exit_code = run_cli_mode(factory, args)
            else:
                exit_code = run_gui_mode(factory)
        finally:
            if args.profile:
                profiler.disable()
                stats_stream = StringIO()
                stats = pstats.Stats(profiler, stream=stats_stream)
                stats.sort_stats('cumulative')
                stats.print_stats(20)  # Top 20 functions
                logger.info(f"Performance profile:\n{stats_stream.getvalue()}")

        logger.info(f"Application exiting with code {exit_code}")
        return exit_code

    except VideoProcessingException as e:
        logger.error(f"Application error: {e}")
        if args.debug:
            logger.exception("Full traceback:")
        return 1
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.debug:
            logger.exception("Full traceback:")
        else:
            logger.error("Use --debug for full traceback")
        return 1


if __name__ == "__main__":
    sys.exit(main())
