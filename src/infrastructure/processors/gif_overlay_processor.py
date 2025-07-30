"""
GIF Overlay Processor

Implementation of GIF overlay effects for video processing.
"""

import logging
import subprocess
from pathlib import Path
from typing import List, Optional

from ...domain.entities.video import Video
from ...domain.entities.effect import Effect
from ...domain.value_objects.effect_type import EffectType
from ...domain.services.effect_processor_interface import IEffectProcessor, EffectResult
from ...shared.config import FFmpegConfig
from ...shared.exceptions import EffectProcessingException

logger = logging.getLogger(__name__)


class GIFOverlayProcessor(IEffectProcessor):
    """Processor for GIF overlay effects"""

    def __init__(self, ffmpeg_config: FFmpegConfig, path_config=None):
        """
        Initialize GIF overlay processor.

        Args:
            ffmpeg_config: FFmpeg configuration
            path_config: Path configuration for accessing GIF files
        """
        self.ffmpeg_config = ffmpeg_config
        self.path_config = path_config

    def can_handle(self, effect_type: EffectType) -> bool:
        """
        Check if this processor can handle the given effect type.

        Args:
            effect_type: The type of effect to check

        Returns:
            True if this processor can handle the effect type
        """
        return effect_type == EffectType.GIF_OVERLAY

    def apply_effect(self, input_video: Video, effect: Effect, output_path: Path) -> EffectResult:
        """
        Apply a GIF overlay effect to a video.

        Args:
            input_video: The input video to process
            effect: The effect configuration to apply
            output_path: Where to save the processed video

        Returns:
            EffectResult with success status and output information
        """
        import time
        start_time = time.time()

        try:
            # Validate effect
            validation_errors = self.validate_effect_parameters(effect)
            if validation_errors:
                error_msg = f"Effect validation failed: {'; '.join(validation_errors)}"
                return EffectResult(False, error_message=error_msg)

            # Get GIF path from effect parameters
            gif_path = effect.get_parameter('gif_path')
            if not gif_path:
                return EffectResult(False, error_message="GIF path not specified in effect parameters")

            gif_path = Path(gif_path)
            if not gif_path.exists():
                return EffectResult(False, error_message=f"GIF file not found: {gif_path}")

            # Try to get or create tiled GIF if path_config is available
            if self.path_config:
                try:
                    from .gif_processor import GIFProcessor
                    gif_processor = GIFProcessor(self.path_config)
                    tiled_gif_path = gif_processor.get_or_create_tiled_gif(
                        video_path=input_video.path,
                        original_gif_path=gif_path
                    )
                    if tiled_gif_path:
                        gif_path = tiled_gif_path
                        logger.info(f"Using tiled GIF: {gif_path}")
                except Exception as e:
                    logger.warning(f"Failed to create tiled GIF, using original: {e}")

            # Create output directory
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Build FFmpeg command
            cmd = self._build_gif_overlay_command(input_video, effect, output_path)

            # Execute command
            success = self._run_ffmpeg_command(cmd)

            if success:
                processing_time = time.time() - start_time
                return EffectResult(
                    True,
                    output_path=output_path,
                    metadata={
                        'processing_time': processing_time,
                        'gif_path': str(gif_path),
                        'effect_duration': effect.duration
                    }
                )
            else:
                return EffectResult(False, error_message="FFmpeg processing failed")

        except Exception as e:
            logger.error(f"Error applying GIF overlay effect: {e}")
            return EffectResult(False, error_message=str(e))

    def get_supported_effects(self) -> List[EffectType]:
        """
        Get list of effect types supported by this processor.

        Returns:
            List of supported EffectType values
        """
        return [EffectType.GIF_OVERLAY]

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

        # Validate GIF path
        gif_path = effect.get_parameter('gif_path')
        if not gif_path:
            errors.append("GIF path is required")
        else:
            gif_path = Path(gif_path)
            if not gif_path.exists():
                errors.append(f"GIF file not found: {gif_path}")
            elif not gif_path.suffix.lower() == '.gif':
                errors.append(f"File must be a GIF: {gif_path}")

        # Validate duration
        if effect.duration <= 0:
            errors.append("Duration must be positive")
        elif effect.duration > 60:
            errors.append("Duration too long (max 60 seconds)")

        # Validate position parameters
        x_pos = effect.get_parameter('x')
        y_pos = effect.get_parameter('y')
        if x_pos is not None and (not isinstance(x_pos, (int, float)) or x_pos < 0):
            errors.append("X position must be a non-negative number")
        if y_pos is not None and (not isinstance(y_pos, (int, float)) or y_pos < 0):
            errors.append("Y position must be a non-negative number")

        # Validate scale parameter
        scale = effect.get_parameter('scale')
        if scale is not None and (not isinstance(scale, (int, float)) or scale <= 0):
            errors.append("Scale must be a positive number")

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

        # GIF overlay effects are moderately complex
        base_time = video.duration * 0.3  # 30% of video duration

        # Add complexity factors
        complexity_factor = 1.0

        # Longer effects take more time
        if effect.duration > 10:
            complexity_factor *= 1.2

        # Custom positioning or scaling adds complexity
        if effect.get_parameter('x') or effect.get_parameter('y') or effect.get_parameter('scale'):
            complexity_factor *= 1.1

        return base_time * complexity_factor

    def get_processor_name(self) -> str:
        """
        Get the name of this effect processor.

        Returns:
            Human-readable processor name
        """
        return "GIF Overlay Processor"

    def _build_gif_overlay_command(self, input_video: Video, effect: Effect, output_path: Path) -> List[str]:
        """Build FFmpeg command for GIF overlay effect"""
        cmd = ["ffmpeg", "-y"]

        # Input files
        cmd.extend(["-i", str(input_video.path)])
        
        # GIF input
        gif_path = effect.get_parameter('gif_path')
        cmd.extend(["-i", str(gif_path)])

        # Build overlay filter
        overlay_filter = self._build_overlay_filter(effect, input_video.dimensions)

        cmd.extend([
            "-filter_complex", overlay_filter,
            "-c:v", self.ffmpeg_config.codec_video,
            "-preset", self.ffmpeg_config.preset,
            "-c:a", "copy",  # Copy audio without re-encoding
            str(output_path)
        ])

        return cmd

    def _build_overlay_filter(self, effect: Effect, video_dimensions) -> str:
        """Build FFmpeg overlay filter for GIF"""
        # Get parameters
        x_pos = effect.get_parameter('x', 10)  # Default to 10 pixels from left
        y_pos = effect.get_parameter('y', 10)  # Default to 10 pixels from top
        scale = effect.get_parameter('scale', 1.0)  # Default scale

        # Build overlay filter
        # [0:v] is the main video, [1:v] is the GIF
        # Loop the GIF and scale if needed
        if scale != 1.0:
            scale_filter = f"[1:v]scale=iw*{scale}:ih*{scale},loop=-1:1[gif_scaled]"
            overlay_filter = f"[0:v][gif_scaled]overlay={x_pos}:{y_pos}"
            return f"{scale_filter};{overlay_filter}"
        else:
            return f"[1:v]loop=-1:1[gif_looped];[0:v][gif_looped]overlay={x_pos}:{y_pos}"

    def _run_ffmpeg_command(self, cmd: List[str]) -> bool:
        """Execute FFmpeg command with error handling"""
        try:
            logger.info(f"Running GIF overlay FFmpeg command: {' '.join(cmd[:5])}...")

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=300  # 5 minutes timeout
            )

            logger.info("GIF overlay FFmpeg command completed successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"GIF overlay FFmpeg command failed: {e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            logger.error("GIF overlay FFmpeg command timed out")
            return False
        except Exception as e:
            logger.error(f"Error running GIF overlay FFmpeg command: {e}")
            return False 