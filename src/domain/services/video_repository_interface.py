"""
Video Repository Interface

Defines the contract for video data access operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path

from ..entities.video import Video
from ..value_objects.dimensions import Dimensions


class VideoSearchCriteria:
    """Criteria for searching videos"""

    def __init__(self, directory: Optional[Path] = None, min_duration: Optional[float] = None,
                 max_duration: Optional[float] = None, dimensions: Optional[Dimensions] = None,
                 extensions: Optional[List[str]] = None):
        self.directory = directory
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.dimensions = dimensions
        self.extensions = extensions or ['.mp4', '.avi', '.mov', '.mkv']


class IVideoRepository(ABC):
    """Interface for video data access operations"""

    @abstractmethod
    def get_by_path(self, path: Path) -> Optional[Video]:
        """
        Get video by file path.

        Args:
            path: Path to the video file

        Returns:
            Video entity or None if not found
        """
    @abstractmethod
    def get_all(self, criteria: Optional[VideoSearchCriteria] = None) -> List[Video]:
        """
        Get all videos matching the criteria.

        Args:
            criteria: Search criteria (optional)

        Returns:
            List of Video entities
        """
    @abstractmethod
    def save(self, video: Video) -> bool:
        """
        Save video metadata to cache.

        Args:
            video: Video entity to save

        Returns:
            True if saved successfully, False otherwise
        """
    @abstractmethod
    def delete(self, video: Video) -> bool:
        """
        Delete video from cache.

        Args:
            video: Video entity to delete

        Returns:
            True if deleted successfully, False otherwise
        """
    @abstractmethod
    def exists(self, path: Path) -> bool:
        """
        Check if video exists in cache.

        Args:
            path: Path to check

        Returns:
            True if video exists in cache, False otherwise
        """
    @abstractmethod
    def get_cached_videos(self) -> List[Video]:
        """
        Get all cached videos.

        Returns:
            List of cached Video entities
        """
    @abstractmethod
    def clear_cache(self) -> bool:
        """
        Clear all cached video data.

        Returns:
            True if cache was cleared successfully, False otherwise
        """
    @abstractmethod
    def refresh_video(self, path: Path) -> Optional[Video]:
        """
        Refresh video metadata from file system.

        Args:
            path: Path to the video file

        Returns:
            Updated Video entity or None if refresh failed
        """
    @abstractmethod
    def get_videos_by_directory(self, directory: Path) -> List[Video]:
        """
        Get all videos in a specific directory.

        Args:
            directory: Directory to search

        Returns:
            List of Video entities in the directory
        """
    @abstractmethod
    def get_total_duration(self, videos: List[Video]) -> float:
        """
        Calculate total duration of a list of videos.

        Args:
            videos: List of videos

        Returns:
            Total duration in seconds
        """
        pass
