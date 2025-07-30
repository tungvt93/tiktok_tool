"""
Create Processing Job Use Case

Use case for creating and validating video processing jobs.
"""

import logging
from typing import List, Optional
from pathlib import Path

from ...domain.entities.processing_job import ProcessingJob
from ...domain.entities.video import Video
from ...domain.entities.effect import Effect
from ...domain.value_objects.effect_type import EffectType
from ...domain.services.video_repository_interface import IVideoRepository
from ...shared.config import AppConfig
from ...shared.exceptions import ValidationException
from ...shared.utils import get_logger

logger = get_logger(__name__)


class CreateJobRequest:
    """Request for creating a processing job"""

    def __init__(self, main_video_path: Path, background_video_path: Path,
                 output_path: Path, effects: Optional[List[dict]] = None):
        """
        Initialize create job request.

        Args:
            main_video_path: Path to main video file
            background_video_path: Path to background video file
            output_path: Path for output video
            effects: List of effect configurations
        """
        self.main_video_path = main_video_path
        self.background_video_path = background_video_path
        self.output_path = output_path
        self.effects = effects or []


class CreateJobResponse:
    """Response from create processing job use case"""

    def __init__(self, success: bool, job: Optional[ProcessingJob] = None,
                 validation_errors: Optional[List[str]] = None,
                 error_message: Optional[str] = None):
        """
        Initialize create job response.

        Args:
            success: Whether job creation was successful
            job: Created processing job (if successful)
            validation_errors: List of validation errors
            error_message: Error message (if failed)
        """
        self.success = success
        self.job = job
        self.validation_errors = validation_errors or []
        self.error_message = error_message


class CreateProcessingJobUseCase:
    """Use case for creating processing jobs"""

    def __init__(self, video_repository: IVideoRepository, config: AppConfig):
        """
        Initialize create processing job use case.

        Args:
            video_repository: Video repository for data access
            config: Application configuration
        """
        self.video_repository = video_repository
        self.config = config

    def execute(self, request: CreateJobRequest) -> CreateJobResponse:
        """
        Execute create processing job use case.

        Args:
            request: Create job request

        Returns:
            Create job response
        """
        try:
            logger.info(f"Creating processing job: {request.main_video_path.name}")

            # Validate request
            validation_errors = self._validate_request(request)
            if validation_errors:
                return CreateJobResponse(
                    success=False,
                    validation_errors=validation_errors,
                    error_message="Request validation failed"
                )

            # Load videos
            main_video = self._load_video(request.main_video_path)
            if not main_video:
                return CreateJobResponse(
                    success=False,
                    error_message=f"Main video not found: {request.main_video_path}"
                )

            background_video = self._load_video(request.background_video_path)
            if not background_video:
                return CreateJobResponse(
                    success=False,
                    error_message=f"Background video not found: {request.background_video_path}"
                )

            # Create effects
            effects = self._create_effects(request.effects)

            # Create processing job
            job = ProcessingJob(
                main_video=main_video,
                background_video=background_video,
                effects=effects,
                output_path=request.output_path
            )

            # Validate job
            job_validation_errors = job.validate_for_processing()
            if job_validation_errors:
                return CreateJobResponse(
                    success=False,
                    job=job,
                    validation_errors=job_validation_errors,
                    error_message="Job validation failed"
                )

            logger.info(f"Processing job created successfully: {job.id}")

            return CreateJobResponse(
                success=True,
                job=job
            )

        except Exception as e:
            logger.error(f"Error creating processing job: {e}")
            return CreateJobResponse(
                success=False,
                error_message=str(e)
            )

    def _validate_request(self, request: CreateJobRequest) -> List[str]:
        """Validate create job request"""
        errors = []

        # Validate paths
        if not request.main_video_path:
            errors.append("Main video path is required")
        elif not isinstance(request.main_video_path, Path):
            errors.append("Main video path must be a Path object")

        if not request.background_video_path:
            errors.append("Background video path is required")
        elif not isinstance(request.background_video_path, Path):
            errors.append("Background video path must be a Path object")

        if not request.output_path:
            errors.append("Output path is required")
        elif not isinstance(request.output_path, Path):
            errors.append("Output path must be a Path object")

        # Validate output path doesn't already exist
        if request.output_path and request.output_path.exists():
            errors.append(f"Output file already exists: {request.output_path}")

        # Validate effects configuration
        if request.effects:
            for i, effect_config in enumerate(request.effects):
                if not isinstance(effect_config, dict):
                    errors.append(f"Effect {i}: must be a dictionary")
                    continue

                if 'type' not in effect_config:
                    errors.append(f"Effect {i}: type is required")
                    continue

                try:
                    EffectType(effect_config['type'])
                except ValueError:
                    errors.append(f"Effect {i}: invalid effect type '{effect_config['type']}'")

                duration = effect_config.get('duration')
                if duration is not None:
                    if not isinstance(duration, (int, float)) or duration <= 0:
                        errors.append(f"Effect {i}: duration must be a positive number")

        return errors

    def _load_video(self, video_path: Path) -> Optional[Video]:
        """Load video from repository"""
        try:
            return self.video_repository.get_by_path(video_path)
        except Exception as e:
            logger.error(f"Error loading video {video_path}: {e}")
            return None

    def _create_effects(self, effect_configs: List[dict]) -> List[Effect]:
        """Create Effect entities from configuration"""
        effects = []

        for effect_config in effect_configs:
            try:
                effect_type = EffectType(effect_config['type'])
                duration = effect_config.get('duration', self.config.video.default_effect_duration)
                parameters = effect_config.get('parameters', {})

                effect = Effect(
                    type=effect_type,
                    duration=duration,
                    parameters=parameters
                )

                effects.append(effect)

            except Exception as e:
                logger.warning(f"Error creating effect from config {effect_config}: {e}")
                continue

        return effects

    def create_default_job(self, main_video_path: Path, background_video_path: Path,
                          output_path: Path) -> CreateJobResponse:
        """
        Create a processing job with default settings.

        Args:
            main_video_path: Path to main video
            background_video_path: Path to background video
            output_path: Path for output video

        Returns:
            Create job response
        """
        # Create request with default effect
        default_effects = []

        # Add default fade-in effect if configured
        if self.config.video.default_effect_duration > 0:
            default_effects.append({
                'type': 'fade_in',
                'duration': self.config.video.default_effect_duration
            })

        request = CreateJobRequest(
            main_video_path=main_video_path,
            background_video_path=background_video_path,
            output_path=output_path,
            effects=default_effects
        )

        return self.execute(request)

    def create_job_with_random_effect(self, main_video_path: Path,
                                    background_video_path: Path,
                                    output_path: Path) -> CreateJobResponse:
        """
        Create a processing job with a random effect.

        Args:
            main_video_path: Path to main video
            background_video_path: Path to background video
            output_path: Path for output video

        Returns:
            Create job response
        """
        import random

        # Available effects for random selection
        available_effects = [
            {'type': 'fade_in', 'duration': 2.0},
            {'type': 'slide_right_to_left', 'duration': 1.5},
            {'type': 'slide_left_to_right', 'duration': 1.5},
            {'type': 'slide_top_to_bottom', 'duration': 1.5},
            {'type': 'slide_bottom_to_top', 'duration': 1.5},
            {'type': 'circle_expand', 'duration': 2.0},
            {'type': 'circle_contract', 'duration': 2.0}
        ]

        # Select random effect
        random_effect = random.choice(available_effects)

        request = CreateJobRequest(
            main_video_path=main_video_path,
            background_video_path=background_video_path,
            output_path=output_path,
            effects=[random_effect]
        )

        return self.execute(request)
