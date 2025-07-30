"""
Video Repository Implementation

Repository for video data access with caching support.
"""

import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ...domain.entities.video import Video
from ...domain.value_objects.dimensions import Dimensions
from ...domain.services.video_repository_interface import IVideoRepository, VideoSearchCriteria
from ...domain.services.file_repository_interface import IFileRepository, FileSearchCriteria
from ...domain.services.cache_service_interface import ICacheService
from ...shared.exceptions import VideoNotFoundException, VideoCorruptedException

logger = logging.getLogger(__name__)


class VideoRepository(IVideoRepository):
    """Video repository with caching support"""

    def __init__(self, file_repository: IFileRepository, cache_service: ICacheService):
        """
        Initialize video repository.

        Args:
            file_repository: File repository for file system operations
            cache_service: Cache service for metadata caching
        """
        self.file_repository = file_repository
        self.cache_service = cache_service

    def get_by_path(self, path: Path) -> Optional[Video]:
        """
        Get video by file path.

        Args:
            path: Path to the video file

        Returns:
            Video entity or None if not found
        """
        try:
            # Check if file exists
            if not self.file_repository.file_exists(path):
                logger.warning(f"Video file not found: {path}")
                return None

            # Try to get from cache first
            cache_key = f"video:{str(path)}"
            cached_data = self.cache_service.get(cache_key)

            if cached_data:
                try:
                    video = self._deserialize_video(cached_data)
                    # Verify file still exists and hasn't changed
                    if self._is_cache_valid(video, path):
                        logger.debug(f"Video loaded from cache: {path}")
                        return video
                    else:
                        # Cache is stale, remove it
                        self.cache_service.delete(cache_key)
                        logger.debug(f"Cache invalidated for: {path}")
                except Exception as e:
                    logger.warning(f"Error deserializing cached video {path}: {e}")
                    self.cache_service.delete(cache_key)

            # Load video metadata from file system
            video = self._load_video_from_file(path)
            if video:
                # Cache the video metadata
                self._cache_video(video)
                logger.debug(f"Video loaded from file system: {path}")

            return video

        except Exception as e:
            logger.error(f"Error getting video by path {path}: {e}")
            return None

    def get_all(self, criteria: Optional[VideoSearchCriteria] = None) -> List[Video]:
        """
        Get all videos matching the criteria.

        Args:
            criteria: Search criteria (optional)

        Returns:
            List of Video entities
        """
        try:
            videos = []

            if criteria and criteria.directory:
                # Search in specific directory
                search_criteria = FileSearchCriteria(
                    directory=criteria.directory,
                    pattern="*.mp4",  # Default pattern
                    recursive=True
                )
                video_paths = self.file_repository.find_video_files(search_criteria)
            else:
                # Get all cached videos and verify they still exist
                cached_videos = self.get_cached_videos()
                video_paths = [video.path for video in cached_videos
                             if self.file_repository.file_exists(video.path)]

            # Load videos
            for path in video_paths:
                video = self.get_by_path(path)
                if video and self._matches_criteria(video, criteria):
                    videos.append(video)

            # Sort by filename for consistent ordering
            videos.sort(key=lambda v: v.filename)

            logger.info(f"Found {len(videos)} videos matching criteria")
            return videos

        except Exception as e:
            logger.error(f"Error getting all videos: {e}")
            return []

    def save(self, video: Video) -> bool:
        """
        Save video metadata to cache.

        Args:
            video: Video entity to save

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            video.mark_as_cached()
            self._cache_video(video)
            logger.debug(f"Video saved to cache: {video.path}")
            return True
        except Exception as e:
            logger.error(f"Error saving video to cache {video.path}: {e}")
            return False

    def delete(self, video: Video) -> bool:
        """
        Delete video from cache.

        Args:
            video: Video entity to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            cache_key = f"video:{str(video.path)}"
            result = self.cache_service.delete(cache_key)
            if result:
                logger.debug(f"Video deleted from cache: {video.path}")
            return result
        except Exception as e:
            logger.error(f"Error deleting video from cache {video.path}: {e}")
            return False

    def exists(self, path: Path) -> bool:
        """
        Check if video exists in cache.

        Args:
            path: Path to check

        Returns:
            True if video exists in cache, False otherwise
        """
        try:
            cache_key = f"video:{str(path)}"
            return self.cache_service.exists(cache_key)
        except Exception as e:
            logger.warning(f"Error checking video existence in cache {path}: {e}")
            return False

    def get_cached_videos(self) -> List[Video]:
        """
        Get all cached videos.

        Returns:
            List of cached Video entities
        """
        try:
            videos = []
            cache_keys = self.cache_service.get_keys("video:*")

            for cache_key in cache_keys:
                cached_data = self.cache_service.get(cache_key)
                if cached_data:
                    try:
                        video = self._deserialize_video(cached_data)
                        videos.append(video)
                    except Exception as e:
                        logger.warning(f"Error deserializing cached video {cache_key}: {e}")
                        # Remove corrupted cache entry
                        self.cache_service.delete(cache_key)

            logger.debug(f"Retrieved {len(videos)} cached videos")
            return videos

        except Exception as e:
            logger.error(f"Error getting cached videos: {e}")
            return []

    def clear_cache(self) -> bool:
        """
        Clear all cached video data.

        Returns:
            True if cache was cleared successfully, False otherwise
        """
        try:
            # Get all video cache keys
            cache_keys = self.cache_service.get_keys("video:*")

            # Delete each video cache entry
            deleted_count = 0
            for cache_key in cache_keys:
                if self.cache_service.delete(cache_key):
                    deleted_count += 1

            logger.info(f"Cleared {deleted_count} video cache entries")
            return deleted_count == len(cache_keys)

        except Exception as e:
            logger.error(f"Error clearing video cache: {e}")
            return False

    def refresh_video(self, path: Path) -> Optional[Video]:
        """
        Refresh video metadata from file system.

        Args:
            path: Path to the video file

        Returns:
            Updated Video entity or None if refresh failed
        """
        try:
            # Remove from cache first
            cache_key = f"video:{str(path)}"
            self.cache_service.delete(cache_key)

            # Load fresh from file system
            video = self._load_video_from_file(path)
            if video:
                self._cache_video(video)
                logger.debug(f"Video refreshed: {path}")

            return video

        except Exception as e:
            logger.error(f"Error refreshing video {path}: {e}")
            return None

    def get_videos_by_directory(self, directory: Path) -> List[Video]:
        """
        Get all videos in a specific directory.

        Args:
            directory: Directory to search

        Returns:
            List of Video entities in the directory
        """
        criteria = VideoSearchCriteria(directory=directory)
        return self.get_all(criteria)

    def get_total_duration(self, videos: List[Video]) -> float:
        """
        Calculate total duration of a list of videos.

        Args:
            videos: List of videos

        Returns:
            Total duration in seconds
        """
        return sum(video.duration for video in videos)

    def _load_video_from_file(self, path: Path) -> Optional[Video]:
        """
        Load video metadata from file system.

        This is a placeholder implementation. In a real system, this would
        use FFprobe or similar tool to extract video metadata.

        Args:
            path: Path to video file

        Returns:
            Video entity or None if loading failed
        """
        try:
            if not self.file_repository.file_exists(path):
                raise VideoNotFoundException(path)

            # Get file size
            file_size = self.file_repository.get_file_size(path)
            if file_size == 0:
                raise VideoCorruptedException(path, "File is empty")

            # For now, create a basic video entity with placeholder values
            # In real implementation, this would use FFprobe to get actual metadata
            video = Video(
                path=path,
                duration=60.0,  # Placeholder duration
                dimensions=Dimensions(1920, 1080),  # Placeholder dimensions
                metadata={
                    'file_size': file_size,
                    'format': path.suffix.lower(),
                    'loaded_at': datetime.now().isoformat()
                }
            )

            return video

        except Exception as e:
            logger.error(f"Error loading video from file {path}: {e}")
            return None

    def _cache_video(self, video: Video) -> None:
        """Cache video metadata"""
        try:
            cache_key = f"video:{str(video.path)}"
            cache_data = self._serialize_video(video)

            # Cache for 24 hours by default
            from datetime import timedelta
            ttl = timedelta(hours=24)

            self.cache_service.set(cache_key, cache_data, ttl)
        except Exception as e:
            logger.warning(f"Error caching video {video.path}: {e}")

    def _serialize_video(self, video: Video) -> dict:
        """Serialize video to dictionary for caching"""
        return {
            'path': str(video.path),
            'duration': video.duration,
            'dimensions': {
                'width': video.dimensions.width,
                'height': video.dimensions.height
            },
            'metadata': video.metadata,
            'created_at': video.created_at.isoformat(),
            'cached_at': video.cached_at.isoformat() if video.cached_at else None
        }

    def _deserialize_video(self, data: dict) -> Video:
        """Deserialize video from cached dictionary"""
        path = Path(data['path'])
        dimensions = Dimensions(
            width=data['dimensions']['width'],
            height=data['dimensions']['height']
        )

        created_at = datetime.fromisoformat(data['created_at'])
        cached_at = None
        if data.get('cached_at'):
            cached_at = datetime.fromisoformat(data['cached_at'])

        video = Video(
            path=path,
            duration=data['duration'],
            dimensions=dimensions,
            metadata=data.get('metadata', {}),
            created_at=created_at,
            cached_at=cached_at
        )

        return video

    def _is_cache_valid(self, video: Video, path: Path) -> bool:
        """Check if cached video data is still valid"""
        try:
            # Check if file still exists
            if not self.file_repository.file_exists(path):
                return False

            # Check if file size changed (simple modification check)
            current_size = self.file_repository.get_file_size(path)
            cached_size = video.get_metadata_value('file_size')

            if current_size != cached_size:
                return False

            # Check cache age (invalidate after 24 hours)
            if video.cached_at:
                age = datetime.now() - video.cached_at
                if age.total_seconds() > 24 * 60 * 60:  # 24 hours
                    return False

            return True

        except Exception as e:
            logger.warning(f"Error validating cache for {path}: {e}")
            return False

    def _matches_criteria(self, video: Video, criteria: Optional[VideoSearchCriteria]) -> bool:
        """Check if video matches search criteria"""
        if not criteria:
            return True

        # Check duration range
        if criteria.min_duration and video.duration < criteria.min_duration:
            return False
        if criteria.max_duration and video.duration > criteria.max_duration:
            return False

        # Check dimensions
        if criteria.dimensions and video.dimensions != criteria.dimensions:
            return False

        # Check extensions
        if criteria.extensions and video.extension not in criteria.extensions:
            return False

        return True
