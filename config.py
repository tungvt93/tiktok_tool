"""
Configuration file for video processing tool
"""

from dataclasses import dataclass
from typing import Tuple

@dataclass
class VideoConfig:
    """Configuration for video processing"""
    # Output dimensions
    OUTPUT_WIDTH: int = 1080
    OUTPUT_HEIGHT: int = 1080
    HALF_WIDTH: int = 540
    
    # Video processing
    SPEED_MULTIPLIER: float = 1.3
    FRAME_RATE: int = 10
    CRF_VALUE: int = 23
    
    # Paths
    INPUT_DIR: str = "dongphuc"
    BACKGROUND_DIR: str = "video_chia_2"
    OUTPUT_DIR: str = "output"
    EFFECTS_DIR: str = "effects"
    GENERATED_EFFECTS_DIR: str = "generated_effects"  # New folder for generated GIFs
    
    # File patterns
    INPUT_PATTERN: str = "*.mp4"
    BACKGROUND_PATTERN: str = "*.mp4"
    
    # Performance settings
    MAX_WORKERS: int = None  # Will be set to CPU count if None
    CACHE_FILE: str = "video_cache.json"
    
    @property
    def output_size(self) -> Tuple[int, int]:
        return (self.OUTPUT_WIDTH, self.OUTPUT_HEIGHT)

@dataclass
class FFmpegConfig:
    """FFmpeg command configurations"""
    PRESET: str = "ultrafast"
    CODEC_VIDEO: str = "libx264"
    CODEC_AUDIO: str = "aac"
    THREADS: str = "0"

# Default configurations
DEFAULT_VIDEO_CONFIG = VideoConfig()
DEFAULT_FFMPEG_CONFIG = FFmpegConfig()

# Production configurations (higher quality)
PRODUCTION_VIDEO_CONFIG = VideoConfig(
    CRF_VALUE=18,  # Higher quality
    PRESET="medium"  # Better compression
)

# Fast configurations (lower quality, faster processing)
FAST_VIDEO_CONFIG = VideoConfig(
    CRF_VALUE=28,  # Lower quality
    SPEED_MULTIPLIER=1.5  # Faster speed
) 