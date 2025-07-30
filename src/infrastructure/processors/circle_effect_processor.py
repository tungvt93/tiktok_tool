"""
Circle Effect Processor

Implementation of circle-based video effects using numpy masks and OpenCV.
Based on the working implementation from old_logic.
"""

import logging
import tempfile
import os
import subprocess
import math
from pathlib import Path
from typing import List, Callable
import time

import cv2
import numpy as np

from ...domain.entities.video import Video
from ...domain.entities.effect import Effect
from ...domain.value_objects.effect_type import EffectType
from ...domain.services.effect_processor_interface import IEffectProcessor, EffectResult
from ...shared.config import FFmpegConfig
from ...shared.exceptions import EffectProcessingException

logger = logging.getLogger(__name__)


class CircleMaskGenerator:
    """Generate circle masks using numpy and OpenCV (from old_logic)"""
    
    def __init__(self, width: int, height: int, duration: float):
        self.width = width
        self.height = height
        self.duration = duration
        self.center_x = width // 2
        self.center_y = height // 2
        self.max_radius = int(np.hypot(width, height))
    
    def circle_expand_mask(self, t: float) -> np.ndarray:
        """Create expanding circle mask"""
        mask = np.zeros((self.height, self.width), dtype=np.float32)
        progress = min(1, t / self.duration)
        radius = int(progress * self.max_radius)
        
        Y, X = np.ogrid[:self.height, :self.width]
        circle = (X - self.center_x)**2 + (Y - self.center_y)**2 <= radius**2
        mask[circle] = 1
        return mask
    
    def circle_shrink_mask(self, t: float) -> np.ndarray:
        """Create shrinking circle mask - black background with shrinking circle revealing video"""
        mask = np.zeros((self.height, self.width), dtype=np.float32)
        progress = min(1, t / self.duration)
        radius = int((1 - progress) * self.max_radius)
        
        Y, X = np.ogrid[:self.height, :self.width]
        circle = (X - self.center_x)**2 + (Y - self.center_y)**2 <= radius**2
        
        # Mask = 1 outside circle (black background), 0 inside circle (video visible)
        mask[~circle] = 1  # Outside circle = black background
        mask[circle] = 0   # Inside circle = video visible
        return mask
    
    def circle_rotate_mask(self, t: float, clockwise: bool = True) -> np.ndarray:
        """Create rotating circle mask"""
        mask = np.zeros((self.height, self.width), dtype=np.float32)
        progress = min(1, t / self.duration)
        sweep_angle = progress * 2 * np.pi
        if not clockwise:
            sweep_angle = -sweep_angle
        
        Y, X = np.ogrid[:self.height, :self.width]
        angles = np.arctan2(Y - self.center_y, X - self.center_x) % (2 * np.pi)
        radius = np.hypot(X - self.center_x, Y - self.center_y)
        
        # Normalize angles for comparison
        if clockwise:
            # For clockwise, we want angles from 0 to sweep_angle
            angle_condition = angles <= sweep_angle
        else:
            # For counter-clockwise, we want angles from (2*pi - sweep_angle) to 2*pi
            angle_condition = angles >= (2 * np.pi + sweep_angle) % (2 * np.pi)
        
        mask[(angle_condition) & (radius <= self.max_radius)] = 1
        return mask
    
    def create_mask_video(self, mask_func: Callable, output_path: str, input_video: str, fps: int = 30) -> bool:
        """Create a video from mask function"""
        try:
            # Get input video duration
            result = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries", "format=duration", 
                "-of", "default=noprint_wrappers=1:nokey=1", input_video
            ], capture_output=True, text=True, check=True)
            
            input_duration = float(result.stdout.strip())
            total_frames = int(input_duration * fps)
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (self.width, self.height))
            
            for frame_idx in range(total_frames):
                t = frame_idx / fps
                
                # Apply effect only during the specified duration
                if t <= self.duration:
                    mask = mask_func(t)
                else:
                    # After effect duration, show full video (all pixels visible)
                    mask = np.ones((self.height, self.width), dtype=np.float32)
                
                # Convert to 8-bit RGB (3 channels)
                mask_8bit = (mask * 255).astype(np.uint8)
                mask_rgb = np.stack([mask_8bit, mask_8bit, mask_8bit], axis=2)  # Convert to RGB
                
                # Write frame
                out.write(mask_rgb)
            
            out.release()
            return True
            
        except Exception as e:
            logger.error(f"Error creating mask video: {e}")
            return False


