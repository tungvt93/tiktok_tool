"""
FFmpeg Service Implementation

Concrete implementation of video processing using FFmpeg with GPU acceleration.
"""

import subprocess
import logging
import threading
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Callable
from functools import lru_cache
import tempfile
import shutil

from ...domain.entities.video import Video
from ...domain.entities.processing_job import ProcessingJob
from ...domain.value_objects.dimensions import Dimensions
from ...domain.value_objects.effect_type import EffectType
from ...domain.services.video_processor_interface import IVideoProcessor, ProcessingResult, VideoInfo
from ...shared.config import FFmpegConfig, VideoProcessingConfig
from ...shared.exceptions import FFmpegException, VideoNotFoundException, VideoCorruptedException
from ...shared.utils import get_performance_logger

logger = logging.getLogger(__name__)
perf_logger = get_performance_logger()


class FFmpegService(IVideoProcessor):
    """FFmpeg-based video processor implementation with GPU acceleration"""

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
        self._progress_callback: Optional[Callable[[str, float], None]] = None
        
        # Optimized concurrency - allow more concurrent processes based on CPU cores
        import multiprocessing
        max_concurrent = min(multiprocessing.cpu_count(), 4)  # Max 4 concurrent processes
        self._ffmpeg_semaphore = threading.Semaphore(max_concurrent)
        
        # Initialize GPU detection
        self._gpu_encoder = self._detect_gpu_encoder()
        self._duration_cache_file = Path("temp/duration_cache.json")
        self._duration_cache = self._load_duration_cache()
        
        # Create temp directory
        self._temp_dir = Path("temp/ffmpeg_processing")
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"FFmpegService initialized with GPU encoder: {self._gpu_encoder}")
        logger.info(f"Max concurrent processes: {max_concurrent}")

    def set_progress_callback(self, callback: Optional[Callable[[str, float], None]]) -> None:
        """Set progress callback for reporting job progress"""
        self._progress_callback = callback

    def _detect_gpu_encoder(self) -> Optional[str]:
        """Detect available GPU encoder"""
        try:
            # Test NVIDIA NVENC
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1", 
                 "-c:v", "h264_nvenc", "-f", "null", "-"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
            )
            if result.returncode == 0:
                return "h264_nvenc"
        except:
            pass

        try:
            # Test Intel QSV
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1", 
                 "-c:v", "h264_qsv", "-f", "null", "-"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
            )
            if result.returncode == 0:
                return "h264_qsv"
        except:
            pass

        try:
            # Test Apple VideoToolbox
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=1", 
                 "-c:v", "h264_videotoolbox", "-f", "null", "-"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
            )
            if result.returncode == 0:
                return "h264_videotoolbox"
        except:
            pass

        return None

    def _load_duration_cache(self) -> Dict[str, float]:
        """Load video duration cache from file"""
        try:
            if self._duration_cache_file.exists():
                with open(self._duration_cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load duration cache: {e}")
        return {}

    def _save_duration_cache(self) -> None:
        """Save video duration cache to file"""
        try:
            self._duration_cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._duration_cache_file, 'w') as f:
                json.dump(self._duration_cache, f)
        except Exception as e:
            logger.warning(f"Failed to save duration cache: {e}")

    def process_video(self, job: ProcessingJob) -> ProcessingResult:
        """Process a video with effects using optimized single-step processing"""
        try:
            logger.info(f"Processing video: {job.main_video.path}")
            
            # Create temporary directory for this job
            with tempfile.TemporaryDirectory(dir=self._temp_dir) as temp_dir:
                temp_path = Path(temp_dir)
                
                # Check if we have complex effects that require dedicated processor
                has_complex_effects = any(
                    effect.type in [EffectType.CIRCLE_EXPAND, EffectType.CIRCLE_CONTRACT, 
                                  EffectType.CIRCLE_ROTATE_CW, EffectType.CIRCLE_ROTATE_CCW,
                                  EffectType.SLIDE_RIGHT_TO_LEFT, EffectType.SLIDE_LEFT_TO_RIGHT,
                                  EffectType.SLIDE_TOP_TO_BOTTOM, EffectType.SLIDE_BOTTOM_TO_TOP]
                    for effect in job.effects
                )
                
                if has_complex_effects:
                    # Use two-step processing for complex effects
                    logger.info("Complex effects detected - using two-step processing")
                    temp_output = temp_path / "temp_output.mp4"
                    cmd = self._build_optimized_processing_command(job, temp_output)
                    
                    # Create progress callback
                    def progress_callback(progress: float):
                        job.update_progress(progress)
                        # Notify processing service if available
                        if hasattr(self, '_progress_callback') and self._progress_callback:
                            self._progress_callback(job.id, progress)
                    
                    if not self._run_ffmpeg_command(cmd, job.id, progress_callback):
                        return ProcessingResult(False, error_message="FFmpeg processing failed")
                    
                    if self._has_opening_effects(job):
                        success = self._apply_opening_effects(temp_output, job.output_path, job)
                        if not success:
                            return ProcessingResult(False, error_message="Opening effects processing failed")
                    else:
                        shutil.move(str(temp_output), str(job.output_path))
                else:
                    # Use optimized single-step processing for better performance
                    cmd = self._build_optimized_single_step_command(job, job.output_path)
                    
                    # Create progress callback
                    def progress_callback(progress: float):
                        job.update_progress(progress)
                        # Notify processing service if available
                        if hasattr(self, '_progress_callback') and self._progress_callback:
                            self._progress_callback(job.id, progress)
                    
                    if not self._run_ffmpeg_command(cmd, job.id, progress_callback):
                        return ProcessingResult(False, error_message="FFmpeg processing failed")
                
            logger.info(f"Video processing completed: {job.output_path}")
            return ProcessingResult(True, output_path=job.output_path)
            
        except Exception as e:
            logger.error(f"Error processing video {job.main_video.path}: {e}")
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

    def _build_optimized_single_step_command(self, job: ProcessingJob, output_path: Path) -> List[str]:
        """Build optimized single-step FFmpeg command with GPU acceleration"""
        from ...domain.value_objects.effect_type import EffectType
        
        cmd = ["ffmpeg", "-y"]
        
        # Add input files
        cmd.extend(["-i", str(job.main_video.path)])
        
        if job.background_video:
            cmd.extend(["-i", str(job.background_video.path)])
        

        
        # Build optimized filter complex
        filter_parts = []
        input_index = 0
        
        # Scale main video to half width with optimized scaling
        filter_parts.append(f"[{input_index}:v]scale={self.video_config.half_width}:{self.video_config.output_height}:flags=lanczos[left]")
        input_index += 1
        
        # Scale background video to half width with optimized scaling
        if job.background_video:
            filter_parts.append(f"[{input_index}:v]scale={self.video_config.half_width}:{self.video_config.output_height}:flags=lanczos[right]")
            input_index += 1
            # Horizontal stack like old logic
            filter_parts.append("[left][right]hstack=inputs=2[stacked]")
            video_label = "[stacked]"
        else:
            video_label = "[left]"
        

        
        # Apply opening effects (fade, slide, circle)
        for effect in job.effects:
            effect_filter = self._build_opening_effect_filter_single_step(effect, video_label, "[final]")
            if effect_filter:
                filter_parts.append(effect_filter)
                video_label = "[final]"
                break  # Only apply first opening effect like old logic
        
        # If no opening effects, just copy the video
        if video_label != "[final]":
            filter_parts.append(f"{video_label}copy[final]")
        
        # Build final command with GPU acceleration
        cmd.extend([
            "-filter_complex", ";".join(filter_parts),
            "-map", "[final]",
            "-map", "0:a",  # Include audio from first input
            "-c:v", self._gpu_encoder or self.ffmpeg_config.codec_video,
            "-c:a", "copy",  # Copy audio without re-encoding
            "-preset", "fast" if self._gpu_encoder else self.ffmpeg_config.preset,
            "-crf", str(self.video_config.crf_value),
            "-threads", "0",  # Use all available threads
            "-movflags", "+faststart+write_colr",
            "-shortest",
            str(output_path)
        ])
        
        # Add GPU-specific options
        if self._gpu_encoder == "h264_nvenc":
            cmd.extend(["-rc", "vbr", "-cq", "23", "-b:v", "5M", "-maxrate", "10M"])
        elif self._gpu_encoder == "h264_qsv":
            cmd.extend(["-global_quality", "23", "-look_ahead", "1"])
        elif self._gpu_encoder == "h264_videotoolbox":
            cmd.extend(["-allow_sw", "1", "-tag:v", "avc1"])
        
        return cmd



    def _build_opening_effect_filter_single_step(self, effect, input_label: str, output_label: str) -> Optional[str]:
        """Build opening effect filter for single-step processing"""
        from ...domain.value_objects.effect_type import EffectType

        if effect.type == EffectType.FADE_IN:
            return f"{input_label}fade=t=in:st=0:d={effect.duration}{output_label}"
        
        elif effect.type in [EffectType.SLIDE_RIGHT_TO_LEFT, EffectType.SLIDE_LEFT_TO_RIGHT, 
                           EffectType.SLIDE_TOP_TO_BOTTOM, EffectType.SLIDE_BOTTOM_TO_TOP]:
            # For slide effects in single-step, we need to use the dedicated SlideEffectProcessor
            # because they require complex pad/crop logic that can't be done with simple crop filters
            logger.warning(f"Slide effect {effect.type} requires dedicated processor - switching to two-step processing")
            return None  # Return None to trigger two-step processing
        
        elif effect.type in [EffectType.CIRCLE_EXPAND, EffectType.CIRCLE_CONTRACT, 
                           EffectType.CIRCLE_ROTATE_CW, EffectType.CIRCLE_ROTATE_CCW]:
            # For circle effects in single-step, we need to use the dedicated CircleEffectProcessor
            # because they require complex mask generation that can't be done with simple FFmpeg filters
            logger.warning(f"Circle effect {effect.type} requires dedicated processor - switching to two-step processing")
            return None  # Return None to trigger two-step processing
        
        return None

    def _build_optimized_processing_command(self, job: ProcessingJob, temp_output: Path) -> List[str]:
        """Build optimized FFmpeg command for processing job with GPU acceleration"""
        cmd = ["ffmpeg", "-y"]  # -y to overwrite output files

        # Input files
        cmd.extend(["-i", str(job.main_video.path)])
        if job.background_video:
            cmd.extend(["-i", str(job.background_video.path)])



        # Build filter complex for video processing
        filter_parts = []

        # Scale main video to half width with optimized scaling
        filter_parts.append(f"[0:v]scale={self.video_config.half_width}:{self.video_config.output_height}:flags=lanczos[left]")

        # Scale background video to half width with optimized scaling
        if job.background_video:
            filter_parts.append(f"[1:v]scale={self.video_config.half_width}:{self.video_config.output_height}:flags=lanczos[right]")
            # Horizontal stack like old logic
            filter_parts.append("[left][right]hstack=inputs=2[stacked]")
            video_label = "[stacked]"
        else:
            video_label = "[left]"

        # Apply effects if any
        if job.effects:
            for i, effect in enumerate(job.effects):
                # Handle effects
                effect_filter = self._build_effect_filter(effect, video_label, f"[effect{i}]")
                if effect_filter:
                    # Skip circle effects for now to avoid syntax errors
                    if effect.type not in [EffectType.CIRCLE_EXPAND, EffectType.CIRCLE_CONTRACT, 
                                         EffectType.CIRCLE_ROTATE_CW, EffectType.CIRCLE_ROTATE_CCW]:
                        filter_parts.append(effect_filter)
                        video_label = f"[effect{i}]"
                    else:
                        logger.warning(f"Skipping circle effect {effect.type} to avoid syntax errors")

        # Combine all filters
        if filter_parts:
            cmd.extend(["-filter_complex", ";".join(filter_parts)])
            # Map the final output
            cmd.extend(["-map", video_label if 'video_label' in locals() else "[left]"])
        else:
            # No effects, just map the main video
            cmd.extend(["-map", "0:v"])

        # Audio mapping (from main video)
        cmd.extend(["-map", "0:a"])

        # Optimized encoding settings with GPU acceleration
        cmd.extend([
            "-c:v", self._gpu_encoder or self.ffmpeg_config.codec_video,
            "-preset", "fast" if self._gpu_encoder else "ultrafast",  # Use fast for GPU, ultrafast for CPU
            "-crf", "28" if self._gpu_encoder else "28",  # Slightly higher CRF for faster encoding
            "-c:a", self.ffmpeg_config.codec_audio,
            "-threads", "0",  # Use all available threads
            "-shortest",  # Stop when shortest input ends (like old logic)
            "-movflags", "+faststart+write_colr"  # Optimize for streaming and add color info
        ])

        # Add GPU-specific options
        if self._gpu_encoder == "h264_nvenc":
            cmd.extend(["-rc", "vbr", "-cq", "23", "-b:v", "5M", "-maxrate", "10M"])
        elif self._gpu_encoder == "h264_qsv":
            cmd.extend(["-global_quality", "23", "-look_ahead", "1"])
        elif self._gpu_encoder == "h264_videotoolbox":
            cmd.extend(["-allow_sw", "1", "-tag:v", "avc1"])

        # Output file
        cmd.append(str(temp_output))

        return cmd

    def _has_opening_effects(self, job: ProcessingJob) -> bool:
        """Check if job has opening effects"""
        return len(job.effects) > 0

    def _apply_opening_effects(self, input_video: Path, output_video: Path, job: ProcessingJob) -> bool:
        """Apply opening effects to video (like old logic)"""
        try:
            from ...domain.value_objects.effect_type import EffectType
            
            # Find opening effects
            opening_effects = job.effects
            
            if not opening_effects:
                # No opening effects, just copy
                return self._copy_video(input_video, output_video)
            
            # Apply first opening effect (like old logic)
            effect = opening_effects[0]
            
            if effect.type == EffectType.FADE_IN:
                return self._apply_fade_effect(input_video, output_video, effect.duration)
            elif effect.type in [EffectType.SLIDE_RIGHT_TO_LEFT, EffectType.SLIDE_LEFT_TO_RIGHT, 
                               EffectType.SLIDE_TOP_TO_BOTTOM, EffectType.SLIDE_BOTTOM_TO_TOP]:
                return self._apply_slide_effect(input_video, output_video, effect.type, effect.duration)
            elif effect.type in [EffectType.CIRCLE_EXPAND, EffectType.CIRCLE_CONTRACT]:
                return self._apply_circle_effect(input_video, output_video, effect.type, effect.duration)
            elif effect.type in [EffectType.CIRCLE_ROTATE_CW, EffectType.CIRCLE_ROTATE_CCW]:
                return self._apply_circle_rotate_effect(input_video, output_video, effect.type, effect.duration)
            else:
                logger.warning(f"Unsupported opening effect: {effect.type}")
                return self._copy_video(input_video, output_video)
                
        except Exception as e:
            logger.error(f"Error applying opening effects: {e}")
            return False

    def _copy_video(self, input_video: Path, output_video: Path) -> bool:
        """Copy video without re-encoding"""
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", str(input_video),
                "-c", "copy",
                str(output_video)
            ]
            return self._run_ffmpeg_command(cmd, "copy_video", None)
        except Exception as e:
            logger.error(f"Error copying video: {e}")
            return False

    def _apply_fade_effect(self, input_video: Path, output_video: Path, duration: float) -> bool:
        """Apply fade in effect"""
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", str(input_video),
                "-vf", f"fade=t=in:st=0:d={duration}",
                "-c:a", "copy",
                str(output_video)
            ]
            return self._run_ffmpeg_command(cmd, "fade_effect", None)
        except Exception as e:
            logger.error(f"Error applying fade effect: {e}")
            return False

    def _apply_slide_effect(self, input_video: Path, output_video: Path, effect_type, duration: float) -> bool:
        """Apply slide effect using dedicated processor"""
        try:
            from ...domain.value_objects.effect_type import EffectType
            from ...domain.entities.video import Video
            from ...domain.entities.effect import Effect
            from ...infrastructure.processors.slide_effect_processor import SlideEffectProcessor
            
            # Get video duration and dimensions
            video_duration = self._get_video_duration(input_video) or 10.0
            dims = self._get_video_dimensions(input_video) or (1920, 1080)
            
            # Convert tuple to Dimensions object if needed
            from ...domain.value_objects.dimensions import Dimensions
            if isinstance(dims, tuple):
                video_dimensions = Dimensions(*dims)
            else:
                video_dimensions = dims
            
            # Create Video and Effect entities
            video = Video(path=input_video, duration=video_duration, dimensions=video_dimensions)
            effect = Effect(type=effect_type, duration=duration)
            
            # Use SlideEffectProcessor
            processor = SlideEffectProcessor(self.ffmpeg_config)
            result = processor.apply_effect(video, effect, output_video)
            
            return result.success
        except Exception as e:
            logger.error(f"Error applying slide effect: {e}")
            return False

    def _apply_circle_effect(self, input_video: Path, output_video: Path, effect_type, duration: float) -> bool:
        """Apply circle effect using dedicated processor"""
        try:
            from ...domain.value_objects.effect_type import EffectType
            from ...domain.entities.video import Video
            from ...domain.entities.effect import Effect
            from ...infrastructure.processors.circle_effect_processor import CircleEffectProcessor
            
            # Get video duration and dimensions
            video_duration = self._get_video_duration(input_video) or 10.0
            dims = self._get_video_dimensions(input_video) or (1920, 1080)
            
            # Convert tuple to Dimensions object if needed
            from ...domain.value_objects.dimensions import Dimensions
            if isinstance(dims, tuple):
                video_dimensions = Dimensions(*dims)
            else:
                video_dimensions = dims
            
            # Create video entity
            video = Video(
                path=input_video,
                duration=video_duration,
                dimensions=video_dimensions
            )
            
            # Create effect entity
            effect = Effect(
                type=effect_type,
                duration=duration
            )
            
            # Use dedicated circle effect processor
            processor = CircleEffectProcessor(self.ffmpeg_config)
            result = processor.apply_effect(video, effect, output_video)
            
            return result.success
        except Exception as e:
            logger.error(f"Error applying circle effect: {e}")
            return False

    def _apply_circle_rotate_effect(self, input_video: Path, output_video: Path, effect_type, duration: float) -> bool:
        """Apply circle rotate effect using dedicated processor"""
        try:
            from ...domain.value_objects.effect_type import EffectType
            from ...domain.entities.video import Video
            from ...domain.entities.effect import Effect
            from ...infrastructure.processors.circle_effect_processor import CircleEffectProcessor
            
            # Get video duration and dimensions
            video_duration = self._get_video_duration(input_video) or 10.0
            dims = self._get_video_dimensions(input_video) or (1920, 1080)
            
            # Convert tuple to Dimensions object if needed
            from ...domain.value_objects.dimensions import Dimensions
            if isinstance(dims, tuple):
                video_dimensions = Dimensions(*dims)
            else:
                video_dimensions = dims
            
            # Create video entity
            video = Video(
                path=input_video,
                duration=video_duration,
                dimensions=video_dimensions
            )
            
            # Create effect entity
            effect = Effect(
                type=effect_type,
                duration=duration
            )
            
            # Use dedicated circle effect processor
            processor = CircleEffectProcessor(self.ffmpeg_config)
            result = processor.apply_effect(video, effect, output_video)
            
            return result.success
        except Exception as e:
            logger.error(f"Error applying circle rotate effect: {e}")
            return False

    def _build_effect_filter(self, effect, input_label: str, output_label: str) -> Optional[str]:
        """Build FFmpeg filter for a specific effect"""
        from ...domain.value_objects.effect_type import EffectType

        if effect.type == EffectType.FADE_IN:
            return f"{input_label}fade=t=in:st=0:d={effect.duration}{output_label}"
        elif effect.type == EffectType.SLIDE_RIGHT_TO_LEFT:
            # Implement slide effect using crop and overlay
            width = self.video_config.output_width
            height = self.video_config.output_height
            # Create a sliding effect by cropping and moving the video
            return f"{input_label}crop=w={width}:h={height}:x='if(lt(t,{effect.duration}),{width}*(1-t/{effect.duration}),0)':y=0{output_label}"
        elif effect.type == EffectType.SLIDE_LEFT_TO_RIGHT:
            width = self.video_config.output_width
            height = self.video_config.output_height
            return f"{input_label}crop=w={width}:h={height}:x='if(lt(t,{effect.duration}),{width}*(t/{effect.duration}-1),0)':y=0{output_label}"
        elif effect.type == EffectType.SLIDE_TOP_TO_BOTTOM:
            width = self.video_config.output_width
            height = self.video_config.output_height
            return f"{input_label}crop=w={width}:h={height}:x=0:y='if(lt(t,{effect.duration}),{height}*(t/{effect.duration}-1),0)'{output_label}"
        elif effect.type == EffectType.SLIDE_BOTTOM_TO_TOP:
            width = self.video_config.output_width
            height = self.video_config.output_height
            return f"{input_label}crop=w={width}:h={height}:x=0:y='if(lt(t,{effect.duration}),{height}*(1-t/{effect.duration}),0)'{output_label}"
        elif effect.type in [EffectType.CIRCLE_EXPAND, EffectType.CIRCLE_CONTRACT, 
                           EffectType.CIRCLE_ROTATE_CW, EffectType.CIRCLE_ROTATE_CCW]:
            # Circle effects are now handled by dedicated processor in _apply_opening_effects
            # Return None to skip in first pass
            return None

        # Add more effect filters as needed

        return None



    def _validate_output_file(self, output_path: Path) -> bool:
        """Validate that output file is complete and playable"""
        try:
            if not output_path.exists():
                logger.error(f"Output file does not exist: {output_path}")
                return False

            # Check file size (should be > 1MB for a valid video)
            if output_path.stat().st_size < 1024 * 1024:
                logger.error(f"Output file too small: {output_path.stat().st_size} bytes")
                return False

            # Validate with ffprobe
            cmd = [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                str(output_path)
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and "video" in result.stdout:
                logger.info(f"Output file validation passed: {output_path}")
                return True
            else:
                logger.error(f"Output file validation failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error validating output file {output_path}: {e}")
            return False

    def _run_ffmpeg_command(self, cmd: List[str], job_id: str, progress_callback: Optional[Callable[[float], None]] = None) -> bool:
        """Execute FFmpeg command with progress tracking and error handling"""
        # Acquire semaphore to limit concurrent processes
        with self._ffmpeg_semaphore:
            try:
                logger.info(f"Running FFmpeg command for job {job_id}: {' '.join(cmd[:5])}...")
                logger.debug(f"Full FFmpeg command: {' '.join(cmd)}")

                # Add progress reporting to FFmpeg command
                cmd_with_progress = cmd.copy()
                if "-progress" not in cmd_with_progress:
                    # Insert progress reporting before output file
                    cmd_with_progress.insert(-1, "-progress")
                    cmd_with_progress.insert(-1, "pipe:1")

                process = subprocess.Popen(
                    cmd_with_progress,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )

                # Store process for potential cancellation
                self._active_processes[job_id] = process

                # Monitor progress in real-time
                progress_thread = None
                if progress_callback:
                    progress_thread = threading.Thread(
                        target=self._monitor_ffmpeg_progress,
                        args=(process, job_id, progress_callback),
                        daemon=True
                    )
                    progress_thread.start()

                # Wait for completion with timeout (5 minutes)
                try:
                    stdout, stderr = process.communicate(timeout=300)
                except subprocess.TimeoutExpired:
                    logger.error(f"FFmpeg command timed out for job {job_id}")
                    process.kill()
                    process.wait()
                    if job_id in self._active_processes:
                        del self._active_processes[job_id]
                    return False

                # Wait for progress thread to finish
                if progress_thread and progress_thread.is_alive():
                    progress_thread.join(timeout=2.0)

                # Remove from active processes
                if job_id in self._active_processes:
                    del self._active_processes[job_id]

                if process.returncode == 0:
                    logger.info(f"FFmpeg command completed successfully for job {job_id}")
                    
                    # Report 100% progress
                    if progress_callback:
                        progress_callback(100.0)
                    
                    # Validate output file
                    output_path = cmd[-1]  # Last argument is output file
                    if self._validate_output_file(Path(output_path)):
                        return True
                    else:
                        logger.error(f"Output file validation failed for job {job_id}")
                        return False
                else:
                    logger.error(f"FFmpeg command failed for job {job_id}: {stderr}")
                    raise FFmpegException(' '.join(cmd), stderr, process.returncode)

            except Exception as e:
                logger.error(f"Error running FFmpeg command for job {job_id}: {e}")
                # Clean up process if it's still running
                if job_id in self._active_processes:
                    try:
                        self._active_processes[job_id].kill()
                        self._active_processes[job_id].wait()
                    except:
                        pass
                    del self._active_processes[job_id]
                return False

    def _monitor_ffmpeg_progress(self, process: subprocess.Popen, job_id: str, progress_callback: Callable[[float], None]) -> None:
        """Monitor FFmpeg progress output and report progress"""
        try:
            total_duration = None
            current_time = 0.0
            
            while process.poll() is None:
                line = process.stdout.readline()
                if not line:
                    continue
                    
                line = line.strip()
                
                # Parse progress information
                if line.startswith('out_time_ms='):
                    try:
                        time_ms = int(line.split('=')[1])
                        current_time = time_ms / 1000000.0  # Convert microseconds to seconds
                    except (ValueError, IndexError):
                        continue
                        
                elif line.startswith('total_size=') and total_duration is None:
                    # Try to estimate total duration from input video
                    # This is a fallback - we'll get better duration info from job
                    pass
                    
                elif line.startswith('progress='):
                    status = line.split('=')[1]
                    if status == 'end':
                        progress_callback(100.0)
                        break
                        
                # Calculate and report progress
                if current_time > 0 and total_duration and total_duration > 0:
                    progress = min((current_time / total_duration) * 100, 99.0)
                    progress_callback(progress)
                elif current_time > 0:
                    # Estimate progress based on time (fallback)
                    # Assume average video is 30 seconds for estimation
                    estimated_duration = 30.0
                    progress = min((current_time / estimated_duration) * 100, 95.0)
                    progress_callback(progress)
                    
        except Exception as e:
            logger.warning(f"Error monitoring FFmpeg progress for job {job_id}: {e}")

    def _get_job_duration(self, job_id: str) -> Optional[float]:
        """Get total duration for a job (helper for progress calculation)"""
        # This would need to be passed from the job context
        # For now, return None and use fallback estimation
        return None

    @lru_cache(maxsize=256)  # Increased cache size
    def _get_video_duration(self, video_path: Path) -> Optional[float]:
        """Get video duration using cached FFprobe"""
        try:
            # Check cache first
            cache_key = str(video_path.absolute())
            if cache_key in self._duration_cache:
                return self._duration_cache[cache_key]

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

            duration = float(result.stdout.strip())
            
            # Cache the result
            self._duration_cache[cache_key] = duration
            self._save_duration_cache()
            
            return duration

        except Exception as e:
            logger.error(f"Failed to get duration for {video_path}: {e}")
            return None

    @lru_cache(maxsize=256)  # Increased cache size
    def _get_video_dimensions(self, video_path: Path) -> Optional[tuple]:
        """Get video dimensions using cached FFprobe"""
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
