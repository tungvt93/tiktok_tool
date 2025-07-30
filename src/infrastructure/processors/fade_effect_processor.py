"""
Fade Effect Processor

Implementation of fade-based video effects.
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


class FadeEffectProcessor(IEffectProcessor):
    """Processor for fade-based effects"""

    def __init__(self, ffmpeg_config: FFmpegConfig):
        """
        Initialize fade effect processor.

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
        return effect_type == EffectType.FADE_IN

    def apply_effect(self, input_video: Video, effect: Effect, output_path: Path) -> EffectResult:
        """
        Apply a fade effect to a video.

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
                    "Effect type not supported by fade processor",
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
            cmd = self._build_fade_command(input_video, effect, output_path)

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
            logger.error(f"Error applying fade effect {effect.type.value}: {e}")
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
        return [EffectType.FADE_IN]

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
        elif effect.duration > 30:
            errors.append("Duration too long (max 30 seconds)")

        # Validate fade color if present
        fade_color = effect.get_parameter('color')
        if fade_color is not None:
            if not isinstance(fade_color, str):
                errors.append("Fade color must be a string")
            elif not self._is_valid_color(fade_color):
                errors.append("Invalid color format (use hex like #000000 or color names)")

        # Validate alpha parameter if present
        alpha = effect.get_parameter('alpha')
        if alpha is not None:
            if not isinstance(alpha, (int, float)) or not (0 <= alpha <= 1):
                errors.append("Alpha must be a number between 0 and 1")

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

        # Fade effects are relatively simple
        base_time = video.duration * 0.15  # 15% of video duration

        # Add complexity factors
        complexity_factor = 1.0

        # Longer fade duration adds slight complexity
        if effect.duration > 5:
            complexity_factor *= 1.1

        # Custom color or alpha adds minimal complexity
        if effect.get_parameter('color') or effect.get_parameter('alpha'):
            complexity_factor *= 1.05

        return base_time * complexity_factor

    def get_processor_name(self) -> str:
        """
        Get the name of this effect processor.

        Returns:
            Human-readable processor name
        """
        return "Fade Effect Processor"

    def _build_fade_command(self, input_video: Video, effect: Effect, output_path: Path) -> List[str]:
        """Build FFmpeg command for fade effect"""
        cmd = ["ffmpeg", "-y", "-i", str(input_video.path)]

        # Build fade filter
        fade_filter = self._build_fade_filter(effect, input_video.dimensions)

        cmd.extend([
            "-filter_complex", fade_filter,
            "-c:v", self.ffmpeg_config.codec_video,
            "-preset", self.ffmpeg_config.preset,
            "-c:a", "copy",  # Copy audio without re-encoding
            str(output_path)
        ])

        return cmd

    def _build_fade_filter(self, effect: Effect, dimensions) -> str:
        """Build FFmpeg filter for fade effect"""
        width = dimensions.width
        height = dimensions.height
        duration = effect.duration

        # Get fade parameters
        fade_color = effect.get_parameter('color', 'black')
        alpha = effect.get_parameter('alpha', 1.0)

        # Create background color
        color_filter = f"color={fade_color}:{width}x{height}[bg]"

        # Create fade filter for main video
        fade_filter = f"[0:v]fade=t=in:st=0:d={duration}:alpha={alpha}[faded]"

        # Overlay faded video on background
        overlay_filter = "[bg][faded]overlay=shortest=1[v]"

        return f"{color_filter};{fade_filter};{overlay_filter}"

    def _is_valid_color(self, color: str) -> bool:
        """Validate color format"""
        # Check hex color format
        if color.startswith('#') and len(color) == 7:
            try:
                int(color[1:], 16)
                return True
            except ValueError:
                return False

        # Check common color names
        valid_colors = {
            'black', 'white', 'red', 'green', 'blue', 'yellow', 'cyan', 'magenta',
            'gray', 'grey', 'orange', 'purple', 'brown', 'pink', 'transparent'
        }

        return color.lower() in valid_colors

    def _run_ffmpeg_command(self, cmd: List[str]) -> bool:
        """Execute FFmpeg command"""
        try:
            logger.debug(f"Running fade effect command: {' '.join(cmd[:5])}...")

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            logger.debug("Fade effect applied successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg command failed: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error running FFmpeg command: {e}")
            return False