class CircleEffectProcessor(IEffectProcessor):
    """Processor for circle-based effects using numpy masks"""

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
        Apply a circle effect to a video using numpy masks.

        Args:
            input_video: The input video to process
            effect: The effect configuration to apply
            output_path: Where to save the processed video

        Returns:
            EffectResult with processing outcome
        """
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

            # Apply circle effect using mask approach
            success = self._apply_circle_effect_with_mask(input_video, effect, output_path)

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
                    output_path=None,
                    processing_time=processing_time,
                    error_message="Failed to apply circle effect"
                )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error applying circle effect: {e}")
            return EffectResult(
                success=False,
                output_path=None,
                processing_time=processing_time,
                error_message=str(e)
            )

    def get_supported_effects(self) -> List[EffectType]:
        """
        Get list of supported effect types.

        Returns:
            List of supported effect types
        """
        return [
            EffectType.CIRCLE_EXPAND,
            EffectType.CIRCLE_CONTRACT,
            EffectType.CIRCLE_ROTATE_CW,
            EffectType.CIRCLE_ROTATE_CCW
        ]

    def validate_effect_parameters(self, effect: Effect) -> List[str]:
        """
        Validate effect parameters.

        Args:
            effect: The effect to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if effect.duration <= 0:
            errors.append("Duration must be positive")

        if effect.duration > 30:  # Reasonable limit
            errors.append("Duration too long (max 30 seconds)")

        return errors

    def estimate_processing_time(self, video: Video, effect: Effect) -> float:
        """
        Estimate processing time for the effect.

        Args:
            video: The video to process
            effect: The effect to apply

        Returns:
            Estimated processing time in seconds
        """
        # Base time for mask generation + FFmpeg processing
        base_time = 2.0
        
        # Add time based on video duration and effect complexity
        duration_factor = video.duration / 10.0  # Normalize to 10 seconds
        complexity_factor = 1.5 if effect.type in [EffectType.CIRCLE_ROTATE_CW, EffectType.CIRCLE_ROTATE_CCW] else 1.0
        
        return base_time + (duration_factor * complexity_factor)

    def get_processor_name(self) -> str:
        """
        Get the name of this processor.

        Returns:
            Processor name
        """
        return "CircleEffectProcessor"

    def _apply_circle_effect_with_mask(self, input_video: Video, effect: Effect, output_path: Path) -> bool:
        """Apply circle effect using mask approach (from old_logic)"""
        try:
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                mask_video = os.path.join(temp_dir, "mask.mp4")
                
                # Create mask generator
                mask_generator = CircleMaskGenerator(
                    input_video.dimensions.width,
                    input_video.dimensions.height,
                    effect.duration
                )
                
                # Create mask based on effect type
                effect_type_map = {
                    EffectType.CIRCLE_EXPAND: mask_generator.circle_expand_mask,
                    EffectType.CIRCLE_CONTRACT: mask_generator.circle_shrink_mask,
                    EffectType.CIRCLE_ROTATE_CW: lambda t: mask_generator.circle_rotate_mask(t, clockwise=True),
                    EffectType.CIRCLE_ROTATE_CCW: lambda t: mask_generator.circle_rotate_mask(t, clockwise=False)
                }
                
                mask_func = effect_type_map.get(effect.type)
                if not mask_func:
                    logger.error(f"Unknown effect type: {effect.type}")
                    return False
                
                # Create mask video
                success = mask_generator.create_mask_video(
                    mask_func, 
                    mask_video, 
                    str(input_video.path)
                )
                
                if not success:
                    return False
                
                # Apply mask to video using FFmpeg
                cmd = self._build_mask_command(
                    str(input_video.path),
                    mask_video,
                    str(output_path),
                    input_video.dimensions.width,
                    input_video.dimensions.height
                )
                
                return self._run_ffmpeg_command(cmd)
                
        except Exception as e:
            logger.error(f"Error applying circle effect with mask: {e}")
            return False

    def _build_mask_command(self, input_video: str, mask_video: str, output_video: str, width: int, height: int) -> List[str]:
        """Build FFmpeg command for applying mask to video"""
        cmd = [
            "ffmpeg", "-y",
            "-i", input_video,
            "-i", mask_video,
            "-filter_complex",
            f"color=black:{width}x{height}[bg];"
            f"[0:v]scale={width}:{height}[video];"
            f"[1:v]scale={width}:{height}[mask];"
            f"[video][mask]alphamerge[alpha];"
            f"[bg][alpha]overlay=shortest=1",
            "-c:v", self.ffmpeg_config.codec_video,
            "-preset", self.ffmpeg_config.preset,
            "-c:a", "copy",  # Copy audio without re-encoding
            output_video
        ]
        
        return cmd

    def _run_ffmpeg_command(self, cmd: List[str]) -> bool:
        """Run FFmpeg command"""
        try:
            logger.debug(f"Running FFmpeg command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg command failed: {result.stderr}")
                return False
            
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg command timed out")
            return False
        except Exception as e:
            logger.error(f"Error running FFmpeg command: {e}")
            return False
