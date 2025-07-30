"""
Process Video Use Case

Use case for processing videos with effects and background merging.
"""

import logging
from typing import Optional
from pathlib import Path

from ...domain.entities.processing_job import ProcessingJob
from ...domain.entities.video import Video
from ...domain.entities.effect import Effect
from ...domain.value_objects.job_status import JobStatus
from ...domain.services.video_processor_interface import IVideoProcessor, ProcessingResult
from ...domain.services.video_repository_interface import IVideoRepository
from ...shared.config import AppConfig
from ...shared.exceptions import ProcessingJobException, VideoNotFoundException
from ...shared.utils import get_logger, get_performance_logger

logger = get_logger(__name__)
perf_logger = get_performance_logger()


class ProcessVideoRequest:
    """Request for video processing use case"""

    def __init__(self, main_video_path: Path, background_video_path: Path,
                 output_path: Path, effects: Optional[list] = None):
        """
        Initialize process video request.

        Args:
            main_video_path: Path to main video file
            background_video_path: Path to background video file
            output_path: Path for output video
            effects: List of effects to apply (optional)
        """
        self.main_video_path = main_video_path
        self.background_video_path = background_video_path
        self.output_path = output_path
        self.effects = effects or []


class ProcessVideoResponse:
    """Response from video processing use case"""

    def __init__(self, success: bool, job_id: Optional[str] = None,
                 output_path: Optional[Path] = None, error_message: Optional[str] = None,
                 processing_time: Optional[float] = None):
        """
        Initialize process video response.

        Args:
            success: Whether processing was successful
            job_id: ID of the processing job
            output_path: Path to output video (if successful)
            error_message: Error message (if failed)
            processing_time: Time taken for processing in seconds
        """
        self.success = success
        self.job_id = job_id
        self.output_path = output_path
        self.error_message = error_message
        self.processing_time = processing_time


class ProcessVideoUseCase:
    """Use case for processing videos"""

    def __init__(self, video_processor: IVideoProcessor,
                 video_repository: IVideoRepository, config: AppConfig):
        """
        Initialize process video use case.

        Args:
            video_processor: Video processor service
            video_repository: Video repository for data access
            config: Application configuration
        """
        self.video_processor = video_processor
        self.video_repository = video_repository
        self.config = config

    def execute(self, request: ProcessVideoRequest) -> ProcessVideoResponse:
        """
        Execute video processing use case.

        Args:
            request: Process video request

        Returns:
            Process video response
        """
        import time
        start_time = time.time()

        try:
            logger.info(f"Starting video processing: {request.main_video_path.name}")

            # Load main video
            main_video = self._load_video(request.main_video_path)
            if not main_video:
                return ProcessVideoResponse(
                    success=False,
                    error_message=f"Main video not found: {request.main_video_path}"
                )

            # Load background video
            background_video = self._load_video(request.background_video_path)
            if not background_video:
                return ProcessVideoResponse(
                    success=False,
                    error_message=f"Background video not found: {request.background_video_path}"
                )

            # Create effects from request
            effects = self._create_effects(request.effects)

            # Create processing job
            job = ProcessingJob(
                main_video=main_video,
                background_video=background_video,
                effects=effects,
                output_path=request.output_path
            )

            # Validate job
            validation_errors = job.validate_for_processing()
            if validation_errors:
                error_msg = f"Job validation failed: {'; '.join(validation_errors)}"
                return ProcessVideoResponse(
                    success=False,
                    job_id=job.id,
                    error_message=error_msg
                )

            # Update job status
            job.update_status(JobStatus.PROCESSING)

            # Process video
            result = self.video_processor.process_video(job)

            processing_time = time.time() - start_time

            if result.is_success():
                # Update job status
                job.update_status(JobStatus.COMPLETED)
                job.update_progress(100.0)

                # Log performance metrics
                perf_logger.log_processing_time(
                    "video_processing_use_case",
                    processing_time,
                    str(request.main_video_path),
                    job_id=job.id,
                    effects_count=len(effects),
                    output_size=result.output_path.stat().st_size if result.output_path else 0
                )

                logger.info(f"Video processing completed successfully: {job.id}")

                return ProcessVideoResponse(
                    success=True,
                    job_id=job.id,
                    output_path=result.output_path,
                    processing_time=processing_time
                )
            else:
                # Update job status
                job.update_status(JobStatus.FAILED, result.get_error())

                logger.error(f"Video processing failed: {job.id} - {result.get_error()}")

                return ProcessVideoResponse(
                    success=False,
                    job_id=job.id,
                    error_message=result.get_error(),
                    processing_time=processing_time
                )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error in video processing use case: {e}")

            return ProcessVideoResponse(
                success=False,
                error_message=str(e),
                processing_time=processing_time
            )

    def _load_video(self, video_path: Path) -> Optional[Video]:
        """Load video from repository or file system"""
        try:
            # Try to get from repository first (with caching)
            video = self.video_repository.get_by_path(video_path)
            if video:
                return video

            # If not in repository, try to get video info and create Video entity
            video_info = self.video_processor.get_video_info(video_path)
            if video_info:
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

                # Save to repository for caching
                self.video_repository.save(video)
                return video

            return None

        except Exception as e:
            logger.error(f"Error loading video {video_path}: {e}")
            return None

    def _create_effects(self, effect_configs: list) -> list:
        """Create Effect entities from configuration"""
        effects = []

        for effect_config in effect_configs:
            try:
                if isinstance(effect_config, dict):
                    # Create effect from dictionary
                    from ...domain.value_objects.effect_type import EffectType

                    effect_type = EffectType(effect_config.get('type', 'none'))
                    duration = effect_config.get('duration', 2.0)
                    parameters = effect_config.get('parameters', {})

                    effect = Effect(
                        type=effect_type,
                        duration=duration,
                        parameters=parameters
                    )
                    effects.append(effect)

                elif isinstance(effect_config, Effect):
                    # Already an Effect entity
                    effects.append(effect_config)

            except Exception as e:
                logger.warning(f"Error creating effect from config {effect_config}: {e}")
                continue

        return effects
