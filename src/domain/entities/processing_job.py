"""
Processing Job Entity

Represents a video processing job with all its configuration and status.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from .video import Video
from .effect import Effect
from ..value_objects.job_status import JobStatus


@dataclass
class ProcessingJob:
    """Processing job entity representing a complete video processing task"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    main_video: Optional[Video] = None
    background_video: Optional[Video] = None
    effects: List[Effect] = field(default_factory=list)
    output_path: Optional[Path] = None
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate job properties after initialization"""
        if self.progress < 0 or self.progress > 100:
            raise ValueError(f"Progress must be between 0 and 100, got {self.progress}")

    def validate_for_processing(self) -> List[str]:
        """Validate that job is ready for processing, return list of errors"""
        errors = []

        if not self.main_video:
            errors.append("Main video is required")
        elif not self.main_video.path.exists():
            errors.append(f"Main video file does not exist: {self.main_video.path}")

        if not self.background_video:
            errors.append("Background video is required")
        elif not self.background_video.path.exists():
            errors.append(f"Background video file does not exist: {self.background_video.path}")

        if not self.output_path:
            errors.append("Output path is required")
        elif self.output_path.exists():
            errors.append(f"Output file already exists: {self.output_path}")

        # Validate effects
        for i, effect in enumerate(self.effects):
            try:
                effect._validate()
            except ValueError as e:
                errors.append(f"Effect {i}: {str(e)}")

        return errors

    def is_valid_for_processing(self) -> bool:
        """Check if job is valid for processing"""
        return len(self.validate_for_processing()) == 0

    def add_effect(self, effect: Effect) -> None:
        """Add an effect to the job"""
        self.effects.append(effect)

    def remove_effect(self, effect: Effect) -> bool:
        """Remove an effect from the job, return True if removed"""
        try:
            self.effects.remove(effect)
            return True
        except ValueError:
            return False

    def clear_effects(self) -> None:
        """Remove all effects from the job"""
        self.effects.clear()

    def update_status(self, new_status: JobStatus, error_message: Optional[str] = None) -> bool:
        """Update job status with validation"""
        if not self.status.can_transition_to(new_status):
            return False

        old_status = self.status
        self.status = new_status

        # Update timestamps
        if new_status == JobStatus.PROCESSING and old_status != JobStatus.PROCESSING:
            self.started_at = datetime.now()
        elif new_status.is_terminal() and not self.completed_at:
            self.completed_at = datetime.now()

        # Handle error message
        if new_status == JobStatus.FAILED:
            self.error_message = error_message
        elif new_status == JobStatus.COMPLETED:
            self.error_message = None  # Clear any previous error

        return True

    def update_progress(self, progress: float) -> None:
        """Update job progress (0-100)"""
        if progress < 0 or progress > 100:
            raise ValueError(f"Progress must be between 0 and 100, got {progress}")
        self.progress = progress

    def get_estimated_duration(self) -> float:
        """Get estimated processing duration in seconds"""
        if not self.main_video:
            return 0.0

        base_duration = self.main_video.duration

        # Add effect processing time
        effect_time = sum(
            effect.get_estimated_processing_time(base_duration)
            for effect in self.effects
        )

        # Add base processing overhead (merging, encoding)
        base_overhead = base_duration * 0.5

        return base_overhead + effect_time

    def get_processing_time(self) -> Optional[float]:
        """Get actual processing time in seconds if completed"""
        if not self.started_at or not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """Get metadata value with default"""
        return self.metadata.get(key, default)

    def set_metadata_value(self, key: str, value: Any) -> None:
        """Set metadata value"""
        self.metadata[key] = value

    def reset_for_retry(self) -> None:
        """Reset job for retry (clear timestamps and error)"""
        self.status = JobStatus.PENDING
        self.progress = 0.0
        self.started_at = None
        self.completed_at = None
        self.error_message = None

    def __str__(self) -> str:
        """String representation"""
        main_name = self.main_video.filename if self.main_video else "None"
        return f"ProcessingJob({self.id[:8]}, {main_name}, {self.status.value}, {self.progress:.1f}%)"
