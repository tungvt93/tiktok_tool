"""
Job Status Value Object

Defines the possible states of a video processing job.
"""

from enum import Enum


class JobStatus(Enum):
    """Status of a video processing job"""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    def is_terminal(self) -> bool:
        """Check if this is a terminal status (job is finished)"""
        return self in [self.COMPLETED, self.FAILED, self.CANCELLED]

    def is_active(self) -> bool:
        """Check if the job is currently active"""
        return self in [self.QUEUED, self.PROCESSING]

    def can_transition_to(self, new_status: 'JobStatus') -> bool:
        """Check if transition to new status is valid"""
        valid_transitions = {
            self.PENDING: [self.QUEUED, self.CANCELLED],
            self.QUEUED: [self.PROCESSING, self.CANCELLED],
            self.PROCESSING: [self.COMPLETED, self.FAILED, self.CANCELLED],
            self.COMPLETED: [],  # Terminal state
            self.FAILED: [self.QUEUED],  # Can retry
            self.CANCELLED: [self.QUEUED]  # Can restart
        }
        return new_status in valid_transitions.get(self, [])
