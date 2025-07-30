"""
Processing Models

Data transfer objects for video processing operations.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

from ...domain.entities.processing_job import ProcessingJob
from ...domain.entities.effect import Effect
from ...domain.value_objects.job_status import JobStatus
from ...domain.value_objects.effect_type import EffectType


@dataclass
class EffectDTO:
    """Data transfer object for Effect entity"""
    type: str
    duration: float
    parameters: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_entity(cls, effect: Effect) -> 'EffectDTO':
        """Create DTO from Effect entity"""
        return cls(
            type=effect.type.value,
            duration=effect.duration,
            parameters=effect.parameters.copy()
        )

    def to_entity(self) -> Effect:
        """Convert DTO to Effect entity"""
        return Effect(
            type=EffectType(self.type),
            duration=self.duration,
            parameters=self.parameters.copy()
        )

    @property
    def display_name(self) -> str:
        """Get user-friendly display name"""
        return self.type.replace('_', ' ').title()


@dataclass
class ProcessingJobDTO:
    """Data transfer object for ProcessingJob entity"""
    id: str
    main_video_path: str
    background_video_path: Optional[str] = None
    output_path: Optional[str] = None
    effects: List[EffectDTO] = field(default_factory=list)
    status: str = "pending"
    progress: float = 0.0
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    estimated_duration: Optional[float] = None
    actual_duration: Optional[float] = None

    @classmethod
    def from_entity(cls, job: ProcessingJob) -> 'ProcessingJobDTO':
        """Create DTO from ProcessingJob entity"""
        return cls(
            id=job.id,
            main_video_path=str(job.main_video.path) if job.main_video else "",
            background_video_path=str(job.background_video.path) if job.background_video else None,
            output_path=str(job.output_path) if job.output_path else None,
            effects=[EffectDTO.from_entity(effect) for effect in job.effects],
            status=job.status.value,
            progress=job.progress,
            created_at=job.created_at.isoformat() if job.created_at else None,
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            error_message=job.error_message,
            estimated_duration=job.get_estimated_duration(),
            actual_duration=job.get_processing_time()
        )

    @property
    def is_terminal(self) -> bool:
        """Check if job is in terminal status"""
        return JobStatus(self.status).is_terminal()

    @property
    def is_active(self) -> bool:
        """Check if job is currently active"""
        return JobStatus(self.status).is_active()

    @property
    def main_video_name(self) -> str:
        """Get main video filename"""
        return Path(self.main_video_path).name if self.main_video_path else ""

    @property
    def background_video_name(self) -> Optional[str]:
        """Get background video filename"""
        return Path(self.background_video_path).name if self.background_video_path else None

    @property
    def output_filename(self) -> Optional[str]:
        """Get output filename"""
        return Path(self.output_path).name if self.output_path else None


@dataclass
class ProcessingRequest:
    """Request for video processing"""
    main_video_path: str
    background_video_path: str
    output_path: str
    effects: List[Dict[str, Any]] = field(default_factory=list)

    def to_paths(self) -> tuple:
        """Convert string paths to Path objects"""
        return (
            Path(self.main_video_path),
            Path(self.background_video_path),
            Path(self.output_path)
        )


@dataclass
class ProcessingResponse:
    """Response from video processing"""
    success: bool
    job_id: Optional[str] = None
    output_path: Optional[str] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    validation_errors: List[str] = field(default_factory=list)

    @property
    def output_filename(self) -> Optional[str]:
        """Get output filename"""
        return Path(self.output_path).name if self.output_path else None


@dataclass
class QueueStatus:
    """Status of processing queue"""
    queue_size: int
    processing_count: int
    completed_count: int
    failed_count: int
    is_processing: bool
    total_jobs: int

    @property
    def pending_count(self) -> int:
        """Get number of pending jobs"""
        return self.total_jobs - self.completed_count - self.failed_count - self.processing_count


@dataclass
class ProcessingStatistics:
    """Processing statistics"""
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    cancelled_jobs: int
    success_rate: float
    average_processing_time: float
    total_processing_time: float
    queue_status: QueueStatus

    @property
    def completion_rate(self) -> float:
        """Get completion rate percentage"""
        if self.total_jobs == 0:
            return 0.0
        return round((self.completed_jobs + self.failed_jobs) / self.total_jobs * 100, 1)


@dataclass
class BatchProcessingRequest:
    """Request for batch video processing"""
    video_pairs: List[tuple]  # List of (main_video, background_video) tuples
    output_directory: str
    effects: List[Dict[str, Any]] = field(default_factory=list)
    use_random_effects: bool = False
    filename_pattern: str = "processed_{index}_{original_name}"

    def get_output_directory(self) -> Path:
        """Get output directory as Path"""
        return Path(self.output_directory)


@dataclass
class BatchProcessingResponse:
    """Response from batch processing"""
    success: bool
    job_ids: List[str] = field(default_factory=list)
    total_jobs: int = 0
    error_message: Optional[str] = None

    @property
    def jobs_submitted(self) -> int:
        """Get number of jobs successfully submitted"""
        return len(self.job_ids)
