"""
CLI Application

Command-line interface for batch processing.
"""

import sys
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import time

from ...application.use_cases.process_video_use_case import ProcessVideoUseCase, ProcessVideoRequest
from ...application.use_cases.get_videos_use_case import GetVideosUseCase, GetVideosRequest
from ...application.models.video_models import VideoDTO
from ...domain.value_objects.effect_type import EffectType
from ...shared.utils import get_logger, handle_exception
from ...shared.exceptions.base_exceptions import VideoProcessingException

logger = get_logger(__name__)


class CLIApp:
    """Command-line interface application"""

    def __init__(self, process_video_use_case: ProcessVideoUseCase, get_videos_use_case: GetVideosUseCase):
        """
        Initialize CLI application.

        Args:
            process_video_use_case: Use case for processing videos
            get_videos_use_case: Use case for getting video information
        """
        self.process_video_use_case = process_video_use_case
        self.get_videos_use_case = get_videos_use_case

    def run(self, args) -> int:
        """
        Run CLI application.

        Args:
            args: Parsed command line arguments

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        try:
            if args.command == 'process':
                return self._process_video(args)
            elif args.command == 'list':
                return self._list_videos(args)
            elif args.command == 'effects':
                return self._list_effects(args)
            elif args.command == 'config':
                return self._handle_config_command(args)
            else:
                print("No command specified. Use --help for usage information.")
                return 1

        except Exception as e:
            print(f"CLI Error: {e}")
            logger.error(f"CLI error: {e}")
            return 1

    def _process_video(self, args) -> int:
        """Process a single video"""
        input_path = Path(args.input_video)
        background_path = Path(args.background_video)

        # Validate input files
        if not input_path.exists():
            print(f"Error: Input video not found: {input_path}")
            return 1

        if not background_path.exists():
            print(f"Error: Background video not found: {background_path}")
            return 1

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = input_path.parent / f"processed_{input_path.name}"

        # Create effects if specified
        effects = []
        if args.effect and args.effect != 'none':
            effects.append({
                'type': args.effect,
                'duration': args.duration,
                'parameters': {}
            })

        # Dry run mode
        if hasattr(args, 'dry_run') and args.dry_run:
            print("Dry run mode - showing what would be done:")
            print(f"  Input: {input_path}")
            print(f"  Background: {background_path}")
            print(f"  Output: {output_path}")
            if effects:
                print(f"  Effects: {args.effect} ({args.duration}s)")
            else:
                print("  Effects: None")
            return 0

        # Create request
        request = ProcessVideoRequest(
            main_video_path=input_path,
            background_video_path=background_path,
            output_path=output_path,
            effects=effects
        )

        # Process video with progress reporting
        print(f"Processing video: {input_path.name}")
        print(f"Background: {background_path.name}")
        print(f"Output: {output_path}")

        if effects:
            print(f"Effects: {args.effect} ({args.duration}s)")

        start_time = time.time()
        print("Processing... ", end="", flush=True)

        response = self.process_video_use_case.execute(request)

        processing_time = time.time() - start_time

        if response.success:
            print("✓")
            print(f"✓ Processing completed successfully!")
            print(f"  Output: {response.output_path}")
            print(f"  Time: {processing_time:.1f}s")
            return 0
        else:
            print("✗")
            print(f"✗ Processing failed: {response.error_message}")
            return 1

    def _list_videos(self, args) -> int:
        """List available videos"""
        try:
            # Determine directory to scan
            directory = Path(args.directory) if hasattr(args, 'directory') and args.directory else None

            # Create request
            request = GetVideosRequest(
                directory=directory,
                recursive=hasattr(args, 'recursive') and args.recursive,
                refresh_cache=False
            )

            # Get videos
            response = self.get_videos_use_case.execute(request)

            if not response.success:
                print(f"Error: {response.error_message}")
                return 1

            videos = response.videos

            if not videos:
                print("No videos found.")
                return 0

            # Convert Video entities to VideoDTO
            video_dtos = [VideoDTO.from_entity(video) for video in videos]

            # Format output based on requested format
            output_format = getattr(args, 'format', 'table')

            if output_format == 'json':
                self._output_videos_json(video_dtos)
            elif output_format == 'csv':
                self._output_videos_csv(video_dtos)
            else:  # table format
                self._output_videos_table(video_dtos)

            return 0

        except Exception as e:
            print(f"Error listing videos: {e}")
            logger.error(f"Error listing videos: {e}")
            return 1

    def _output_videos_table(self, videos: List[VideoDTO]) -> None:
        """Output videos in table format"""
        print(f"\nFound {len(videos)} video(s):")
        print()
        print(f"{'Name':<30} {'Duration':<10} {'Size':<15} {'Resolution':<12} {'Path'}")
        print("-" * 90)

        for video in videos:
            duration_str = f"{video.duration:.1f}s" if video.duration else "Unknown"
            size_str = self._format_file_size(video.file_size) if video.file_size else "Unknown"
            resolution_str = f"{video.width}x{video.height}" if video.width and video.height else "Unknown"

            print(f"{video.filename:<30} {duration_str:<10} {size_str:<15} {resolution_str:<12} {video.path}")

    def _output_videos_json(self, videos: List[VideoDTO]) -> None:
        """Output videos in JSON format"""
        video_data = []
        for video in videos:
            video_data.append({
                'filename': video.filename,
                'path': str(video.path),
                'duration': video.duration,
                'file_size': video.file_size,
                'width': video.width,
                'height': video.height,
                'format': video.format,
                'cached': video.cached,
                'metadata': video.metadata
            })

        print(json.dumps(video_data, indent=2))

    def _output_videos_csv(self, videos: List[VideoDTO]) -> None:
        """Output videos in CSV format"""
        import io
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(['filename', 'path', 'duration', 'file_size', 'width', 'height', 'format', 'cached'])

        # Write data
        for video in videos:
            writer.writerow([
                video.filename,
                str(video.path),
                video.duration,
                video.file_size,
                video.width,
                video.height,
                video.format,
                video.cached
            ])

        print(output.getvalue().strip())

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f}KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f}MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f}GB"

    def _list_effects(self, args) -> int:
        """List available effects"""
        print("Available effects:")
        print()

        effects_info = {
            EffectType.NONE: "No effect applied",
            EffectType.FADE_IN: "Gradually fade in from black background",
            EffectType.SLIDE_RIGHT_TO_LEFT: "Slide video from right to left",
            EffectType.SLIDE_LEFT_TO_RIGHT: "Slide video from left to right",
            EffectType.SLIDE_TOP_TO_BOTTOM: "Slide video from top to bottom",
            EffectType.SLIDE_BOTTOM_TO_TOP: "Slide video from bottom to top",
            EffectType.CIRCLE_EXPAND: "Reveal video with expanding circle",
            EffectType.CIRCLE_CONTRACT: "Hide video with contracting circle",
            EffectType.CIRCLE_ROTATE_CW: "Reveal video with clockwise rotating circle",
            EffectType.CIRCLE_ROTATE_CCW: "Reveal video with counter-clockwise rotating circle"
        }

        for effect_type, description in effects_info.items():
            print(f"  {effect_type.value:<20} - {description}")

        print()
        print("Usage: --effect EFFECT_NAME --duration SECONDS")

        return 0

    def _handle_config_command(self, args) -> int:
        """Handle configuration management commands"""
        if not hasattr(args, 'config_command') or not args.config_command:
            print("No config command specified. Use 'config --help' for available commands.")
            return 1

        if args.config_command == 'show':
            return self._show_config()
        elif args.config_command == 'validate':
            return self._validate_config()
        elif args.config_command == 'create':
            return self._create_config()
        elif args.config_command == 'preset':
            return self._apply_preset(args.preset_name)
        else:
            print(f"Unknown config command: {args.config_command}")
            return 1

    def _show_config(self) -> int:
        """Show current configuration"""
        try:
            from ...shared.config.config_loader import get_config_loader

            loader = get_config_loader()
            config = loader.load_config()

            print("Current Configuration:")
            print(f"  Version: {config.config_version}")
            print(f"  Created: {config.created_at}")
            print(f"  Updated: {config.updated_at}")
            print()

            print("Video Settings:")
            print(f"  Output Resolution: {config.video.output_width}x{config.video.output_height}")
            print(f"  Frame Rate: {config.video.frame_rate}")
            print(f"  CRF Value: {config.video.crf_value}")
            print(f"  Speed Multiplier: {config.video.speed_multiplier}")
            print()

            print("FFmpeg Settings:")
            print(f"  Preset: {config.ffmpeg.preset}")
            print(f"  Video Codec: {config.ffmpeg.codec_video}")
            print(f"  Audio Codec: {config.ffmpeg.codec_audio}")
            print()

            print("Paths:")
            print(f"  Input Directory: {config.paths.input_dir}")
            print(f"  Background Directory: {config.paths.background_dir}")
            print(f"  Output Directory: {config.paths.output_dir}")
            print()

            print("Performance:")
            print(f"  Max Workers: {config.performance.max_workers}")
            print(f"  Cache Enabled: {config.performance.cache_enabled}")

            return 0

        except Exception as e:
            print(f"Error showing configuration: {e}")
            return 1

    def _validate_config(self) -> int:
        """Validate current configuration"""
        try:
            from ...shared.config.config_loader import load_config

            config = load_config()
            validation_errors = config.validate()

            if validation_errors:
                print("Configuration validation errors:")
                for error in validation_errors:
                    print(f"  ✗ {error}")
                return 1
            else:
                print("✓ Configuration is valid")
                return 0

        except Exception as e:
            print(f"Error validating configuration: {e}")
            return 1

    def _create_config(self) -> int:
        """Create default configuration file"""
        try:
            from ...shared.config.config_loader import get_config_loader

            loader = get_config_loader()
            created_path = loader.create_default_config_file()
            print(f"✓ Created default configuration file: {created_path}")
            return 0

        except Exception as e:
            print(f"Error creating configuration file: {e}")
            return 1

    def _apply_preset(self, preset_name: str) -> int:
        """Apply configuration preset"""
        try:
            from ...shared.config.config_loader import load_config, save_config

            config = load_config()
            preset_config = config.get_preset_config(preset_name)

            # Apply preset settings
            config.video = preset_config.video
            config.ffmpeg = preset_config.ffmpeg

            save_config(config)
            print(f"✓ Applied '{preset_name}' preset configuration")
            return 0

        except Exception as e:
            print(f"Error applying preset: {e}")
            return 1
