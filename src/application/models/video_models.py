"""
Video Models

Data transfer objects for video-related operations.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path

from ...domain.entities.video import Video
from ...domain.value_objects.dimensions import Dimensions


@dataclass
class VideoDTO:
    """Data transfer object for Video entity"""
    path: str
    filename: str
    duration: float
    width: int
    height: int
    file_size: Optional[int] = None
    format: Optional[str] = None
    cached: bool = False
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @classmethod
    def from_entity(cls, video: Video) -> 'VideoDTO':
        """Create DTO from Video entity"""
        return cls(
            path=str(video.path),
            filename=video.filename,
            duration=video.duration,
            width=video.dimensions.width,
            height=video.dimensions.height,
            file_size=video.file_size,
            format=video.extension,
            cached=video.is_cached(),
            metadata=video.metadata.copy()
        )

    @property
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio"""
        return self.width / self.height if self.height > 0 else 0.0

    @property
    def resolution_string(self) -> str:
        """Get resolution as string"""
        return f"{self.width}x{self.height}"

    @property
    def duration_string(self) -> str:
        """Get duration as formatted string"""
        minutes = int(self.duration // 60)
        seconds = int(self.duration % 60)
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def file_size_mb(self) -> Optional[float]:
        """Get file size in MB"""
        if self.file_size is None:
            return None
        return round(self.file_size / (1024 * 1024), 2)


@dataclass
class VideoListResponse:
    """Response for video list operations"""
    success: bool
    videos: List[VideoDTO]
    total_count: int
    total_duration: float
    total_size: Optional[int] = None
    error_message: Optional[str] = None

    @property
    def total_duration_string(self) -> str:
        """Get total duration as formatted string"""
        hours = int(self.total_duration // 3600)
        minutes = int((self.total_duration % 3600) // 60)
        seconds = int(self.total_duration % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    @property
    def total_size_mb(self) -> Optional[float]:
        """Get total size in MB"""
        if self.total_size is None:
            return None
        return round(self.total_size / (1024 * 1024), 2)


@dataclass
class VideoSearchRequest:
    """Request for video search operations"""
    directory: Optional[str] = None
    pattern: str = "*.mp4"
    recursive: bool = False
    min_duration: Optional[float] = None
    max_duration: Optional[float] = None
    extensions: Optional[List[str]] = None
    refresh_cache: bool = False

    def to_path(self) -> Optional[Path]:
        """Convert directory string to Path"""
        return Path(self.directory) if self.directory else None


@dataclass
class VideoStatistics:
    """Video statistics data"""
    total_count: int
    total_duration: float
    average_duration: float
    total_size: int
    formats: Dict[str, int]
    resolutions: Dict[str, int]

    @property
    def total_size_gb(self) -> float:
        """Get total size in GB"""
        return round(self.total_size / (1024 * 1024 * 1024), 2)

    @property
    def most_common_format(self) -> Optional[str]:
        """Get most common video format"""
        if not self.formats:
            return None
        return max(self.formats.items(), key=lambda x: x[1])[0]

    @property
    def most_common_resolution(self) -> Optional[str]:
        """Get most common resolution"""
        if not self.resolutions:
            return None
        return max(self.resolutions.items(), key=lambda x: x[1])[0]
