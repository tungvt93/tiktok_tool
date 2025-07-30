"""
FFmpeg Service Implementation

Concrete implementation of video processing using FFmpeg.
"""

import subprocess
import logging
import threading
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
        # Limit concurrent FFmpeg processes to prevent system overload
        self._ffmpeg_semaphore = threading.Semaphore(2)  # Max 2 concurrent FFmpeg processes

    def process_video(self, job: ProcessingJob) -> ProcessingResult:
        """Process a video with effects"""
        try:
            logger.info(f"Processing video: {job.main_video.path}")
            
            # Step 1: Render video with hstack and GIF overlay (like old logic)
            temp_output = job.output_path.with_suffix('.temp.mp4')
            
            # Build command for step 1 (video merge + GIF overlay)
            cmd = self._build_processing_command(job, temp_output)
            
            # Execute step 1
            if not self._run_ffmpeg_command(cmd, job.id):
                return ProcessingResult(False, error_message="FFmpeg processing failed")
            
            # Step 2: Apply opening effects (like old logic)
            if self._has_opening_effects(job):
                success = self._apply_opening_effects(temp_output, job.output_path, job)
                # Clean up temp file
                try:
                    temp_output.unlink()
                except:
                    pass
                if not success:
                    return ProcessingResult(False, error_message="Opening effect processing failed")
            else:
                # No opening effects, just rename temp file
                try:
                    temp_output.rename(job.output_path)
                except Exception as e:
                    logger.error(f"Failed to rename temp file: {e}")
                    return ProcessingResult(False, error_message="Failed to create output file")
            
            logger.info(f"Video processing completed: {job.output_path}")
            return ProcessingResult(True, output_path=job.output_path)
            
        except Exception as e:
            logger.error(f"Error processing video {job.main_video.path}: {e}")
            return ProcessingResult.failure(str(e))

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

    def _build_processing_command(self, job: ProcessingJob, temp_output: Path) -> List[str]:
        """Build FFmpeg command for processing job"""
        cmd = ["ffmpeg", "-y"]  # -y to overwrite output files

        # Input files
        cmd.extend(["-i", str(job.main_video.path)])
        if job.background_video:
            cmd.extend(["-i", str(job.background_video.path)])

        # Add GIF inputs for GIF overlay effects
        from ...domain.value_objects.effect_type import EffectType
        gif_inputs = []
        for effect in job.effects:
            if effect.type == EffectType.GIF_OVERLAY:
                gif_path = effect.get_parameter('gif_path')
                if gif_path:
                    # Try to get or create tiled GIF
                    tiled_gif_path = self._get_or_create_tiled_gif(Path(gif_path))
                    if tiled_gif_path:
                        cmd.extend(["-i", str(tiled_gif_path)])
                        gif_inputs.append(str(tiled_gif_path))
                        logger.info(f"Using tiled GIF: {tiled_gif_path}")
                    else:
                        # Fallback to original GIF
                        cmd.extend(["-i", str(gif_path)])
                        gif_inputs.append(gif_path)
                        logger.warning(f"Using original GIF (tiled creation failed): {gif_path}")

        # Build filter complex for video processing
        filter_parts = []

        # Scale main video to half width (like old logic)
        filter_parts.append(f"[0:v]scale={self.video_config.half_width}:{self.video_config.output_height}[left]")

        # Scale background video to half width (like old logic)
        if job.background_video:
            filter_parts.append(f"[1:v]scale={self.video_config.half_width}:{self.video_config.output_height}[right]")
            # Horizontal stack like old logic
            filter_parts.append("[left][right]hstack=inputs=2[stacked]")
            video_label = "[stacked]"
        else:
            video_label = "[left]"

        # Apply effects if any
        if job.effects:
            gif_input_index = 2 if job.background_video else 1  # Start after main video (0) and background video (1)
            for i, effect in enumerate(job.effects):
                if effect.type == EffectType.GIF_OVERLAY:
                    # Handle GIF overlay effect
                    effect_filter = self._build_gif_overlay_filter(effect, video_label, f"[effect{i}]", gif_input_index)
                    if effect_filter:
                        filter_parts.append(effect_filter)
                        video_label = f"[effect{i}]"
                        gif_input_index += 1
                else:
                    # Handle other effects
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

        # Encoding settings - optimized for performance and safety
        cmd.extend([
            "-c:v", self.ffmpeg_config.codec_video,
            "-preset", "ultrafast",  # Use ultrafast for better performance
            "-crf", "28",  # Slightly higher CRF for faster encoding
            "-c:a", self.ffmpeg_config.codec_audio,
            "-threads", "0",  # Use all available threads
            "-shortest",  # Stop when shortest input ends (like old logic)
            "-movflags", "+faststart+write_colr"  # Optimize for streaming and add color info
        ])

        # Output file
        cmd.append(str(temp_output))

        return cmd

    def _has_opening_effects(self, job: ProcessingJob) -> bool:
        """Check if job has opening effects (non-GIF effects)"""
        from ...domain.value_objects.effect_type import EffectType
        for effect in job.effects:
            if effect.type != EffectType.GIF_OVERLAY:
                return True
        return False

    def _apply_opening_effects(self, input_video: Path, output_video: Path, job: ProcessingJob) -> bool:
        """Apply opening effects to video (like old logic)"""
        try:
            from ...domain.value_objects.effect_type import EffectType
            
            # Find opening effects (non-GIF effects)
            opening_effects = [effect for effect in job.effects if effect.type != EffectType.GIF_OVERLAY]
            
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
            return self._run_ffmpeg_command(cmd, "copy_video")
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
            return self._run_ffmpeg_command(cmd, "fade_effect")
        except Exception as e:
            logger.error(f"Error applying fade effect: {e}")
            return False

    def _apply_slide_effect(self, input_video: Path, output_video: Path, effect_type, duration: float) -> bool:
        """Apply slide effect"""
        try:
            from ...domain.value_objects.effect_type import EffectType
            
            width = self.video_config.output_width
            height = self.video_config.output_height
            
            if effect_type == EffectType.SLIDE_RIGHT_TO_LEFT:
                crop_filter = f"crop=w={width}:h={height}:x='if(lt(t,{duration}),{width}*(1-t/{duration}),0)':y=0"
            elif effect_type == EffectType.SLIDE_LEFT_TO_RIGHT:
                crop_filter = f"crop=w={width}:h={height}:x='if(lt(t,{duration}),{width}*(t/{duration}-1),0)':y=0"
            elif effect_type == EffectType.SLIDE_TOP_TO_BOTTOM:
                crop_filter = f"crop=w={width}:h={height}:x=0:y='if(lt(t,{duration}),{height}*(t/{duration}-1),0)'"
            elif effect_type == EffectType.SLIDE_BOTTOM_TO_TOP:
                crop_filter = f"crop=w={width}:h={height}:x=0:y='if(lt(t,{duration}),{height}*(1-t/{duration}),0)'"
            else:
                return self._copy_video(input_video, output_video)
            
            cmd = [
                "ffmpeg", "-y",
                "-i", str(input_video),
                "-vf", crop_filter,
                "-c:a", "copy",
                str(output_video)
            ]
            return self._run_ffmpeg_command(cmd, "slide_effect")
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
        elif effect.type == EffectType.GIF_OVERLAY:
            # GIF overlay effect - this will be handled differently in the main command building
            # For now, return None as GIF overlays require additional input streams
            return None
        # Add more effect filters as needed

        return None

    def _build_gif_overlay_filter(self, effect, input_label: str, output_label: str, gif_input_index: int) -> Optional[str]:
        """Build FFmpeg filter for GIF overlay effect"""
        from ...domain.value_objects.effect_type import EffectType

        if effect.type == EffectType.GIF_OVERLAY:
            # Get parameters
            x_pos = effect.get_parameter('x', 10)  # Default to 10 pixels from left
            y_pos = effect.get_parameter('y', 10)  # Default to 10 pixels from top
            scale = effect.get_parameter('scale', 1.0)  # Default scale

            # Build overlay filter - use simple overlay like old logic
            # input_label is the video stream, [gif_input_index:v] is the GIF stream
            gif_stream = f"[{gif_input_index}:v]"
            
            # Scale the GIF if needed (no loop, let FFmpeg handle it naturally)
            if scale != 1.0:
                scale_filter = f"{gif_stream}scale=iw*{scale}:ih*{scale}[gif_scaled]"
                overlay_filter = f"{input_label}[gif_scaled]overlay={x_pos}:{y_pos}{output_label}"
                return f"{scale_filter};{overlay_filter}"
            else:
                return f"{input_label}{gif_stream}overlay={x_pos}:{y_pos}{output_label}"

        return None

    def _get_or_create_tiled_gif(self, gif_path: Path) -> Optional[Path]:
        """Get existing tiled GIF or create new one"""
        try:
            from ...domain.value_objects.dimensions import Dimensions
            from ...infrastructure.processors.gif_processor import GIFProcessor
            from ...shared.config import PathConfig
            
            # Create a temporary path config for GIF processor
            path_config = PathConfig(
                effects_dir=Path("effects"),
                generated_effects_dir=Path("generated_effects"),
                output_dir=Path("output"),
                temp_dir=Path("temp")
            )
            
            gif_processor = GIFProcessor(path_config)
            tiled_gif_path = gif_processor.get_or_create_tiled_gif(
                video_path=Path("temp"),  # Dummy path
                original_gif_path=gif_path
            )
            
            return tiled_gif_path
            
        except Exception as e:
            logger.warning(f"Failed to create tiled GIF for {gif_path}: {e}")
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

    def _run_ffmpeg_command(self, cmd: List[str], job_id: str) -> bool:
        """Execute FFmpeg command with error handling"""
        # Acquire semaphore to limit concurrent processes
        with self._ffmpeg_semaphore:
            try:
                logger.info(f"Running FFmpeg command for job {job_id}: {' '.join(cmd[:5])}...")
                logger.debug(f"Full FFmpeg command: {' '.join(cmd)}")

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                # Store process for potential cancellation
                self._active_processes[job_id] = process

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

                # Remove from active processes
                if job_id in self._active_processes:
                    del self._active_processes[job_id]

                if process.returncode == 0:
                    logger.info(f"FFmpeg command completed successfully for job {job_id}")
                    
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
