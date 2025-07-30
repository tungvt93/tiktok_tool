"""
Video Processor Interface

Defines the contract for video processing operations.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path

from ..entities.video import Video
from ..entities.processing_job import ProcessingJob
from ..value_objects.dimensions import Dimensions


class ProcessingResult:
    """Result of a video processing operation"""

    def __init__(self, success: bool, output_path: Optional[Path] = None,
                 error_message: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        self.success = success
        self.output_path = output_path
        self.error_message = error_message
        self.metadata = metadata or {}

    def is_success(self) -> bool:
        """Check if processing was successful"""
        return self.success

    def get_error(self) -> Optional[str]:
        """Get error message if processing failed"""
        return self.error_message


class VideoInfo:
    """Video information extracted from file"""

    def __init__(self, duration: float, dimensions: Dimensions,
                 codec: str, bitrate: int, metadata: Optional[Dict[str, Any]] = None):
        self.duration = duration
        self.dimensions = dimensions
        self.codec = codec
        self.bitrate = bitrate
        self.metadata = metadata or {}


class IVideoProcessor(ABC):
    """Interface for video processing operations"""

    @abstractmethod
    def process_video(self, job: ProcessingJob) -> ProcessingResult:
        """
        Process a video according to the job specification.

        Args:
            job: The processing job containing all configuration

        Returns:
            ProcessingResult with success status and output information
        """
    @abstractmethod
    def get_video_info(self, video_path: Path) -> Optional[VideoInfo]:
        """
        Extract video information from file.

        Args:
            video_path: Path to the video file

        Returns:
            VideoInfo object or None if extraction fails
        """
    @abstractmethod
    def validate_video_file(self, video_path: Path) -> bool:
        """
        Validate that a file is a valid video.

        Args:
            video_path: Path to the video file

        Returns:
            True if file is a valid video, False otherwise
        """
    @abstractmethod
    def estimate_processing_time(self, job: ProcessingJob) -> float:
        """
        Estimate processing time for a job in seconds.

        Args:
            job: The processing job to estimate

        Returns:
            Estimated processing time in seconds
        """
    @abstractmethod
    def cancel_processing(self, job_id: str) -> bool:
        """
        Cancel an ongoing processing job.

        Args:
            job_id: ID of the job to cancel

        Returns:
            True if cancellation was successful, False otherwise
        """
        pass
