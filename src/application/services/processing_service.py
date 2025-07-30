"""
Processing Service

Application service for managing video processing jobs and queue.
"""

import logging
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path
import threading
import queue
import time
from datetime import datetime

from ...domain.entities.processing_job import ProcessingJob
from ...domain.entities.video import Video
from ...domain.value_objects.job_status import JobStatus
from ...domain.services.video_processor_interface import IVideoProcessor
from ...shared.config import AppConfig
from ...shared.utils import get_logger, get_performance_logger
from ...shared.exceptions import ProcessingJobException

logger = get_logger(__name__)
perf_logger = get_performance_logger()


class JobProgressCallback:
    """Callback interface for job progress updates"""

    def __init__(self, on_progress: Optional[Callable[[str, float], None]] = None,
                 on_status_change: Optional[Callable[[str, JobStatus], None]] = None,
                 on_complete: Optional[Callable[[str, bool], None]] = None):
        """
        Initialize callback.

        Args:
            on_progress: Called when job progress updates (job_id, progress)
            on_status_change: Called when job status changes (job_id, status)
            on_complete: Called when job completes (job_id, success)
        """
        self.on_progress = on_progress
        self.on_status_change = on_status_change
        self.on_complete = on_complete


class ProcessingService:
    """Application service for processing job management"""

    def __init__(self, video_processor: IVideoProcessor, config: AppConfig):
        """
        Initialize processing service.

        Args:
            video_processor: Video processor for actual processing
            config: Application configuration
        """
        self.video_processor = video_processor
        self.config = config

        # Job management
        self._jobs: Dict[str, ProcessingJob] = {}
        self._job_queue = queue.Queue()
        self._processing_thread: Optional[threading.Thread] = None
        self._is_processing = False
        self._callbacks: Dict[str, JobProgressCallback] = {}

        # Statistics
        self._stats = {
            'total_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'cancelled_jobs': 0,
            'total_processing_time': 0.0
        }

    def submit_job(self, job: ProcessingJob,
                   callback: Optional[JobProgressCallback] = None) -> str:
        """
        Submit a processing job to the queue.

        Args:
            job: Processing job to submit
            callback: Optional callback for progress updates

        Returns:
            Job ID
        """
        try:
            # Validate job
            validation_errors = job.validate_for_processing()
            if validation_errors:
                raise ProcessingJobException(
                    job.id,
                    f"Job validation failed: {'; '.join(validation_errors)}"
                )

            # Store job and callback
            self._jobs[job.id] = job
            if callback:
                self._callbacks[job.id] = callback

            # Update job status
            job.update_status(JobStatus.QUEUED)
            self._notify_status_change(job.id, JobStatus.QUEUED)

            # Add to queue
            self._job_queue.put(job.id)
            self._stats['total_jobs'] += 1

            # Start processing thread if not running
            self._ensure_processing_thread()

            logger.info(f"Job submitted to queue: {job.id}")
            return job.id

        except Exception as e:
            logger.error(f"Error submitting job {job.id}: {e}")
            raise ProcessingJobException(job.id, str(e))

    def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        """
        Get job by ID.

        Args:
            job_id: Job ID

        Returns:
            Processing job or None if not found
        """
        return self._jobs.get(job_id)

    def get_all_jobs(self) -> List[ProcessingJob]:
        """
        Get all jobs.

        Returns:
            List of all processing jobs
        """
        return list(self._jobs.values())

    def get_jobs_by_status(self, status: JobStatus) -> List[ProcessingJob]:
        """
        Get jobs by status.

        Args:
            status: Job status to filter by

        Returns:
            List of jobs with specified status
        """
        return [job for job in self._jobs.values() if job.status == status]

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if job was cancelled successfully
        """
        try:
            job = self._jobs.get(job_id)
            if not job:
                logger.warning(f"Job not found for cancellation: {job_id}")
                return False

            if job.status.is_terminal():
                logger.warning(f"Cannot cancel job in terminal status: {job_id} ({job.status.value})")
                return False

            # Try to cancel with video processor if processing
            if job.status == JobStatus.PROCESSING:
                self.video_processor.cancel_processing(job_id)

            # Update job status
            job.update_status(JobStatus.CANCELLED)
            self._notify_status_change(job_id, JobStatus.CANCELLED)
            self._notify_complete(job_id, False)

            self._stats['cancelled_jobs'] += 1

            logger.info(f"Job cancelled: {job_id}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return False

    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status.

        Returns:
            Dictionary with queue information
        """
        queued_jobs = self.get_jobs_by_status(JobStatus.QUEUED)
        processing_jobs = self.get_jobs_by_status(JobStatus.PROCESSING)
        completed_jobs = self.get_jobs_by_status(JobStatus.COMPLETED)
        failed_jobs = self.get_jobs_by_status(JobStatus.FAILED)

        return {
            'queue_size': len(queued_jobs),
            'processing_count': len(processing_jobs),
            'completed_count': len(completed_jobs),
            'failed_count': len(failed_jobs),
            'is_processing': self._is_processing,
            'total_jobs': len(self._jobs)
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics.

        Returns:
            Dictionary with processing statistics
        """
        queue_status = self.get_queue_status()

        # Calculate average processing time
        avg_processing_time = 0.0
        if self._stats['completed_jobs'] > 0:
            avg_processing_time = self._stats['total_processing_time'] / self._stats['completed_jobs']

        return {
            **self._stats,
            **queue_status,
            'average_processing_time': round(avg_processing_time, 2),
            'success_rate': self._calculate_success_rate()
        }

    def clear_completed_jobs(self) -> int:
        """
        Clear completed and failed jobs from memory.

        Returns:
            Number of jobs cleared
        """
        try:
            jobs_to_remove = []

            for job_id, job in self._jobs.items():
                if job.status.is_terminal():
                    jobs_to_remove.append(job_id)

            # Remove jobs and callbacks
            for job_id in jobs_to_remove:
                del self._jobs[job_id]
                if job_id in self._callbacks:
                    del self._callbacks[job_id]

            logger.info(f"Cleared {len(jobs_to_remove)} completed jobs")
            return len(jobs_to_remove)

        except Exception as e:
            logger.error(f"Error clearing completed jobs: {e}")
            return 0

    def stop_processing(self) -> None:
        """Stop the processing thread and cancel all pending jobs"""
        try:
            self._is_processing = False

            # Cancel all queued jobs
            queued_jobs = self.get_jobs_by_status(JobStatus.QUEUED)
            for job in queued_jobs:
                self.cancel_job(job.id)

            # Wait for processing thread to finish
            if self._processing_thread and self._processing_thread.is_alive():
                self._processing_thread.join(timeout=5.0)

            logger.info("Processing service stopped")

        except Exception as e:
            logger.error(f"Error stopping processing service: {e}")

    def _ensure_processing_thread(self) -> None:
        """Ensure processing thread is running"""
        if not self._processing_thread or not self._processing_thread.is_alive():
            self._is_processing = True
            self._processing_thread = threading.Thread(
                target=self._process_jobs,
                daemon=True,
                name="ProcessingService"
            )
            self._processing_thread.start()
            logger.debug("Processing thread started")

    def _process_jobs(self) -> None:
        """Main processing loop (runs in separate thread)"""
        logger.info("Processing thread started")

        while self._is_processing:
            try:
                # Get next job from queue (with timeout)
                try:
                    job_id = self._job_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                job = self._jobs.get(job_id)
                if not job:
                    logger.warning(f"Job not found in processing queue: {job_id}")
                    continue

                # Skip if job was cancelled
                if job.status == JobStatus.CANCELLED:
                    continue

                # Process the job
                self._process_single_job(job)

            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                time.sleep(1.0)  # Brief pause before continuing

        logger.info("Processing thread stopped")

    def _process_single_job(self, job: ProcessingJob) -> None:
        """Process a single job"""
        start_time = time.time()

        try:
            logger.info(f"Starting job processing: {job.id}")

            # Update job status
            job.update_status(JobStatus.PROCESSING)
            self._notify_status_change(job.id, JobStatus.PROCESSING)

            # Process video with timeout
            try:
                result = self.video_processor.process_video(job)
            except Exception as e:
                logger.error(f"Video processing failed for job {job.id}: {e}")
                job.update_status(JobStatus.FAILED, str(e))
                self._stats['failed_jobs'] += 1
                self._notify_status_change(job.id, JobStatus.FAILED)
                self._notify_complete(job.id, False)
                return

            processing_time = time.time() - start_time

            if result.is_success():
                # Job completed successfully
                job.update_status(JobStatus.COMPLETED)
                job.update_progress(100.0)

                self._stats['completed_jobs'] += 1
                self._stats['total_processing_time'] += processing_time

                # Log performance
                perf_logger.log_processing_time(
                    "job_processing",
                    processing_time,
                    str(job.main_video.path) if job.main_video else None,
                    job_id=job.id,
                    effects_count=len(job.effects)
                )

                logger.info(f"Job completed successfully: {job.id} ({processing_time:.1f}s)")

                self._notify_status_change(job.id, JobStatus.COMPLETED)
                self._notify_complete(job.id, True)

            else:
                # Job failed
                job.update_status(JobStatus.FAILED, result.get_error())
                self._stats['failed_jobs'] += 1

                logger.error(f"Job failed: {job.id} - {result.get_error()}")

                self._notify_status_change(job.id, JobStatus.FAILED)
                self._notify_complete(job.id, False)

        except Exception as e:
            # Unexpected error during processing
            processing_time = time.time() - start_time

            job.update_status(JobStatus.FAILED, str(e))
            self._stats['failed_jobs'] += 1

            logger.error(f"Unexpected error processing job {job.id}: {e}")

            self._notify_status_change(job.id, JobStatus.FAILED)
            self._notify_complete(job.id, False)

    def _notify_progress(self, job_id: str, progress: float) -> None:
        """Notify progress callback"""
        callback = self._callbacks.get(job_id)
        if callback and callback.on_progress:
            try:
                callback.on_progress(job_id, progress)
            except Exception as e:
                logger.warning(f"Error in progress callback for job {job_id}: {e}")

    def _notify_status_change(self, job_id: str, status: JobStatus) -> None:
        """Notify status change callback"""
        callback = self._callbacks.get(job_id)
        if callback and callback.on_status_change:
            try:
                callback.on_status_change(job_id, status)
            except Exception as e:
                logger.warning(f"Error in status change callback for job {job_id}: {e}")

    def _notify_complete(self, job_id: str, success: bool) -> None:
        """Notify completion callback"""
        callback = self._callbacks.get(job_id)
        if callback and callback.on_complete:
            try:
                callback.on_complete(job_id, success)
            except Exception as e:
                logger.warning(f"Error in completion callback for job {job_id}: {e}")

    def _calculate_success_rate(self) -> float:
        """Calculate success rate percentage"""
        total_finished = self._stats['completed_jobs'] + self._stats['failed_jobs']
        if total_finished == 0:
            return 0.0
        return round((self._stats['completed_jobs'] / total_finished) * 100, 1)
