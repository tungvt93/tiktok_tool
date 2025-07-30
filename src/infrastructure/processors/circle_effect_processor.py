"""
Circle Effect Processor

Implementation of circle-based video effects.
"""

import logging
from pathlib import Path
from typing import List
import subprocess
import math

from ...domain.entities.video import Video
from ...domain.entities.effect import Effect
from ...domain.value_objects.effect_type import EffectType
from ...domain.services.effect_processor_interface import IEffectProcessor, EffectResult
from ...shared.config import FFmpegConfig
from ...shared.exceptions import EffectProcessingException

logger = logging.getLogger(__name__)


class CircleEffectProcessor(IEffectProcessor):
    """Processor for circle-based effects"""

    def __init__(self, ffmpeg_config: FFmpegConfig):
        """
        Initialize circle effect processor.

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
        return effect_type.is_circle_effect()

    def apply_effect(self, input_video: Video, effect: Effect, output_path: Path) -> EffectResult:
        """
        Apply a circle effect to a video.

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
                    "Effect type not supported by circle processor",
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

            # Try to use external circle effects processor if available
            try:
                success = self._apply_with_external_processor(input_video, effect, output_path)
                if success:
                    processing_time = time.time() - start_time
                    return EffectResult(
                        success=True,
                        output_path=output_path,
                        processing_time=processing_time
                    )
            except ImportError:
                logger.info("External circle processor not available, using FFmpeg fallback")

            # Fallback to FFmpeg implementation
            cmd = self._build_circle_command(input_video, effect, output_path)
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
            logger.error(f"Error applying circle effect {effect.type.value}: {e}")
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
        return EffectType.get_circle_effects()

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

        # Validate radius parameter if present
        radius = effect.get_parameter('radius')
        if radius is not None:
            if not isinstance(radius, (int, float)) or radius <= 0:
                errors.append("Radius must be a positive number")
            elif radius > 1000:
                errors.append("Radius too large (max 1000)")

        # Validate center point if present
        center_x = effect.get_parameter('center_x')
        center_y = effect.get_parameter('center_y')
        if center_x is not None and (not isinstance(center_x, (int, float)) or center_x < 0):
            errors.append("Center X must be a non-negative number")
        if center_y is not None and (not isinstance(center_y, (int, float)) or center_y < 0):
            errors.append("Center Y must be a non-negative number")

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

        # Circle effects are more complex than slide effects
        base_time = video.duration * 0.4  # 40% of video duration

        # Add complexity factors
        complexity_factor = 1.0

        # Longer effects take more time
        if effect.duration > 3:
            complexity_factor *= 1.3

        # Custom radius or center point adds complexity
        if effect.get_parameter('radius') or effect.get_parameter('center_x'):
            complexity_factor *= 1.2

        # Rotation effects are more complex
        if effect.type in [EffectType.CIRCLE_ROTATE_CW, EffectType.CIRCLE_ROTATE_CCW]:
            complexity_factor *= 1.5

        return base_time * complexity_factor

    def get_processor_name(self) -> str:
        """
        Get the name of this effect processor.

        Returns:
            Human-readable processor name
        """
        return "Circle Effect Processor"

    def _apply_with_external_processor(self, input_video: Video, effect: Effect, output_path: Path) -> bool:
        """Try to apply effect using external circle effects processor"""
        try:
            # This would import the external processor if available
            from circle_effects_processor import CircleEffectsProcessor

            width = input_video.dimensions.width
            height = input_video.dimensions.height
            duration = effect.duration

            processor = CircleEffectsProcessor(width, height, duration, str(input_video.path))

            # Map effect types to processor methods
            effect_type_map = {
                EffectType.CIRCLE_EXPAND: "expand",
                EffectType.CIRCLE_CONTRACT: "shrink",
                EffectType.CIRCLE_ROTATE_CW: "rotate_cw",
                EffectType.CIRCLE_ROTATE_CCW: "rotate_ccw"
            }

            effect_type_str = effect_type_map.get(effect.type)
            if not effect_type_str:
                return False

            return processor.apply_circle_effect(
                str(input_video.path),
                str(output_path),
                effect_type_str
            )

        except ImportError:
            raise  # Re-raise to indicate external processor not available
        except Exception as e:
            logger.warning(f"External circle processor failed: {e}")
            return False

    def _build_circle_command(self, input_video: Video, effect: Effect, output_path: Path) -> List[str]:
        """Build FFmpeg command for circle effect (fallback implementation)"""
        cmd = ["ffmpeg", "-y", "-i", str(input_video.path)]

        # Build circle filter based on effect type
        circle_filter = self._build_circle_filter(effect, input_video.dimensions)

        cmd.extend([
            "-filter_complex", circle_filter,
            "-c:v", self.ffmpeg_config.codec_video,
            "-preset", self.ffmpeg_config.preset,
            "-c:a", "copy",  # Copy audio without re-encoding
            str(output_path)
        ])

        return cmd

    def _build_circle_filter(self, effect: Effect, dimensions) -> str:
        """Build FFmpeg filter for circle effect (simplified fallback)"""
        width = dimensions.width
        height = dimensions.height
        duration = effect.duration

        # Get center point (default to center of video)
        center_x = effect.get_parameter('center_x', width // 2)
        center_y = effect.get_parameter('center_y', height // 2)

        # Calculate maximum radius (distance to farthest corner)
        max_radius = math.sqrt(
            max(center_x, width - center_x) ** 2 +
            max(center_y, height - center_y) ** 2
        )

        # Get custom radius or use calculated max
        radius = effect.get_parameter('radius', max_radius)

        if effect.type == EffectType.CIRCLE_EXPAND:
            # Start with small circle and expand
            radius_expr = f"if(lt(t,{duration}), {radius}*t/{duration}, {radius})"

        elif effect.type == EffectType.CIRCLE_CONTRACT:
            # Start with full circle and contract
            radius_expr = f"if(lt(t,{duration}), {radius}*(1-t/{duration}), 0)"

        elif effect.type in [EffectType.CIRCLE_ROTATE_CW, EffectType.CIRCLE_ROTATE_CCW]:
            # Rotating circle mask (simplified)
            rotation_speed = 360 / duration  # degrees per second
            direction = 1 if effect.type == EffectType.CIRCLE_ROTATE_CW else -1
            radius_expr = str(radius)

        else:
            # Fallback - no effect
            return "[0:v]copy[v]"

        # Create circular mask using geq filter (simplified approach)
        # This is a basic implementation - the external processor would be much better
        mask_filter = (
            f"geq=r='if(lt(sqrt(pow(X-{center_x},2)+pow(Y-{center_y},2)),{radius_expr}),255,0)':"
            f"g='if(lt(sqrt(pow(X-{center_x},2)+pow(Y-{center_y},2)),{radius_expr}),255,0)':"
            f"b='if(lt(sqrt(pow(X-{center_x},2)+pow(Y-{center_y},2)),{radius_expr}),255,0)'"
        )

        return f"[0:v]{mask_filter}[v]"

    def _run_ffmpeg_command(self, cmd: List[str]) -> bool:
        """Execute FFmpeg command"""
        try:
            logger.debug(f"Running circle effect command: {' '.join(cmd[:5])}...")

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )

            logger.debug("Circle effect applied successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg command failed: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error running FFmpeg command: {e}")
            return False
