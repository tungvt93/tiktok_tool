"""
Video Processing Configuration

Configuration classes for video processing operations.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
import os

from ...domain.value_objects.dimensions import Dimensions


@dataclass
class VideoProcessingConfig:
    """Configuration for video processing operations"""
    # Output dimensions
    output_width: int = 1080
    output_height: int = 1080

    # Video processing settings
    speed_multiplier: float = 1.3
    frame_rate: int = 10
    crf_value: int = 23

    # Opening effect settings
    default_effect_duration: float = 2.0

    def __post_init__(self):
        """Validate configuration after initialization"""
        self._validate()

    def _validate(self):
        """Validate configuration values"""
        if self.output_width <= 0:
            raise ValueError(f"Output width must be positive, got {self.output_width}")
        if self.output_height <= 0:
            raise ValueError(f"Output height must be positive, got {self.output_height}")
        if self.speed_multiplier <= 0:
            raise ValueError(f"Speed multiplier must be positive, got {self.speed_multiplier}")
        if self.frame_rate <= 0:
            raise ValueError(f"Frame rate must be positive, got {self.frame_rate}")
        if not (0 <= self.crf_value <= 51):
            raise ValueError(f"CRF value must be between 0 and 51, got {self.crf_value}")
        if self.default_effect_duration < 0:
            raise ValueError(f"Effect duration must be non-negative, got {self.default_effect_duration}")

    @property
    def output_dimensions(self) -> Dimensions:
        """Get output dimensions as Dimensions object"""
        return Dimensions(self.output_width, self.output_height)

    @property
    def half_width(self) -> int:
        """Get half width for side-by-side layouts"""
        return self.output_width // 2

    def get_quality_preset(self) -> str:
        """Get quality preset based on CRF value"""
        if self.crf_value <= 18:
            return "high"
        elif self.crf_value <= 23:
            return "medium"
        else:
            return "fast"


@dataclass
class FFmpegConfig:
    """Configuration for FFmpeg operations"""
    preset: str = "ultrafast"
    codec_video: str = "libx264"
    codec_audio: str = "aac"
    threads: str = "0"

    def __post_init__(self):
        """Validate configuration after initialization"""
        self._validate()

    def _validate(self):
        """Validate FFmpeg configuration"""
        valid_presets = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]
        if self.preset not in valid_presets:
            raise ValueError(f"Invalid preset: {self.preset}. Must be one of {valid_presets}")

        valid_video_codecs = ["libx264", "libx265", "libvpx", "libvpx-vp9"]
        if self.codec_video not in valid_video_codecs:
            raise ValueError(f"Invalid video codec: {self.codec_video}. Must be one of {valid_video_codecs}")

        valid_audio_codecs = ["aac", "mp3", "libvorbis", "libopus"]
        if self.codec_audio not in valid_audio_codecs:
            raise ValueError(f"Invalid audio codec: {self.codec_audio}. Must be one of {valid_audio_codecs}")


@dataclass
class PathConfig:
    """Configuration for file paths and directories"""
    input_dir: Path = Path("dongphuc")
    background_dir: Path = Path("video_chia_2")
    output_dir: Path = Path("output")
    effects_dir: Path = Path("effects")
    generated_effects_dir: Path = Path("generated_effects")
    temp_dir: Optional[Path] = None

    # File patterns
    input_pattern: str = "*.mp4"
    background_pattern: str = "*.mp4"

    def __post_init__(self):
        """Initialize paths and validate configuration"""
        # Convert string paths to Path objects
        if isinstance(self.input_dir, str):
            self.input_dir = Path(self.input_dir)
        if isinstance(self.background_dir, str):
            self.background_dir = Path(self.background_dir)
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        if isinstance(self.effects_dir, str):
            self.effects_dir = Path(self.effects_dir)
        if isinstance(self.generated_effects_dir, str):
            self.generated_effects_dir = Path(self.generated_effects_dir)

        # Set default temp directory if not specified
        if self.temp_dir is None:
            self.temp_dir = Path.cwd() / "temp"
        elif isinstance(self.temp_dir, str):
            self.temp_dir = Path(self.temp_dir)

    def ensure_directories_exist(self) -> None:
        """Create directories if they don't exist"""
        directories = [
            self.output_dir,
            self.effects_dir,
            self.generated_effects_dir,
            self.temp_dir
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def get_input_files_pattern(self) -> str:
        """Get full pattern for input files"""
        return str(self.input_dir / self.input_pattern)

    def get_background_files_pattern(self) -> str:
        """Get full pattern for background files"""
        return str(self.background_dir / self.background_pattern)


@dataclass
class PerformanceConfig:
    """Configuration for performance settings"""
    max_workers: Optional[int] = None
    cache_enabled: bool = True
    cache_file: str = "video_cache.json"
    memory_limit_mb: Optional[int] = None

    def __post_init__(self):
        """Initialize performance settings"""
        # Set default max_workers to CPU count if not specified
        if self.max_workers is None:
            self.max_workers = os.cpu_count() or 1

        self._validate()

    def _validate(self):
        """Validate performance configuration"""
        if self.max_workers <= 0:
            raise ValueError(f"Max workers must be positive, got {self.max_workers}")

        if self.memory_limit_mb is not None and self.memory_limit_mb <= 0:
            raise ValueError(f"Memory limit must be positive, got {self.memory_limit_mb}")

    @property
    def cache_path(self) -> Path:
        """Get cache file path"""
        return Path(self.cache_file)


@dataclass
class UIConfig:
    """Configuration for user interface"""
    theme: str = "dark"
    window_width: int = 1400
    window_height: int = 800
    auto_refresh_interval: int = 5  # seconds
    show_preview: bool = True
    log_level: str = "INFO"

    def __post_init__(self):
        """Validate UI configuration"""
        self._validate()

    def _validate(self):
        """Validate UI configuration"""
        valid_themes = ["dark", "light", "auto"]
        if self.theme not in valid_themes:
            raise ValueError(f"Invalid theme: {self.theme}. Must be one of {valid_themes}")

        if self.window_width <= 0:
            raise ValueError(f"Window width must be positive, got {self.window_width}")
        if self.window_height <= 0:
            raise ValueError(f"Window height must be positive, got {self.window_height}")

        if self.auto_refresh_interval <= 0:
            raise ValueError(f"Auto refresh interval must be positive, got {self.auto_refresh_interval}")

        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_log_levels:
            raise ValueError(f"Invalid log level: {self.log_level}. Must be one of {valid_log_levels}")
