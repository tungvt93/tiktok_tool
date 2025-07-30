"""
GIF Processor

Implementation of GIF processing and tiling operations.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np
from PIL import Image, ImageOps

from ...domain.entities.video import Video
from ...domain.entities.effect import Effect
from ...domain.value_objects.effect_type import EffectType
from ...domain.value_objects.dimensions import Dimensions
from ...domain.services.effect_processor_interface import IEffectProcessor, EffectResult
from ...shared.config import PathConfig
from ...shared.exceptions import EffectProcessingException

logger = logging.getLogger(__name__)


class GIFProcessor(IEffectProcessor):
    """Processor for GIF effects and tiling operations"""

    def __init__(self, path_config: PathConfig):
        """
        Initialize GIF processor.

        Args:
            path_config: Path configuration
        """
        self.path_config = path_config

    def can_handle(self, effect_type: EffectType) -> bool:
        """
        Check if this processor can handle the given effect type.

        Note: GIF processor doesn't handle standard effects but provides
        GIF processing utilities for other processors.

        Args:
            effect_type: The type of effect to check

        Returns:
            False - GIF processor is a utility processor
        """
        return False  # This is a utility processor, not an effect processor

    def apply_effect(self, input_video: Video, effect: Effect, output_path: Path) -> EffectResult:
        """
        Apply an effect to a video.

        Note: GIF processor doesn't apply effects directly.

        Args:
            input_video: The input video to process
            effect: The effect configuration to apply
            output_path: Where to save the processed video

        Returns:
            EffectResult indicating this processor doesn't handle effects
        """
        return EffectResult(
            success=False,
            error_message="GIF processor is a utility processor and doesn't handle effects directly"
        )

    def get_supported_effects(self) -> List[EffectType]:
        """
        Get list of effect types supported by this processor.

        Returns:
            Empty list - this is a utility processor
        """
        return []

    def validate_effect_parameters(self, effect: Effect) -> List[str]:
        """
        Validate effect parameters for this processor.

        Args:
            effect: The effect to validate

        Returns:
            List indicating this processor doesn't handle effects
        """
        return ["GIF processor doesn't handle effects directly"]

    def estimate_processing_time(self, video: Video, effect: Effect) -> float:
        """
        Estimate processing time for applying an effect.

        Args:
            video: The video to process
            effect: The effect to apply

        Returns:
            0.0 - this processor doesn't handle effects
        """
        return 0.0

    def get_processor_name(self) -> str:
        """
        Get the name of this effect processor.

        Returns:
            Human-readable processor name
        """
        return "GIF Utility Processor"

    def create_tiled_gif(self, input_gif_path: Path, output_gif_path: Path,
                        target_size: Dimensions) -> bool:
        """
        Create tiled GIF optimized for video rendering.

        Args:
            input_gif_path: Path to input GIF file
            output_gif_path: Path for output tiled GIF
            target_size: Target dimensions for tiling

        Returns:
            True if tiling was successful, False otherwise
        """
        try:
            if output_gif_path.exists():
                logger.info(f"Tiled GIF already exists: {output_gif_path}")
                return True

            if not input_gif_path.exists():
                logger.error(f"Input GIF does not exist: {input_gif_path}")
                return False

            with Image.open(input_gif_path) as original_gif:
                logger.info(f"Creating tiled GIF: {original_gif.size} -> {target_size.as_tuple()}")

                frames, durations, disposal_methods = self._process_gif_frames(
                    original_gif, target_size
                )

                if not frames:
                    logger.error("No frames processed")
                    return False

                return self._save_tiled_gif(frames, durations, disposal_methods, output_gif_path)

        except Exception as e:
            logger.error(f"Error creating tiled GIF: {e}")
            return False

    def get_or_create_tiled_gif(self, video_path: Path,
                               original_gif_path: Optional[Path] = None) -> Optional[Path]:
        """
        Get existing tiled GIF or create new one.

        Args:
            video_path: Path to video being processed
            original_gif_path: Path to original GIF file (optional)

        Returns:
            Path to tiled GIF or None if creation failed
        """
        try:
            # Create generated effects directory if it doesn't exist
            self.path_config.generated_effects_dir.mkdir(parents=True, exist_ok=True)

            # Use generated effects directory for new GIFs
            output_gif_path = (
                self.path_config.generated_effects_dir /
                f"star_tiled_{target_size.width}x{target_size.height}.gif"
            )

            # Use default GIF if none provided
            if original_gif_path is None:
                # Look for default GIF in effects directory
                default_gifs = list(self.path_config.effects_dir.glob("*.gif"))
                if default_gifs:
                    original_gif_path = default_gifs[0]
                else:
                    logger.warning("No GIF files found in effects directory")
                    return None

            # Get target size from video or use default
            target_size = Dimensions(1080, 1080)  # Default size

            if self.create_tiled_gif(original_gif_path, output_gif_path, target_size):
                return output_gif_path
            return None

        except Exception as e:
            logger.error(f"Error in get_or_create_tiled_gif: {e}")
            return None

    def _process_gif_frames(self, original_gif: Image.Image,
                           target_size: Dimensions) -> Tuple[List[Image.Image], List[int], List[int]]:
        """Process GIF frames for tiling"""
        transparency_color = original_gif.info.get('transparency')
        frames, durations, disposal_methods = [], [], []

        frame_index = 0
        while True:
            try:
                original_gif.seek(frame_index)
                frame = original_gif.copy()

                frame_duration = original_gif.info.get('duration', 100)
                disposal_method = original_gif.info.get('disposal', 2)

                processed_frame = self._create_tiled_frame(frame, target_size, transparency_color)

                frames.append(processed_frame)
                durations.append(frame_duration)
                disposal_methods.append(disposal_method)

                frame_index += 1

            except EOFError:
                break

        logger.debug(f"Processed {len(frames)} GIF frames")
        return frames, durations, disposal_methods

    def _create_tiled_frame(self, frame: Image.Image, target_size: Dimensions,
                           transparency_color: Optional[int]) -> Image.Image:
        """Create a single tiled frame"""
        frame_width, frame_height = frame.size
        tiles_x = target_size.width // frame_width + (1 if target_size.width % frame_width != 0 else 0)
        tiles_y = target_size.height // frame_height + (1 if target_size.height % frame_height != 0 else 0)

        new_frame = Image.new('RGBA', target_size.as_tuple(), (0, 0, 0, 0))

        # Process transparency
        frame = self._process_transparency(frame, transparency_color)

        # Tile and mirror for seamless pattern
        for y in range(tiles_y):
            for x in range(tiles_x):
                tile = frame.copy()

                # Mirror alternating tiles for seamless effect
                if x % 2 == 1:
                    tile = ImageOps.mirror(tile)
                if y % 2 == 1:
                    tile = ImageOps.flip(tile)

                paste_x = x * frame_width
                paste_y = y * frame_height

                # Ensure we don't paste outside target bounds
                if paste_x < target_size.width and paste_y < target_size.height:
                    new_frame.paste(tile, (paste_x, paste_y), tile)

        return new_frame

    def _process_transparency(self, frame: Image.Image,
                            transparency_color: Optional[int]) -> Image.Image:
        """Process transparency for a frame"""
        if transparency_color is not None and frame.mode == 'P':
            # Handle palette mode with transparency
            palette = frame.palette.palette
            if transparency_color * 3 + 2 < len(palette):
                trans_r = palette[transparency_color * 3]
                trans_g = palette[transparency_color * 3 + 1]
                trans_b = palette[transparency_color * 3 + 2]

                rgba_frame = frame.convert('RGBA')
                tile_data = np.array(rgba_frame)

                # Make transparent pixels fully transparent
                mask = (tile_data[:, :, 0] == trans_r) & \
                       (tile_data[:, :, 1] == trans_g) & \
                       (tile_data[:, :, 2] == trans_b)
                tile_data[:, :, 3] = np.where(mask, 0, 255)

                return Image.fromarray(tile_data)

        # Convert to RGBA if not already
        return frame.convert('RGBA') if frame.mode != 'RGBA' else frame

    def _save_tiled_gif(self, frames: List[Image.Image], durations: List[int],
                       disposal_methods: List[int], output_path: Path) -> bool:
        """Save tiled GIF with optimized parameters"""
        try:
            # Create output directory
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Prepare save parameters
            save_kwargs = {
                'save_all': True,
                'append_images': frames[1:] if len(frames) > 1 else [],
                'duration': durations,
                'loop': 0,  # Infinite loop
                'optimize': True,
                'transparency': 0,
                'disposal': disposal_methods
            }

            # Save the GIF
            frames[0].save(output_path, **save_kwargs)
            logger.info(f"Created tiled GIF: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save tiled GIF: {e}")
            return False

    def validate_gif_file(self, gif_path: Path) -> bool:
        """
        Validate that a file is a valid GIF.

        Args:
            gif_path: Path to GIF file

        Returns:
            True if file is a valid GIF, False otherwise
        """
        try:
            if not gif_path.exists():
                return False

            with Image.open(gif_path) as img:
                return img.format == 'GIF'

        except Exception as e:
            logger.warning(f"Error validating GIF file {gif_path}: {e}")
            return False

    def get_gif_info(self, gif_path: Path) -> Optional[dict]:
        """
        Get information about a GIF file.

        Args:
            gif_path: Path to GIF file

        Returns:
            Dictionary with GIF information or None if error
        """
        try:
            if not self.validate_gif_file(gif_path):
                return None

            with Image.open(gif_path) as gif:
                info = {
                    'size': gif.size,
                    'mode': gif.mode,
                    'frames': getattr(gif, 'n_frames', 1),
                    'duration': gif.info.get('duration', 100),
                    'loop': gif.info.get('loop', 0),
                    'transparency': gif.info.get('transparency'),
                    'disposal': gif.info.get('disposal')
                }

                return info

        except Exception as e:
            logger.error(f"Error getting GIF info for {gif_path}: {e}")
            return None
