"""
Video Service

Application service for video-related operations.
"""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from ...domain.entities.video import Video
from ...domain.services.video_repository_interface import IVideoRepository, VideoSearchCriteria
from ...domain.services.file_repository_interface import IFileRepository, FileSearchCriteria
from ...domain.services.video_processor_interface import IVideoProcessor
from ...shared.config import AppConfig
from ...shared.utils import get_logger, get_performance_logger
from ...shared.exceptions import VideoNotFoundException

logger = get_logger(__name__)
perf_logger = get_performance_logger()


class VideoService:
    """Application service for video operations"""

    def __init__(self, video_repository: IVideoRepository,
                 file_repository: IFileRepository,
                 video_processor: IVideoProcessor,
                 config: AppConfig):
        """
        Initialize video service.

        Args:
            video_repository: Video repository for data access
            file_repository: File repository for file operations
            video_processor: Video processor for metadata extraction
            config: Application configuration
        """
        self.video_repository = video_repository
        self.file_repository = file_repository
        self.video_processor = video_processor
        self.config = config

    def get_videos_from_directory(self, directory: Optional[Path] = None,
                                 pattern: str = "*.mp4",
                                 recursive: bool = False) -> List[Video]:
        """
        Get all videos from a directory.

        Args:
            directory: Directory to search (uses config default if None)
            pattern: File pattern to match
            recursive: Whether to search recursively

        Returns:
            List of Video entities
        """
        try:
            search_dir = directory or self.config.paths.input_dir
            logger.info(f"Getting videos from directory: {search_dir}")

            # Create search criteria
            criteria = VideoSearchCriteria(directory=search_dir)

            # Get videos from repository (with caching)
            videos = self.video_repository.get_all(criteria)

            # If no cached videos, scan file system
            if not videos:
                videos = self._scan_directory_for_videos(search_dir, pattern, recursive)

            logger.info(f"Found {len(videos)} videos in {search_dir}")
            return videos

        except Exception as e:
            logger.error(f"Error getting videos from directory {directory}: {e}")
            return []

    def get_background_videos(self) -> List[Video]:
        """
        Get all background videos from configured directory.

        Returns:
            List of background Video entities
        """
        return self.get_videos_from_directory(
            directory=self.config.paths.background_dir,
            pattern=self.config.paths.background_pattern
        )

    def get_video_by_path(self, video_path: Path) -> Optional[Video]:
        """
        Get video by file path.

        Args:
            video_path: Path to video file

        Returns:
            Video entity or None if not found
        """
        try:
            return self.video_repository.get_by_path(video_path)
        except Exception as e:
            logger.error(f"Error getting video by path {video_path}: {e}")
            return None

    def refresh_video_cache(self, video_path: Optional[Path] = None) -> bool:
        """
        Refresh video cache for specific video or all videos.

        Args:
            video_path: Specific video to refresh (None for all)

        Returns:
            True if refresh was successful
        """
        try:
            if video_path:
                # Refresh specific video
                refreshed_video = self.video_repository.refresh_video(video_path)
                success = refreshed_video is not None
                logger.info(f"Refreshed video cache: {video_path} - {'Success' if success else 'Failed'}")
                return success
            else:
                # Clear entire cache
                success = self.video_repository.clear_cache()
                logger.info(f"Cleared video cache - {'Success' if success else 'Failed'}")
                return success

        except Exception as e:
            logger.error(f"Error refreshing video cache: {e}")
            return False

    def validate_video_file(self, video_path: Path) -> bool:
        """
        Validate that a file is a valid video.

        Args:
            video_path: Path to video file

        Returns:
            True if file is a valid video
        """
        try:
            return self.video_processor.validate_video_file(video_path)
        except Exception as e:
            logger.warning(f"Error validating video file {video_path}: {e}")
            return False

    def get_video_statistics(self, videos: Optional[List[Video]] = None) -> Dict[str, Any]:
        """
        Get statistics about videos.

        Args:
            videos: List of videos to analyze (None for all cached videos)

        Returns:
            Dictionary with video statistics
        """
        try:
            if videos is None:
                videos = self.video_repository.get_cached_videos()

            if not videos:
                return {
                    'total_count': 0,
                    'total_duration': 0.0,
                    'average_duration': 0.0,
                    'total_size': 0,
                    'formats': {},
                    'resolutions': {}
                }

            # Calculate statistics
            total_count = len(videos)
            total_duration = sum(video.duration for video in videos)
            average_duration = total_duration / total_count if total_count > 0 else 0.0

            # Calculate total file size
            total_size = 0
            for video in videos:
                try:
                    size = self.file_repository.get_file_size(video.path)
                    if size:
                        total_size += size
                except Exception:
                    continue

            # Analyze formats
            formats = {}
            for video in videos:
                ext = video.extension
                formats[ext] = formats.get(ext, 0) + 1

            # Analyze resolutions
            resolutions = {}
            for video in videos:
                resolution = f"{video.dimensions.width}x{video.dimensions.height}"
                resolutions[resolution] = resolutions.get(resolution, 0) + 1

            return {
                'total_count': total_count,
                'total_duration': round(total_duration, 2),
                'average_duration': round(average_duration, 2),
                'total_size': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'formats': formats,
                'resolutions': resolutions
            }

        except Exception as e:
            logger.error(f"Error calculating video statistics: {e}")
            return {}

    def find_videos_by_criteria(self, min_duration: Optional[float] = None,
                               max_duration: Optional[float] = None,
                               extensions: Optional[List[str]] = None) -> List[Video]:
        """
        Find videos matching specific criteria.

        Args:
            min_duration: Minimum duration in seconds
            max_duration: Maximum duration in seconds
            extensions: List of file extensions to include

        Returns:
            List of matching Video entities
        """
        try:
            criteria = VideoSearchCriteria(
                min_duration=min_duration,
                max_duration=max_duration,
                extensions=extensions
            )

            videos = self.video_repository.get_all(criteria)
            logger.info(f"Found {len(videos)} videos matching criteria")
            return videos

        except Exception as e:
            logger.error(f"Error finding videos by criteria: {e}")
            return []

    def _scan_directory_for_videos(self, directory: Path, pattern: str,
                                  recursive: bool) -> List[Video]:
        """Scan directory for video files and create Video entities"""
        try:
            # Find video files
            file_criteria = FileSearchCriteria(
                directory=directory,
                pattern=pattern,
                recursive=recursive
            )

            video_paths = self.file_repository.find_video_files(file_criteria)

            # Create Video entities
            videos = []
            for video_path in video_paths:
                video = self._create_video_from_path(video_path)
                if video:
                    videos.append(video)
                    # Save to repository for caching
                    self.video_repository.save(video)

            return videos

        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
            return []

    def _create_video_from_path(self, video_path: Path) -> Optional[Video]:
        """Create Video entity from file path"""
        try:
            # Get video info using processor
            video_info = self.video_processor.get_video_info(video_path)
            if not video_info:
                logger.warning(f"Could not get video info for: {video_path}")
                return None

            # Create Video entity
            video = Video(
                path=video_path,
                duration=video_info.duration,
                dimensions=video_info.dimensions,
                metadata={
                    'codec': video_info.codec,
                    'bitrate': video_info.bitrate,
                    **video_info.metadata
                }
            )

            return video

        except Exception as e:
            logger.error(f"Error creating video from path {video_path}: {e}")
            return None
