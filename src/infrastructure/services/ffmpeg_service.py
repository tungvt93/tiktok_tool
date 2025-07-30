"""
FFmpeg Service Implementation

Concrete implementation of video processing using FFmpeg.
"""

import subprocess
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from functools import lru_cache

from ...domain.entities.video import Video
from ...domain.entities.processing_job import ProcessingJob
from ...domain.value_objects.dimensions import Dimensions
from ...domain.services.video_processor_interface import IVideoProcessor, ProcessingResult, VideoInfo
from ...shared.config import FFmpegConfig, VideoProcessingConfig
from ...shared.exceptions import FFmpegException, VideoNotFoundException, VideoCorruptedException
from ...shared.utils import get_performance_logger

logger = logging.getLogger(__name__)
perf_logger = get_performance_logger()


class FFmpegService(IVideoProcessor):
    """FFmpeg-based video processor implementation"""

    def __init__(self, video_config: VideoProcessingConfig, ffmpeg_config: FFmpegConfig):
        """
        Initialize FFmpeg service.

        Args:
            video_config: Video processing configuration
            ffmpeg_config: FFmpeg-specific configuration
        """
        self.video_config = video_config
        self.ffmpeg_config = ffmpeg_config
        self._active_processes: Dict[str, subprocess.Popen] = {}

    def process_video(self, job: ProcessingJob) -> ProcessingResult:
        """
        Process a video according to the job specification.

        Args:
            job: The processing job containing all configuration

        Returns:
            ProcessingResult with success status and output information
        """
        import time
        start_time = time.time()

        try:
            # Validate job
            validation_errors = job.validate_for_processing()
            if validation_errors:
                error_msg = f"Job validation failed: {'; '.join(validation_errors)}"
                return ProcessingResult(False, error_message=error_msg)

            # Create output directory
            job.output_path.parent.mkdir(parents=True, exist_ok=True)

            # Build FFmpeg command
            cmd = self._build_processing_command(job)

            # Execute command
            success = self._run_ffmpeg_command(cmd, job.id)

            if success:
                # Verify output file was created
                if job.output_path.exists() and job.output_path.stat().st_size > 0:
                    processing_time = time.time() - start_time
                    perf_logger.log_processing_time(
                        "video_processing",
                        processing_time,
                        str(job.main_video.path),
                        job_id=job.id,
                        effects_count=len(job.effects)
                    )

                    return ProcessingResult(
                        True,
                        output_path=job.output_path,
                        metadata={
                            'processing_time': processing_time,
                            'effects_applied': len(job.effects),
                            'output_size': job.output_path.stat().st_size
                        }
                    )
                else:
                    return ProcessingResult(False, error_message="Output file was not created or is empty")
            else:
                return ProcessingResult(False, error_message="FFmpeg processing failed")

        except Exception as e:
            logger.error(f"Error processing video job {job.id}: {e}")
            return ProcessingResult(False, error_message=str(e))

    def get_video_info(self, video_path: Path) -> Optional[VideoInfo]:
        """
        Extract video information from file.

        Args:
            video_path: Path to the video file

        Returns:
            VideoInfo object or None if extraction fails
        """
        try:
            if not video_path.exists():
                raise VideoNotFoundException(video_path)

            # Get duration
            duration = self._get_video_duration(video_path)
            if duration is None:
                return None

            # Get dimensions
            dimensions_tuple = self._get_video_dimensions(video_path)
            if dimensions_tuple is None:
                return None

            dimensions = Dimensions(dimensions_tuple[0], dimensions_tuple[1])

            # Get codec and bitrate info
            codec_info = self._get_video_codec_info(video_path)

            return VideoInfo(
                duration=duration,
                dimensions=dimensions,
                codec=codec_info.get('codec', 'unknown'),
                bitrate=codec_info.get('bitrate', 0),
                metadata=codec_info
            )

        except Exception as e:
            logger.error(f"Error getting video info for {video_path}: {e}")
            return None

    def validate_video_file(self, video_path: Path) -> bool:
        """
        Validate that a file is a valid video.

        Args:
            video_path: Path to the video file

        Returns:
            True if file is a valid video, False otherwise
        """
        try:
            if not video_path.exists():
                return False

            # Try to get basic video info
            cmd = [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                str(video_path)
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )

            return result.returncode == 0 and "video" in result.stdout

        except Exception as e:
            logger.warning(f"Error validating video file {video_path}: {e}")
            return False

    def estimate_processing_time(self, job: ProcessingJob) -> float:
        """
        Estimate processing time for a job in seconds.

        Args:
            job: The processing job to estimate

        Returns:
            Estimated processing time in seconds
        """
        if not job.main_video:
            return 0.0

        base_duration = job.main_video.duration

        # Base processing time (encoding overhead)
        base_time = base_duration * 0.3  # 30% of video duration

        # Add effect processing time
        effect_time = sum(
            effect.get_estimated_processing_time(base_duration)
            for effect in job.effects
        )

        # Add complexity factors
        complexity_factor = 1.0

        # Higher resolution increases processing time
        total_pixels = job.main_video.dimensions.total_pixels
        if total_pixels > 1920 * 1080:  # 4K+
            complexity_factor *= 2.0
        elif total_pixels > 1280 * 720:  # 1080p
            complexity_factor *= 1.5

        # Multiple effects increase complexity
        if len(job.effects) > 1:
            complexity_factor *= 1.2

        return (base_time + effect_time) * complexity_factor

    def cancel_processing(self, job_id: str) -> bool:
        """
        Cancel an ongoing processing job.

        Args:
            job_id: ID of the job to cancel

        Returns:
            True if cancellation was successful, False otherwise
        """
        try:
            if job_id in self._active_processes:
                process = self._active_processes[job_id]
                process.terminate()

                # Wait a bit for graceful termination
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    process.kill()
                    process.wait()

                del self._active_processes[job_id]
                logger.info(f"Cancelled processing job: {job_id}")
                return True
            else:
                logger.warning(f"No active process found for job: {job_id}")
                return False

        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return False

    def _build_processing_command(self, job: ProcessingJob) -> List[str]:
        """Build FFmpeg command for processing job"""
        cmd = ["ffmpeg", "-y"]  # -y to overwrite output files

        # Input files
        cmd.extend(["-i", str(job.main_video.path)])
        if job.background_video:
            cmd.extend(["-i", str(job.background_video.path)])

        # Build filter complex for video processing
        filter_parts = []

        # Scale main video to half width
        filter_parts.append(f"[0:v]scale={self.video_config.half_width}:{self.video_config.output_height}[main]")

        if job.background_video:
            # Scale background video to half width
            filter_parts.append(f"[1:v]scale={self.video_config.half_width}:{self.video_config.output_height}[bg]")
            # Horizontal stack
            filter_parts.append("[main][bg]hstack=inputs=2[video]")
            video_label = "[video]"
        else:
            video_label = "[main]"

        # Apply effects if any
        if job.effects:
            for i, effect in enumerate(job.effects):
                effect_filter = self._build_effect_filter(effect, video_label, f"[effect{i}]")
                if effect_filter:
                    filter_parts.append(effect_filter)
                    video_label = f"[effect{i}]"

        # Combine all filters
        if filter_parts:
            cmd.extend(["-filter_complex", ";".join(filter_parts)])
            cmd.extend(["-map", video_label.strip("[]")])

        # Audio mapping (from main video)
        cmd.extend(["-map", "0:a"])

        # Encoding settings
        cmd.extend([
            "-c:v", self.ffmpeg_config.codec_video,
            "-preset", self.ffmpeg_config.preset,
            "-crf", str(self.video_config.crf_value),
            "-c:a", self.ffmpeg_config.codec_audio,
            "-threads", self.ffmpeg_config.threads
        ])

        # Output file
        cmd.append(str(job.output_path))

        return cmd

    def _build_effect_filter(self, effect, input_label: str, output_label: str) -> Optional[str]:
        """Build FFmpeg filter for a specific effect"""
        from ...domain.value_objects.effect_type import EffectType

        if effect.type == EffectType.FADE_IN:
            return f"{input_label}fade=t=in:st=0:d={effect.duration}{output_label}"
        elif effect.type == EffectType.SLIDE_RIGHT_TO_LEFT:
            return f"{input_label}slide=direction=right:duration={effect.duration}{output_label}"
        # Add more effect filters as needed

        return None

    def _run_ffmpeg_command(self, cmd: List[str], job_id: str) -> bool:
        """Execute FFmpeg command with error handling"""
        try:
            logger.info(f"Running FFmpeg command for job {job_id}: {' '.join(cmd[:5])}...")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Store process for potential cancellation
            self._active_processes[job_id] = process

            # Wait for completion
            stdout, stderr = process.communicate()

            # Remove from active processes
            if job_id in self._active_processes:
                del self._active_processes[job_id]

            if process.returncode == 0:
                logger.info(f"FFmpeg command completed successfully for job {job_id}")
                return True
            else:
                logger.error(f"FFmpeg command failed for job {job_id}: {stderr}")
                raise FFmpegException(' '.join(cmd), stderr, process.returncode)

        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg command timed out for job {job_id}")
            return False
        except Exception as e:
            logger.error(f"Error running FFmpeg command for job {job_id}: {e}")
            return False

    @lru_cache(maxsize=128)
    def _get_video_duration(self, video_path: Path) -> Optional[float]:
        """Get video duration using FFprobe"""
        try:
            cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=10
            )

            return float(result.stdout.strip())

        except Exception as e:
            logger.error(f"Failed to get duration for {video_path}: {e}")
            return None

    @lru_cache(maxsize=128)
    def _get_video_dimensions(self, video_path: Path) -> Optional[tuple]:
        """Get video dimensions using FFprobe"""
        try:
            cmd = [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height", "-of", "csv=p=0",
                str(video_path)
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=10
            )

            width, height = map(int, result.stdout.strip().split(','))
            return (width, height)

        except Exception as e:
            logger.error(f"Failed to get dimensions for {video_path}: {e}")
            return None

    def _get_video_codec_info(self, video_path: Path) -> Dict[str, Any]:
        """Get video codec and bitrate information"""
        try:
            cmd = [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=codec_name,bit_rate,r_frame_rate",
                "-of", "json", str(video_path)
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=10
            )

            import json
            data = json.loads(result.stdout)

            if data.get('streams'):
                stream = data['streams'][0]
                return {
                    'codec': stream.get('codec_name', 'unknown'),
                    'bitrate': int(stream.get('bit_rate', 0)),
                    'frame_rate': stream.get('r_frame_rate', '0/1')
                }

            return {}

        except Exception as e:
            logger.warning(f"Failed to get codec info for {video_path}: {e}")
            return {}
