import os
from typing import Tuple, List, Optional
from PIL import Image, ImageOps
import numpy as np
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class GifInfo:
    """Container for GIF metadata"""
    transparency_color: Optional[int]
    background_color: Optional[int]
    frame_duration: int
    disposal_method: int

@dataclass
class TileConfig:
    """Container for tile configuration"""
    tiles_x: int
    tiles_y: int
    frame_width: int
    frame_height: int

class GifTiler:
    """Optimized GIF tiler with performance improvements"""
    
    def __init__(self, target_size: Tuple[int, int] = (1080, 1080)):
        self.target_size = target_size
        self._transparency_cache = {}
        self._palette_cache = {}
    
    def _calculate_tiles(self, frame_size: Tuple[int, int]) -> TileConfig:
        """Calculate tile configuration efficiently"""
        frame_width, frame_height = frame_size
        tiles_x = self.target_size[0] // frame_width + (1 if self.target_size[0] % frame_width != 0 else 0)
        tiles_y = self.target_size[1] // frame_height + (1 if self.target_size[1] % frame_height != 0 else 0)
        
        return TileConfig(tiles_x, tiles_y, frame_width, frame_height)
    
    def _get_transparency_mask(self, frame: Image.Image, transparency_color: int) -> np.ndarray:
        """Get transparency mask with caching for performance"""
        frame_hash = hash(frame.tobytes())
        cache_key = (frame_hash, transparency_color)
        
        if cache_key in self._transparency_cache:
            return self._transparency_cache[cache_key]
        
        if frame.mode == 'P':
            palette = frame.palette.palette
            if transparency_color * 3 + 2 >= len(palette):
                mask = np.zeros(frame.size[::-1], dtype=bool)
            else:
                trans_r = palette[transparency_color * 3]
                trans_g = palette[transparency_color * 3 + 1]
                trans_b = palette[transparency_color * 3 + 2]
                
                # Convert to RGBA once and cache
                rgba_frame = frame.convert('RGBA')
                tile_data = np.array(rgba_frame)
                
                mask = (tile_data[:, :, 0] == trans_r) & \
                       (tile_data[:, :, 1] == trans_g) & \
                       (tile_data[:, :, 2] == trans_b)
        else:
            mask = np.zeros(frame.size[::-1], dtype=bool)
        
        self._transparency_cache[cache_key] = mask
        return mask
    
    def _apply_transparency(self, frame: Image.Image, transparency_color: Optional[int]) -> Image.Image:
        """Apply transparency efficiently"""
        if transparency_color is None or frame.mode != 'P':
            return frame.convert('RGBA') if frame.mode != 'RGBA' else frame
        
        # Get cached transparency mask
        mask = self._get_transparency_mask(frame, transparency_color)
        
        # Convert to RGBA and apply transparency
        rgba_frame = frame.convert('RGBA')
        tile_data = np.array(rgba_frame)
        tile_data[:, :, 3] = np.where(mask, 0, 255)
        
        return Image.fromarray(tile_data)
    
    def _create_mirrored_tile(self, frame: Image.Image, x: int, y: int) -> Image.Image:
        """Create mirrored tile efficiently"""
        # Use single copy and apply transformations
        tile = frame
        
        if x % 2 == 1:
            tile = ImageOps.mirror(tile)
        if y % 2 == 1:
            tile = ImageOps.flip(tile)
        
        return tile
    
    def _process_frame(self, frame: Image.Image, gif_info: GifInfo) -> Image.Image:
        """Process single frame with optimized tile creation"""
        tile_config = self._calculate_tiles(frame.size)
        
        # Pre-apply transparency to avoid repeated conversions
        processed_frame = self._apply_transparency(frame, gif_info.transparency_color)
        
        # Create new frame with transparent background
        new_frame = Image.new('RGBA', self.target_size, (0, 0, 0, 0))
        
        # Optimized tile placement using vectorized operations
        for y in range(tile_config.tiles_y):
            for x in range(tile_config.tiles_x):
                # Create mirrored tile
                tile = self._create_mirrored_tile(processed_frame, x, y)
                
                # Calculate position
                paste_x = x * tile_config.frame_width
                paste_y = y * tile_config.frame_height
                
                # Paste with alpha channel
                new_frame.paste(tile, (paste_x, paste_y), tile)
        
        return new_frame
    
    def _extract_gif_info(self, gif: Image.Image, frame_index: int) -> GifInfo:
        """Extract GIF information efficiently"""
        gif.seek(frame_index)
        
        return GifInfo(
            transparency_color=gif.info.get('transparency'),
            background_color=gif.info.get('background'),
            frame_duration=gif.info.get('duration', 100),
            disposal_method=gif.info.get('disposal', 2)
        )
    
    def create_tiled_gif(self, input_path: str, output_path: str) -> bool:
        """
        Create tiled GIF with optimized performance
        
        Args:
            input_path: Path to input GIF
            output_path: Path to output GIF
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Validate input
            if not os.path.exists(input_path):
                logger.error(f"Input file not found: {input_path}")
                return False
            
            # Open GIF
            with Image.open(input_path) as original_gif:
                logger.info(f"Processing GIF: {original_gif.size} -> {self.target_size}")
                
                # Extract metadata
                transparency_color = original_gif.info.get('transparency')
                background_color = original_gif.info.get('background')
                logger.info(f"Transparency: {transparency_color}, Background: {background_color}")
                
                # Process frames
                frames = []
                durations = []
                disposal_methods = []
                
                frame_index = 0
                while True:
                    try:
                        # Extract frame info
                        gif_info = self._extract_gif_info(original_gif, frame_index)
                        
                        # Get frame
                        original_gif.seek(frame_index)
                        frame = original_gif.copy()
                        
                        # Process frame
                        processed_frame = self._process_frame(frame, gif_info)
                        
                        # Store results
                        frames.append(processed_frame)
                        durations.append(gif_info.frame_duration)
                        disposal_methods.append(gif_info.disposal_method)
                        
                        logger.info(f"Frame {frame_index}: duration={gif_info.frame_duration}, disposal={gif_info.disposal_method}")
                        
                        frame_index += 1
                        
                    except EOFError:
                        break
                
                # Save optimized GIF
                if frames:
                    self._save_gif(frames, durations, disposal_methods, output_path)
                    logger.info(f"Successfully created {len(frames)} frames")
                    return True
                else:
                    logger.error("No frames processed")
                    return False
                    
        except Exception as e:
            logger.error(f"Error processing GIF: {e}")
            return False
    
    def _save_gif(self, frames: List[Image.Image], durations: List[int], 
                  disposal_methods: List[int], output_path: str) -> None:
        """Save GIF with optimized parameters"""
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Prepare save parameters
        save_kwargs = {
            'save_all': True,
            'append_images': frames[1:],
            'duration': durations,
            'loop': 0,
            'optimize': True,
            'transparency': 0,
            'disposal': disposal_methods
        }
        
        # Save with error handling
        try:
            frames[0].save(output_path, **save_kwargs)
            logger.info(f"Saved to: {output_path}")
            logger.info(f"Size: {frames[0].size}")
        except Exception as e:
            logger.error(f"Error saving GIF: {e}")
            raise

def create_tiled_gif(input_gif_path: str, output_gif_path: str, 
                    target_size: Tuple[int, int] = (1080, 1080)) -> bool:
    """
    High-performance GIF tiler with optimized memory usage and processing
    
    Args:
        input_gif_path: Path to input GIF
        output_gif_path: Path to output GIF
        target_size: Target size (width, height)
        
    Returns:
        bool: True if successful, False otherwise
    """
    tiler = GifTiler(target_size)
    return tiler.create_tiled_gif(input_gif_path, output_gif_path)

def main():
    """Main function with improved error handling"""
    # Configuration
    input_gif = "effects/star.gif"
    output_gif = "output/star_tiled_1080x1080.gif"
    target_size = (1080, 1080)
    
    try:
        # Process GIF
        success = create_tiled_gif(input_gif, output_gif, target_size)
        
        if success:
            logger.info("GIF processing completed successfully")
        else:
            logger.error("GIF processing failed")
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
