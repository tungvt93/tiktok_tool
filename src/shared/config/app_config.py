"""
Application Configuration

Main configuration class that combines all configuration sections.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import os
from datetime import datetime

from .video_config import VideoProcessingConfig, FFmpegConfig, PathConfig, PerformanceConfig, UIConfig


@dataclass
class AppConfig:
    """Main application configuration"""
    video: VideoProcessingConfig = None
    ffmpeg: FFmpegConfig = None
    paths: PathConfig = None
    performance: PerformanceConfig = None
    ui: UIConfig = None

    # Metadata
    config_version: str = "2.0.0"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Initialize default configurations if not provided"""
        if self.video is None:
            self.video = VideoProcessingConfig()
        if self.ffmpeg is None:
            self.ffmpeg = FFmpegConfig()
        if self.paths is None:
            self.paths = PathConfig()
        if self.performance is None:
            self.performance = PerformanceConfig()
        if self.ui is None:
            self.ui = UIConfig()

        if self.created_at is None:
            self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def validate(self) -> List[str]:
        """Validate entire configuration and return list of errors"""
        errors = []

        # Each config section validates itself in __post_init__
        # This method can add cross-section validation

        # Validate that output directory is writable
        try:
            self.paths.output_dir.mkdir(parents=True, exist_ok=True)
            test_file = self.paths.output_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            errors.append(f"Output directory is not writable: {e}")

        # Validate that input directories exist
        if not self.paths.input_dir.exists():
            errors.append(f"Input directory does not exist: {self.paths.input_dir}")
        if not self.paths.background_dir.exists():
            errors.append(f"Background directory does not exist: {self.paths.background_dir}")

        # Validate performance settings
        if self.performance.memory_limit_mb:
            if self.performance.memory_limit_mb < 512:
                errors.append("Memory limit should be at least 512MB for video processing")

        return errors

    def is_valid(self) -> bool:
        """Check if configuration is valid"""
        return len(self.validate()) == 0

    def ensure_directories(self) -> None:
        """Ensure all required directories exist"""
        self.paths.ensure_directories_exist()

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        config_dict = {}

        # Convert each section to dict
        config_dict['video'] = asdict(self.video)
        config_dict['ffmpeg'] = asdict(self.ffmpeg)
        config_dict['paths'] = {
            'input_dir': str(self.paths.input_dir),
            'background_dir': str(self.paths.background_dir),
            'output_dir': str(self.paths.output_dir),
            'effects_dir': str(self.paths.effects_dir),
            'generated_effects_dir': str(self.paths.generated_effects_dir),
            'temp_dir': str(self.paths.temp_dir) if self.paths.temp_dir else None,
            'input_pattern': self.paths.input_pattern,
            'background_pattern': self.paths.background_pattern
        }
        config_dict['performance'] = asdict(self.performance)
        config_dict['ui'] = asdict(self.ui)

        # Add metadata
        config_dict['config_version'] = self.config_version
        config_dict['created_at'] = self.created_at.isoformat() if self.created_at else None
        config_dict['updated_at'] = self.updated_at.isoformat() if self.updated_at else None

        return config_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """Create configuration from dictionary"""
        # Parse datetime fields
        created_at = None
        updated_at = None
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            updated_at = datetime.fromisoformat(data['updated_at'])

        # Create config sections
        video_config = VideoProcessingConfig(**data.get('video', {}))
        ffmpeg_config = FFmpegConfig(**data.get('ffmpeg', {}))

        # Handle paths specially due to Path objects
        paths_data = data.get('paths', {})
        paths_config = PathConfig(
            input_dir=Path(paths_data.get('input_dir', 'dongphuc')),
            background_dir=Path(paths_data.get('background_dir', 'video_chia_2')),
            output_dir=Path(paths_data.get('output_dir', 'output')),
            effects_dir=Path(paths_data.get('effects_dir', 'effects')),
            generated_effects_dir=Path(paths_data.get('generated_effects_dir', 'generated_effects')),
            temp_dir=Path(paths_data['temp_dir']) if paths_data.get('temp_dir') else None,
            input_pattern=paths_data.get('input_pattern', '*.mp4'),
            background_pattern=paths_data.get('background_pattern', '*.mp4')
        )

        performance_config = PerformanceConfig(**data.get('performance', {}))
        ui_config = UIConfig(**data.get('ui', {}))

        return cls(
            video=video_config,
            ffmpeg=ffmpeg_config,
            paths=paths_config,
            performance=performance_config,
            ui=ui_config,
            config_version=data.get('config_version', '2.0.0'),
            created_at=created_at,
            updated_at=updated_at
        )

    @classmethod
    def from_file(cls, config_path: Path) -> 'AppConfig':
        """Load configuration from JSON file"""
        if not config_path.exists():
            # Return default configuration if file doesn't exist
            return cls()

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            raise ValueError(f"Failed to load configuration from {config_path}: {e}")

    def save_to_file(self, config_path: Path) -> None:
        """Save configuration to JSON file"""
        self.updated_at = datetime.now()

        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise ValueError(f"Failed to save configuration to {config_path}: {e}")

    @classmethod
    def from_environment(cls) -> 'AppConfig':
        """Create configuration from environment variables"""
        config = cls()

        # Override with environment variables if present
        if os.getenv('VIDEO_OUTPUT_WIDTH'):
            config.video.output_width = int(os.getenv('VIDEO_OUTPUT_WIDTH'))
        if os.getenv('VIDEO_OUTPUT_HEIGHT'):
            config.video.output_height = int(os.getenv('VIDEO_OUTPUT_HEIGHT'))
        if os.getenv('VIDEO_CRF_VALUE'):
            config.video.crf_value = int(os.getenv('VIDEO_CRF_VALUE'))

        if os.getenv('FFMPEG_PRESET'):
            config.ffmpeg.preset = os.getenv('FFMPEG_PRESET')

        if os.getenv('INPUT_DIR'):
            config.paths.input_dir = Path(os.getenv('INPUT_DIR'))
        if os.getenv('OUTPUT_DIR'):
            config.paths.output_dir = Path(os.getenv('OUTPUT_DIR'))

        if os.getenv('MAX_WORKERS'):
            config.performance.max_workers = int(os.getenv('MAX_WORKERS'))

        if os.getenv('UI_THEME'):
            config.ui.theme = os.getenv('UI_THEME')
        if os.getenv('LOG_LEVEL'):
            config.ui.log_level = os.getenv('LOG_LEVEL')

        return config

    def get_preset_config(self, preset_name: str) -> 'AppConfig':
        """Get a preset configuration"""
        presets = {
            'fast': self._get_fast_preset(),
            'balanced': self._get_balanced_preset(),
            'quality': self._get_quality_preset()
        }

        if preset_name not in presets:
            raise ValueError(f"Unknown preset: {preset_name}. Available: {list(presets.keys())}")

        return presets[preset_name]

    def _get_fast_preset(self) -> 'AppConfig':
        """Get fast processing preset"""
        config = AppConfig()
        config.video.crf_value = 28
        config.video.speed_multiplier = 1.5
        config.ffmpeg.preset = "ultrafast"
        return config

    def _get_balanced_preset(self) -> 'AppConfig':
        """Get balanced preset"""
        config = AppConfig()
        config.video.crf_value = 23
        config.video.speed_multiplier = 1.3
        config.ffmpeg.preset = "fast"
        return config

    def _get_quality_preset(self) -> 'AppConfig':
        """Get high quality preset"""
        config = AppConfig()
        config.video.crf_value = 18
        config.video.speed_multiplier = 1.0
        config.ffmpeg.preset = "medium"
        return config
