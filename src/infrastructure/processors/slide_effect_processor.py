"""
Slide Effect Processor

Implementation of slide-based video effects.
"""

import logging
from pathlib import Path
from typing import List
import subprocess

from ...domain.entities.video import Video
from ...domain.entities.effect import Effect
from ...domain.value_objects.effect_type import EffectType
from ...domain.services.effect_processor_interface import IEffectProcessor, EffectResult
from ...shared.config import FFmpegConfig
from ...shared.exceptions import EffectProcessingException

logger = logging.getLogger(__name__)


class SlideEffectProcessor(IEffectProcessor):
    """Processor for slide-based effects"""

    def __init__(self, ffmpeg_config: FFmpegConfig):
        """
        Initialize slide effect processor.

        Args:
            ffmpeg_config: FFmpeg configuration
        """
        self.ffmpeg_config = ffmpeg_config

    def can_handle(self, effect_type: EffectType) -> bool:
        """
        Check if this processor can handle the given effect type.

        Args:
            effect_type: The type of effect to check

        Returns:
            True if this processor can handle the effect, False otherwise
        """
        return effect_type.is_slide_effect()

    def apply_effect(self, input_video: Video, effect: Effect, output_path: Path) -> EffectResult:
        """
        Apply a slide effect to a video.

        Args:
            input_video: The input video to process
            effect: The effect configuration to apply
            output_path: Where to save the processed video

        Returns:
            EffectResult with processing outcome
        """
        import time
        start_time = time.time()

        try:
            if not self.can_handle(effect.type):
                raise EffectProcessingException(
                    effect.type.value,
                    "Effect type not supported by slide processor",
                    input_video.path
                )

            # Validate effect parameters
            validation_errors = self.validate_effect_parameters(effect)
            if validation_errors:
                raise EffectProcessingException(
                    effect.type.value,
                    f"Invalid parameters: {'; '.join(validation_errors)}",
                    input_video.path
                )

            # Build FFmpeg command
            cmd = self._build_slide_command(input_video, effect, output_path)

            # Execute command
            success = self._run_ffmpeg_command(cmd)

            processing_time = time.time() - start_time

            if success:
                return EffectResult(
                    success=True,
                    output_path=output_path,
                    processing_time=processing_time
                )
            else:
                return EffectResult(
                    success=False,
                    error_message="FFmpeg command failed",
                    processing_time=processing_time
                )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error applying slide effect {effect.type.value}: {e}")
            return EffectResult(
                success=False,
                error_message=str(e),
                processing_time=processing_time
            )

    def get_supported_effects(self) -> List[EffectType]:
        """
        Get list of effect types supported by this processor.

        Returns:
            List of supported EffectType values
        """
        return EffectType.get_slide_effects()

    def validate_effect_parameters(self, effect: Effect) -> List[str]:
        """
        Validate effect parameters for this processor.

        Args:
            effect: The effect to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if not self.can_handle(effect.type):
            errors.append(f"Effect type {effect.type.value} not supported")
            return errors

        # Validate duration
        if effect.duration <= 0:
            errors.append("Duration must be positive")
        elif effect.duration > 10:
            errors.append("Duration too long (max 10 seconds)")

        # Validate easing parameter if present
        easing = effect.get_parameter('easing')
        if easing is not None:
            valid_easing = ['linear', 'ease-in', 'ease-out', 'ease-in-out']
            if easing not in valid_easing:
                errors.append(f"Invalid easing: {easing}. Must be one of {valid_easing}")

        return errors

    def estimate_processing_time(self, video: Video, effect: Effect) -> float:
        """
        Estimate processing time for applying an effect.

        Args:
            video: The video to process
            effect: The effect to apply

        Returns:
            Estimated processing time in seconds
        """
        if not self.can_handle(effect.type):
            return 0.0

        # Base time proportional to video duration
        base_time = video.duration * 0.2  # 20% of video duration

        # Add effect complexity factor
        complexity_factor = 1.0

        # Longer effects take slightly more time
        if effect.duration > 3:
            complexity_factor *= 1.2

        # Custom easing adds complexity
        if effect.get_parameter('easing') and effect.get_parameter('easing') != 'linear':
            complexity_factor *= 1.1

        return base_time * complexity_factor

    def get_processor_name(self) -> str:
        """
        Get the name of this effect processor.

        Returns:
            Human-readable processor name
        """
        return "Slide Effect Processor"

    def _build_slide_command(self, input_video: Video, effect: Effect, output_path: Path) -> List[str]:
        """Build FFmpeg command for slide effect"""
        cmd = ["ffmpeg", "-y", "-i", str(input_video.path)]

        # Build slide filter based on effect type
        slide_filter = self._build_slide_filter(effect, input_video.dimensions)

        cmd.extend([
            "-filter_complex", slide_filter,
            "-map", "[v]",  # Map the video output from filter
            "-map", "0:a",  # Map audio from input
            "-c:v", self.ffmpeg_config.codec_video,
            "-preset", self.ffmpeg_config.preset,
            "-c:a", "copy",  # Copy audio without re-encoding
            str(output_path)
        ])

        return cmd

    def _build_slide_filter(self, effect: Effect, dimensions) -> str:
        """Build FFmpeg filter for slide effect"""
        width = dimensions.width
        height = dimensions.height
        duration = effect.duration

        # No easing needed for simple slide effects

        if effect.type == EffectType.SLIDE_RIGHT_TO_LEFT:
            # Video slides from right to left over black background
            return (
                f"color=black:{width}x{height}:d={duration}[bg];"
                f"[0:v]scale={width}:{height}[video];"
                f"[bg][video]overlay=x='if(lt(t,{duration}),{width}-(t/{duration})*{width},0)':y=0[v]"
            )

        elif effect.type == EffectType.SLIDE_LEFT_TO_RIGHT:
            # Video slides from left to right over black background
            return (
                f"color=black:{width}x{height}:d={duration}[bg];"
                f"[0:v]scale={width}:{height}[video];"
                f"[bg][video]overlay=x='if(lt(t,{duration}),-(t/{duration})*{width}+{width},0)':y=0[v]"
            )

        elif effect.type == EffectType.SLIDE_TOP_TO_BOTTOM:
            # Video slides from top to bottom over black background
            return (
                f"color=black:{width}x{height}:d={duration}[bg];"
                f"[0:v]scale={width}:{height}[video];"
                f"[bg][video]overlay=x=0:y='if(lt(t,{duration}),-(t/{duration})*{height}+{height},0)'[v]"
            )

        elif effect.type == EffectType.SLIDE_BOTTOM_TO_TOP:
            # Video slides from bottom to top over black background
            return (
                f"color=black:{width}x{height}:d={duration}[bg];"
                f"[0:v]scale={width}:{height}[video];"
                f"[bg][video]overlay=x=0:y='if(lt(t,{duration}),{height}-(t/{duration})*{height},0)'[v]"
            )

        else:
            # Fallback - no effect
            return "[0:v]copy[v]"



    def _run_ffmpeg_command(self, cmd: List[str]) -> bool:
        """Execute FFmpeg command"""
        try:
            logger.debug(f"Running slide effect command: {' '.join(cmd[:5])}...")

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            logger.debug("Slide effect applied successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg command failed: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error running FFmpeg command: {e}")
            return False
