"""
Video Entity

Represents a video file with its metadata and properties.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from ..value_objects.dimensions import Dimensions


@dataclass
class Video:
    """Video entity representing a video file and its metadata"""
    path: Path
    duration: float
    dimensions: Dimensions
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    cached_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate video properties after initialization"""
        self._validate()

    def _validate(self):
        """Validate video properties"""
        if not self.path.exists():
            raise ValueError(f"Video file does not exist: {self.path}")

        if self.duration <= 0:
            raise ValueError(f"Duration must be positive, got {self.duration}")

        if not self.path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
            raise ValueError(f"Unsupported video format: {self.path.suffix}")

    @property
    def filename(self) -> str:
        """Get the filename without path"""
        return self.path.name

    @property
    def file_size(self) -> int:
        """Get file size in bytes"""
        return self.path.stat().st_size

    @property
    def extension(self) -> str:
        """Get file extension"""
        return self.path.suffix.lower()

    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """Get metadata value with default"""
        return self.metadata.get(key, default)

    def set_metadata_value(self, key: str, value: Any) -> None:
        """Set metadata value"""
        self.metadata[key] = value

    def is_cached(self) -> bool:
        """Check if video metadata is cached"""
        return self.cached_at is not None

    def mark_as_cached(self) -> None:
        """Mark video as cached with current timestamp"""
        self.cached_at = datetime.now()

    def get_display_name(self) -> str:
        """Get user-friendly display name"""
        return self.path.stem

    def __str__(self) -> str:
        """String representation"""
        return f"Video({self.filename}, {self.duration:.1f}s, {self.dimensions.width}x{self.dimensions.height})"

    def __eq__(self, other) -> bool:
        """Equality based on path"""
        if not isinstance(other, Video):
            return False
        return self.path == other.path

    def __hash__(self) -> int:
        """Hash based on path"""
        return hash(self.path)
