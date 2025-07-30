"""
Get Videos Use Case

Use case for discovering and retrieving video files.
"""

import logging
from typing import List, Optional
from pathlib import Path

from ...domain.entities.video import Video
from ...domain.services.video_repository_interface import IVideoRepository, VideoSearchCriteria
from ...domain.services.file_repository_interface import IFileRepository, FileSearchCriteria
from ...shared.config import AppConfig
from ...shared.utils import get_logger

logger = get_logger(__name__)


class GetVideosRequest:
    """Request for get videos use case"""

    def __init__(self, directory: Optional[Path] = None, pattern: str = "*.mp4",
                 recursive: bool = False, refresh_cache: bool = False,
                 min_duration: Optional[float] = None, max_duration: Optional[float] = None):
        """
        Initialize get videos request.

        Args:
            directory: Directory to search (optional, uses config default)
            pattern: File pattern to match
            recursive: Whether to search recursively
            refresh_cache: Whether to refresh cached video data
            min_duration: Minimum video duration filter
            max_duration: Maximum video duration filter
        """
        self.directory = directory
        self.pattern = pattern
        self.recursive = recursive
        self.refresh_cache = refresh_cache
        self.min_duration = min_duration
        self.max_duration = max_duration


class GetVideosResponse:
    """Response from get videos use case"""

    def __init__(self, success: bool, videos: List[Video],
                 total_count: int, total_duration: float,
                 error_message: Optional[str] = None):
        """
        Initialize get videos response.

        Args:
            success: Whether operation was successful
            videos: List of found videos
            total_count: Total number of videos found
            total_duration: Total duration of all videos
            error_message: Error message (if failed)
        """
        self.success = success
        self.videos = videos
        self.total_count = total_count
        self.total_duration = total_duration
        self.error_message = error_message


class GetVideosUseCase:
    """Use case for getting videos"""

    def __init__(self, video_repository: IVideoRepository,
                 file_repository: IFileRepository, config: AppConfig):
        """
        Initialize get videos use case.

        Args:
            video_repository: Video repository for data access
            file_repository: File repository for file system operations
            config: Application configuration
        """
        self.video_repository = video_repository
        self.file_repository = file_repository
        self.config = config

    def execute(self, request: GetVideosRequest) -> GetVideosResponse:
        """
        Execute get videos use case.

        Args:
            request: Get videos request

        Returns:
            Get videos response
        """
        try:
            logger.info(f"Getting videos from directory: {request.directory or 'default'}")

            # Determine search directory
            search_directory = request.directory or self.config.paths.input_dir

            if request.refresh_cache:
                # Clear cache and reload from file system
                videos = self._load_videos_from_filesystem(request, search_directory)
            else:
                # Try to get from cache first
                videos = self._get_videos_with_cache(request, search_directory)

            # Apply filters
            filtered_videos = self._apply_filters(videos, request)

            # Calculate totals
            total_count = len(filtered_videos)
            total_duration = self.video_repository.get_total_duration(filtered_videos)

            logger.info(f"Found {total_count} videos with total duration {total_duration:.1f}s")

            return GetVideosResponse(
                success=True,
                videos=filtered_videos,
                total_count=total_count,
                total_duration=total_duration
            )

        except Exception as e:
            logger.error(f"Error in get videos use case: {e}")
            return GetVideosResponse(
                success=False,
                videos=[],
                total_count=0,
                total_duration=0.0,
                error_message=str(e)
            )

    def _get_videos_with_cache(self, request: GetVideosRequest,
                              search_directory: Path) -> List[Video]:
        """Get videos using cache when possible"""
        # Create search criteria
        criteria = VideoSearchCriteria(
            directory=search_directory,
            min_duration=request.min_duration,
            max_duration=request.max_duration
        )

        # Get videos from repository (uses cache)
        videos = self.video_repository.get_all(criteria)

        # If no cached videos found, load from file system
        if not videos:
            logger.info("No cached videos found, loading from file system")
            videos = self._load_videos_from_filesystem(request, search_directory)

        return videos

    def _load_videos_from_filesystem(self, request: GetVideosRequest,
                                   search_directory: Path) -> List[Video]:
        """Load videos directly from file system"""
        # Create file search criteria
        file_criteria = FileSearchCriteria(
            directory=search_directory,
            pattern=request.pattern,
            recursive=request.recursive
        )

        # Find video files
        video_paths = self.file_repository.find_video_files(file_criteria)

        # Load video metadata for each file
        videos = []
        for video_path in video_paths:
            video = self.video_repository.get_by_path(video_path)
            if video:
                videos.append(video)
            else:
                logger.warning(f"Could not load video metadata: {video_path}")

        return videos

    def _apply_filters(self, videos: List[Video], request: GetVideosRequest) -> List[Video]:
        """Apply additional filters to video list"""
        filtered_videos = videos

        # Duration filters
        if request.min_duration is not None:
            filtered_videos = [v for v in filtered_videos if v.duration >= request.min_duration]

        if request.max_duration is not None:
            filtered_videos = [v for v in filtered_videos if v.duration <= request.max_duration]

        return filtered_videos
