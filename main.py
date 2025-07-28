"""
Optimized Video Processing Tool
Handles video merging with background loops and effects
"""

import os
import subprocess
from glob import glob
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
import tempfile
from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageOps
import numpy as np
import logging
from functools import lru_cache
import json
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EffectType(Enum):
    """Types of opening effects"""
    NONE = "none"
    SLIDE_RIGHT_TO_LEFT = "slide_right_to_left"
    SLIDE_LEFT_TO_RIGHT = "slide_left_to_right"
    SLIDE_TOP_TO_BOTTOM = "slide_top_to_bottom"
    SLIDE_BOTTOM_TO_TOP = "slide_bottom_to_top"
    CIRCLE_EXPAND = "circle_expand"
    CIRCLE_CONTRACT = "circle_contract"
    CIRCLE_ROTATE_CW = "circle_rotate_cw"
    CIRCLE_ROTATE_CCW = "circle_rotate_ccw"
    FADE_IN = "fade_in"

@dataclass
class VideoConfig:
    """Configuration for video processing"""
    # Output dimensions
    OUTPUT_WIDTH: int = 1080
    OUTPUT_HEIGHT: int = 1080
    HALF_WIDTH: int = 540
    
    # Video processing
    SPEED_MULTIPLIER: float = 1.3
    FRAME_RATE: int = 10
    CRF_VALUE: int = 23
    
    # Opening effect settings
    OPENING_EFFECT: EffectType = EffectType.NONE
    OPENING_DURATION: float = 2.0  # Duration of opening effect in seconds
    
    # Paths
    INPUT_DIR: str = "dongphuc"
    BACKGROUND_DIR: str = "video_chia_2"
    OUTPUT_DIR: str = "output"
    EFFECTS_DIR: str = "effects"
    GENERATED_EFFECTS_DIR: str = "generated_effects"  # New folder for generated GIFs
    
    # File patterns
    INPUT_PATTERN: str = "*.mp4"
    BACKGROUND_PATTERN: str = "*.mp4"
    
    @property
    def output_size(self) -> Tuple[int, int]:
        return (self.OUTPUT_WIDTH, self.OUTPUT_HEIGHT)

@dataclass
class FFmpegConfig:
    """FFmpeg command configurations"""
    PRESET: str = "ultrafast"
    CODEC_VIDEO: str = "libx264"
    CODEC_AUDIO: str = "aac"
    THREADS: str = "0"

class VideoProcessor:
    """Main video processing class"""
    
    def __init__(self, config: VideoConfig = None):
        self.config = config or VideoConfig()
        self.ffmpeg_config = FFmpegConfig()
        self._cache_file = "video_cache.json"
        self._load_cache()
    
    def _load_cache(self):
        """Load cached video metadata"""
        try:
            if os.path.exists(self._cache_file):
                with open(self._cache_file, 'r') as f:
                    self._cache = json.load(f)
            else:
                self._cache = {}
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            self._cache = {}
    
    def _save_cache(self):
        """Save cached video metadata"""
        try:
            with open(self._cache_file, 'w') as f:
                json.dump(self._cache, f)
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def run_ffmpeg(self, cmd: List[str], silent: bool = False) -> bool:
        """Execute FFmpeg command with error handling"""
        try:
            if not silent:
                logger.info(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd, 
                check=True, 
                stdout=subprocess.DEVNULL if silent else None,
                stderr=subprocess.PIPE if silent else None
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg command failed: {e}")
            if silent and e.stderr:
                logger.error(f"FFmpeg error: {e.stderr.decode()}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error running FFmpeg: {e}")
            return False
    
    @lru_cache(maxsize=128)
    def get_video_duration(self, path: str) -> Optional[float]:
        """Get video duration with caching"""
        if path in self._cache.get('duration', {}):
            return self._cache['duration'][path]
        
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
                 "-of", "default=noprint_wrappers=1:nokey=1", path],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                check=True
            )
            duration = float(result.stdout.strip())
            
            # Update cache
            if 'duration' not in self._cache:
                self._cache['duration'] = {}
            self._cache['duration'][path] = duration
            self._save_cache()
            
            return duration
        except Exception as e:
            logger.error(f"Failed to get duration for {path}: {e}")
            return None
    
    @lru_cache(maxsize=128)
    def get_video_dimensions(self, video_path: str) -> Optional[Tuple[int, int]]:
        """Get video dimensions with caching"""
        if video_path in self._cache.get('dimensions', {}):
            cached = self._cache['dimensions'][video_path]
            return (cached['width'], cached['height'])
        
        try:
            result = subprocess.run([
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height", "-of", "csv=p=0", video_path
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True)
            
            width, height = map(int, result.stdout.strip().split(','))
            
            # Update cache
            if 'dimensions' not in self._cache:
                self._cache['dimensions'] = {}
            self._cache['dimensions'][video_path] = {'width': width, 'height': height}
            self._save_cache()
            
            return width, height
        except Exception as e:
            logger.error(f"Failed to get dimensions for {video_path}: {e}")
            return None

class GIFProcessor:
    """Handles GIF processing and tiling"""
    
    def __init__(self, config: VideoConfig):
        self.config = config
    
    def create_tiled_gif(self, input_gif_path: str, output_gif_path: str, 
                        target_size: Tuple[int, int]) -> bool:
        """Create tiled GIF optimized for video rendering"""
        try:
            if os.path.exists(output_gif_path):
                logger.info(f"GIF already exists: {output_gif_path}")
                return True
            
            with Image.open(input_gif_path) as original_gif:
                logger.info(f"Creating tiled GIF: {original_gif.size} -> {target_size}")
                
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
    
    def _process_gif_frames(self, original_gif: Image.Image, 
                           target_size: Tuple[int, int]) -> Tuple[List[Image.Image], List[int], List[int]]:
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
        
        return frames, durations, disposal_methods
    
    def _create_tiled_frame(self, frame: Image.Image, target_size: Tuple[int, int], 
                           transparency_color: Optional[int]) -> Image.Image:
        """Create a single tiled frame"""
        frame_width, frame_height = frame.size
        tiles_x = target_size[0] // frame_width + (1 if target_size[0] % frame_width != 0 else 0)
        tiles_y = target_size[1] // frame_height + (1 if target_size[1] % frame_height != 0 else 0)
        
        new_frame = Image.new('RGBA', target_size, (0, 0, 0, 0))
        
        # Process transparency
        frame = self._process_transparency(frame, transparency_color)
        
        # Tile and mirror
        for y in range(tiles_y):
            for x in range(tiles_x):
                tile = frame.copy()
                
                if x % 2 == 1:
                    tile = ImageOps.mirror(tile)
                if y % 2 == 1:
                    tile = ImageOps.flip(tile)
                
                paste_x = x * frame_width
                paste_y = y * frame_height
                new_frame.paste(tile, (paste_x, paste_y), tile)
        
        return new_frame
    
    def _process_transparency(self, frame: Image.Image, 
                            transparency_color: Optional[int]) -> Image.Image:
        """Process transparency for a frame"""
        if transparency_color is not None and frame.mode == 'P':
            palette = frame.palette.palette
            if transparency_color * 3 + 2 < len(palette):
                trans_r = palette[transparency_color * 3]
                trans_g = palette[transparency_color * 3 + 1]
                trans_b = palette[transparency_color * 3 + 2]
                
                rgba_frame = frame.convert('RGBA')
                tile_data = np.array(rgba_frame)
                mask = (tile_data[:, :, 0] == trans_r) & \
                       (tile_data[:, :, 1] == trans_g) & \
                       (tile_data[:, :, 2] == trans_b)
                tile_data[:, :, 3] = np.where(mask, 0, 255)
                return Image.fromarray(tile_data)
        
        return frame.convert('RGBA') if frame.mode != 'RGBA' else frame
    
    def _save_tiled_gif(self, frames: List[Image.Image], durations: List[int], 
                       disposal_methods: List[int], output_path: str) -> bool:
        """Save tiled GIF with optimized parameters"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            save_kwargs = {
                'save_all': True,
                'append_images': frames[1:],
                'duration': durations,
                'loop': 0,
                'optimize': True,
                'transparency': 0,
                'disposal': disposal_methods
            }
            
            frames[0].save(output_path, **save_kwargs)
            logger.info(f"Created tiled GIF: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save GIF: {e}")
            return False

class OpeningEffectProcessor:
    """Handles opening effects for videos"""
    
    def __init__(self, config: VideoConfig):
        self.config = config
    
    def create_opening_effect(self, input_video: str, output_video: str, 
                            effect_type: EffectType, duration: float) -> bool:
        """Apply opening effect to video"""
        if effect_type == EffectType.NONE:
            return self._copy_video(input_video, output_video)
        
        try:
            if effect_type in [EffectType.SLIDE_RIGHT_TO_LEFT, EffectType.SLIDE_LEFT_TO_RIGHT,
                              EffectType.SLIDE_TOP_TO_BOTTOM, EffectType.SLIDE_BOTTOM_TO_TOP]:
                return self._apply_slide_effect(input_video, output_video, effect_type, duration)
            elif effect_type in [EffectType.CIRCLE_EXPAND, EffectType.CIRCLE_CONTRACT]:
                return self._apply_circle_expand_contract_effect(input_video, output_video, effect_type, duration)
            elif effect_type in [EffectType.CIRCLE_ROTATE_CW, EffectType.CIRCLE_ROTATE_CCW]:
                return self._apply_circle_rotate_effect(input_video, output_video, effect_type, duration)
            elif effect_type == EffectType.FADE_IN:
                return self._apply_fade_effect(input_video, output_video, duration)
            else:
                logger.warning(f"Unknown effect type: {effect_type}")
                return self._copy_video(input_video, output_video)
                
        except Exception as e:
            logger.error(f"Error applying opening effect: {e}")
            return self._copy_video(input_video, output_video)
    
    def _copy_video(self, input_video: str, output_video: str) -> bool:
        """Simple video copy without effects"""
        cmd = [
            "ffmpeg", "-y", "-i", input_video,
            "-c", "copy", output_video
        ]
        return self._run_ffmpeg(cmd, silent=True)
    
    def _apply_slide_effect(self, input_video: str, output_video: str, 
                           effect_type: EffectType, duration: float) -> bool:
        """Apply slide effect (right-to-left, left-to-right, top-to-bottom, bottom-to-top)"""
        width, height = self.config.output_size
        
        if effect_type == EffectType.SLIDE_RIGHT_TO_LEFT:
            # Video slides from right to left over black background
            filter_expr = (
                f"color=black:{width}x{height}:d={duration}[bg];"
                f"[0:v]scale={width}:{height}[video];"
                f"[bg][video]overlay=x='if(lt(t,{duration}),{width}-(t/{duration})*{width},0)':y=0"
            )
        elif effect_type == EffectType.SLIDE_LEFT_TO_RIGHT:
            # Video slides from left to right over black background
            filter_expr = (
                f"color=black:{width}x{height}:d={duration}[bg];"
                f"[0:v]scale={width}:{height}[video];"
                f"[bg][video]overlay=x='if(lt(t,{duration}),-(t/{duration})*{width}+{width},0)':y=0"
            )
        elif effect_type == EffectType.SLIDE_TOP_TO_BOTTOM:
            # Video slides from top to bottom over black background
            filter_expr = (
                f"color=black:{width}x{height}:d={duration}[bg];"
                f"[0:v]scale={width}:{height}[video];"
                f"[bg][video]overlay=x=0:y='if(lt(t,{duration}),-(t/{duration})*{height}+{height},0)'"
            )
        elif effect_type == EffectType.SLIDE_BOTTOM_TO_TOP:
            # Video slides from bottom to top over black background
            filter_expr = (
                f"color=black:{width}x{height}:d={duration}[bg];"
                f"[0:v]scale={width}:{height}[video];"
                f"[bg][video]overlay=x=0:y='if(lt(t,{duration}),{height}-(t/{duration})*{height},0)'"
            )
        else:
            return False
        
        cmd = [
            "ffmpeg", "-y", "-i", input_video,
            "-filter_complex", filter_expr,
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "copy",
            output_video
        ]
        return self._run_ffmpeg(cmd)
    
    def _apply_circle_expand_contract_effect(self, input_video: str, output_video: str,
                                           effect_type: EffectType, duration: float) -> bool:
        """Apply circle expand or contract effect with proper circle reveal"""
        try:
            from circle_effects_processor import CircleEffectsProcessor
            
            width, height = self.config.output_size
            processor = CircleEffectsProcessor(width, height, duration, input_video)
            
            if effect_type == EffectType.CIRCLE_EXPAND:
                effect_type_str = "expand"
            else:  # CIRCLE_CONTRACT
                effect_type_str = "shrink"
            
            return processor.apply_circle_effect(input_video, output_video, effect_type_str)
            
        except ImportError:
            # Fallback to simple FFmpeg approach if processor not available
            logger.warning("Circle effects processor not available, using fallback")
            return self._apply_circle_fallback(input_video, output_video, effect_type, duration)
    
    def _apply_circle_rotate_effect(self, input_video: str, output_video: str,
                                  effect_type: EffectType, duration: float) -> bool:
        """Apply circle rotate effect with proper circle reveal"""
        try:
            from circle_effects_processor import CircleEffectsProcessor
            
            width, height = self.config.output_size
            processor = CircleEffectsProcessor(width, height, duration, input_video)
            
            if effect_type == EffectType.CIRCLE_ROTATE_CW:
                effect_type_str = "rotate_cw"
            else:  # CIRCLE_ROTATE_CCW
                effect_type_str = "rotate_ccw"
            
            return processor.apply_circle_effect(input_video, output_video, effect_type_str)
            
        except ImportError:
            # Fallback to simple FFmpeg approach if processor not available
            logger.warning("Circle effects processor not available, using fallback")
            return self._apply_circle_fallback(input_video, output_video, effect_type, duration)
    
    def _apply_circle_fallback(self, input_video: str, output_video: str,
                              effect_type: EffectType, duration: float) -> bool:
        """Fallback method for circle effects using simple FFmpeg filters"""
        width, height = self.config.output_size
        center_x, center_y = width // 2, height // 2
        
        if effect_type == EffectType.CIRCLE_EXPAND:
            # Simple expanding circle using crop
            filter_expr = (
                f"scale={width}:{height},"
                f"crop=w='if(lt(t,{duration}),(t/{duration})*{width},{width})':"
                f"h='if(lt(t,{duration}),(t/{duration})*{height},{height})':"
                f"x='if(lt(t,{duration}),{center_x}-(t/{duration})*{center_x},{center_x}-{center_x})':"
                f"y='if(lt(t,{duration}),{center_y}-(t/{duration})*{center_y},{center_y}-{center_y})',"
                f"pad=w={width}:h={height}:x=0:y=0:color=black"
            )
        elif effect_type == EffectType.CIRCLE_CONTRACT:
            # Simple contracting circle using crop
            filter_expr = (
                f"scale={width}:{height},"
                f"pad=w={width}:h={height}:x=0:y=0:color=black,"
                f"crop=w='if(lt(t,{duration}),{width}-(t/{duration})*{width},{width})':"
                f"h='if(lt(t,{duration}),{height}-(t/{duration})*{height},{height})':"
                f"x='if(lt(t,{duration}),(t/{duration})*{center_x},{center_x})':"
                f"y='if(lt(t,{duration}),(t/{duration})*{center_y},{center_y})'"
            )
        elif effect_type == EffectType.CIRCLE_ROTATE_CW:
            # Simple rotating circle using crop and rotate
            filter_expr = (
                f"scale={width}:{height},"
                f"crop=w='if(lt(t,{duration}),(t/{duration})*{width},{width})':"
                f"h='if(lt(t,{duration}),(t/{duration})*{height},{height})':"
                f"x='if(lt(t,{duration}),{center_x}-(t/{duration})*{center_x},{center_x}-{center_x})':"
                f"y='if(lt(t,{duration}),{center_y}-(t/{duration})*{center_y},{center_y}-{center_y})',"
                f"rotate='if(lt(t,{duration}),(t/{duration})*360,360)':bilinear=0,"
                f"pad=w={width}:h={height}:x=0:y=0:color=black"
            )
        else:  # CIRCLE_ROTATE_CCW
            # Simple rotating circle counter-clockwise
            filter_expr = (
                f"scale={width}:{height},"
                f"crop=w='if(lt(t,{duration}),(t/{duration})*{width},{width})':"
                f"h='if(lt(t,{duration}),(t/{duration})*{height},{height})':"
                f"x='if(lt(t,{duration}),{center_x}-(t/{duration})*{center_x},{center_x}-{center_x})':"
                f"y='if(lt(t,{duration}),{center_y}-(t/{duration})*{center_y},{center_y}-{center_y})',"
                f"rotate='if(lt(t,{duration}),-(t/{duration})*360,-360)':bilinear=0,"
                f"pad=w={width}:h={height}:x=0:y=0:color=black"
            )
        
        cmd = [
            "ffmpeg", "-y", "-i", input_video,
            "-vf", filter_expr,
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "copy",
            output_video
        ]
        return self._run_ffmpeg(cmd)
    
    def _apply_fade_effect(self, input_video: str, output_video: str, duration: float) -> bool:
        """Apply fade-in effect over black background"""
        width, height = self.config.output_size
        
        filter_expr = (
            f"color=black:{width}x{height}[bg];"
            f"[0:v]scale={width}:{height},fade=t=in:st=0:d={duration}[video];"
            f"[bg][video]overlay=shortest=1"
        )
        
        cmd = [
            "ffmpeg", "-y", "-i", input_video,
            "-filter_complex", filter_expr,
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "copy",
            output_video
        ]
        return self._run_ffmpeg(cmd)
    
    def _run_ffmpeg(self, cmd: List[str], silent: bool = False) -> bool:
        """Execute FFmpeg command with error handling"""
        try:
            if not silent:
                logger.info(f"Running opening effect: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd, 
                check=True, 
                stdout=subprocess.DEVNULL if silent else None,
                stderr=subprocess.PIPE if silent else None
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg command failed: {e}")
            if silent and e.stderr:
                logger.error(f"FFmpeg error: {e.stderr.decode()}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error running FFmpeg: {e}")
            return False

class VideoRenderer:
    """Handles video rendering operations"""
    
    def __init__(self, config: VideoConfig, processor: VideoProcessor):
        self.config = config
        self.processor = processor
        self.gif_processor = GIFProcessor(config)
        self.opening_effect_processor = OpeningEffectProcessor(config)
    
    def create_background_loop(self, bg_video: str, target_duration: float, 
                              temp_dir: str) -> Optional[str]:
        """Create background video loop"""
        bg_duration = self.processor.get_video_duration(bg_video)
        if not bg_duration:
            return None
        
        loop_count = int(target_duration // bg_duration) + 2
        loop_filter = f"loop=loop={loop_count}:size=1:start=0"
        temp_bg_loop = os.path.join(temp_dir, "bg_loop.mp4")
        
        cmd = [
            "ffmpeg", "-y", "-i", bg_video,
            "-filter:v", loop_filter,
            "-t", str(target_duration),
            "-c:v", "libx264", "-preset", "ultrafast",
            "-an", temp_bg_loop
        ]
        
        if self.processor.run_ffmpeg(cmd, silent=True):
            return temp_bg_loop
        return None
    
    def create_gif_loop(self, gif_path: str, target_duration: float, 
                       temp_dir: str) -> Optional[str]:
        """Create GIF loop as PNG sequence"""
        png_pattern = os.path.join(temp_dir, "gif_frames_%04d.png")
        
        cmd = [
            "ffmpeg", "-y", "-stream_loop", "-1", "-i", gif_path,
            "-t", str(target_duration),
            "-vf", f"fps={self.config.FRAME_RATE}",
            png_pattern
        ]
        
        if self.processor.run_ffmpeg(cmd, silent=True):
            return png_pattern
        return None
    
    def speed_up_video(self, input_video: str, output_video: str, 
                      speed_multiplier: float) -> bool:
        """Speed up video with audio"""
        cmd = [
            "ffmpeg", "-y", "-i", input_video,
            "-filter_complex", f"[0:v]setpts=PTS/{speed_multiplier}[v];[0:a]atempo={speed_multiplier}[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac", "-threads", "0",
            output_video
        ]
        return self.processor.run_ffmpeg(cmd, silent=True)
    
    def render_with_effects(self, main_video: str, bg_video: str, 
                           gif_pattern: str, output_file: str) -> bool:
        """Render video with GIF effects overlay"""
        # First render the basic video with effects
        temp_output = output_file.replace('.mp4', '_temp.mp4')
        
        cmd = [
            "ffmpeg", "-y",
            "-i", main_video,
            "-i", bg_video,
            "-framerate", str(self.config.FRAME_RATE), "-i", gif_pattern,
            "-filter_complex",
            f"[0:v]scale={self.config.HALF_WIDTH}:{self.config.OUTPUT_HEIGHT}[left]; "
            f"[1:v]scale={self.config.HALF_WIDTH}:{self.config.OUTPUT_HEIGHT}[right]; "
            "[left][right]hstack=inputs=2[stacked]; "
            "[stacked][2:v]overlay=0:0[v]",
            "-map", "[v]", "-map", "0:a",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", str(self.config.CRF_VALUE),
            "-c:a", "aac",
            "-shortest",
            "-threads", "0",
            temp_output
        ]
        
        if not self.processor.run_ffmpeg(cmd):
            return False
        
        # Apply opening effect to the merged video
        if self.config.OPENING_EFFECT != EffectType.NONE:
            success = self.opening_effect_processor.create_opening_effect(
                temp_output, output_file, 
                self.config.OPENING_EFFECT, 
                self.config.OPENING_DURATION
            )
            # Clean up temp file
            try:
                os.remove(temp_output)
            except:
                pass
            return success
        else:
            # No opening effect, just rename temp file
            try:
                os.rename(temp_output, output_file)
                return True
            except:
                return False
    
    def render_without_effects(self, main_video: str, bg_video: str, 
                              output_file: str) -> bool:
        """Render video without effects"""
        # First render the basic video
        temp_output = output_file.replace('.mp4', '_temp.mp4')
        
        cmd = [
            "ffmpeg", "-y",
            "-i", main_video,
            "-i", bg_video,
            "-filter_complex",
            f"[0:v]scale={self.config.HALF_WIDTH}:{self.config.OUTPUT_HEIGHT}[left]; "
            f"[1:v]scale={self.config.HALF_WIDTH}:{self.config.OUTPUT_HEIGHT}[right]; "
            "[left][right]hstack=inputs=2[v]",
            "-map", "[v]", "-map", "0:a",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", str(self.config.CRF_VALUE),
            "-c:a", "aac",
            "-shortest",
            "-threads", "0",
            temp_output
        ]
        
        if not self.processor.run_ffmpeg(cmd):
            return False
        
        # Apply opening effect to the merged video
        if self.config.OPENING_EFFECT != EffectType.NONE:
            success = self.opening_effect_processor.create_opening_effect(
                temp_output, output_file, 
                self.config.OPENING_EFFECT, 
                self.config.OPENING_DURATION
            )
            # Clean up temp file
            try:
                os.remove(temp_output)
            except:
                pass
            return success
        else:
            # No opening effect, just rename temp file
            try:
                os.rename(temp_output, output_file)
                return True
            except:
                return False

class VideoMerger:
    """Main class for video merging operations"""
    
    def __init__(self, config: VideoConfig = None):
        self.config = config or VideoConfig()
        self.processor = VideoProcessor(self.config)
        self.renderer = VideoRenderer(self.config, self.processor)
        self.gif_processor = GIFProcessor(self.config)  # Add GIF processor
    
    def get_or_create_tiled_gif(self, video_path: str, 
                               original_gif_path: str = "effects/star.gif") -> Optional[str]:
        """Get existing tiled GIF or create new one"""
        try:
            # Create generated effects directory if it doesn't exist
            os.makedirs(self.config.GENERATED_EFFECTS_DIR, exist_ok=True)
            
            # Use generated effects directory for new GIFs
            output_gif_path = f"{self.config.GENERATED_EFFECTS_DIR}/star_tiled_{self.config.OUTPUT_WIDTH}x{self.config.OUTPUT_HEIGHT}.gif"
            
            if self.gif_processor.create_tiled_gif(original_gif_path, output_gif_path, 
                                                 self.config.output_size):
                return output_gif_path
            return None
        except Exception as e:
            logger.error(f"Error in get_or_create_tiled_gif: {e}")
            return None
    
    def render_single_video(self, main_video: str, bg_video: str, 
                           index: int, add_effects: bool = True) -> bool:
        """Render a single video with background and optional effects"""
        video_name = Path(main_video).stem
        output_file = f"{self.config.OUTPUT_DIR}/{video_name}.mp4"
        
        # Debug: Log the current config
        logger.info(f"Current opening effect: {self.config.OPENING_EFFECT.value}")
        logger.info(f"Current opening duration: {self.config.OPENING_DURATION}")
        
        if os.path.exists(output_file):
            logger.info(f"Skipping existing file: {output_file}")
            return True
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_main = os.path.join(temp_dir, "main_speed.mp4")
                
                # Speed up main video
                if not self.renderer.speed_up_video(main_video, temp_main, 
                                                  self.config.SPEED_MULTIPLIER):
                    return False
                
                main_duration = self.processor.get_video_duration(temp_main)
                if not main_duration:
                    return False
                
                # Create background loop
                temp_bg_loop = self.renderer.create_background_loop(bg_video, main_duration, temp_dir)
                if not temp_bg_loop:
                    return False
                
                # Render with or without effects
                if add_effects and os.path.exists(f"{self.config.EFFECTS_DIR}/star.gif"):
                    tiled_gif_path = self.get_or_create_tiled_gif(main_video)
                    
                    if tiled_gif_path and os.path.exists(tiled_gif_path):
                        logger.info(f"Using tiled GIF: {Path(tiled_gif_path).name}")
                        png_pattern = self.renderer.create_gif_loop(tiled_gif_path, main_duration, temp_dir)
                        
                        if png_pattern:
                            success = self.renderer.render_with_effects(temp_main, temp_bg_loop, 
                                                                      png_pattern, output_file)
                        else:
                            success = self.renderer.render_without_effects(temp_main, temp_bg_loop, output_file)
                    else:
                        logger.warning("Could not create tiled GIF, rendering without effects")
                        success = self.renderer.render_without_effects(temp_main, temp_bg_loop, output_file)
                else:
                    success = self.renderer.render_without_effects(temp_main, temp_bg_loop, output_file)
                
                if success:
                    logger.info(f"Successfully rendered: {output_file}")
                    return True
                else:
                    logger.error(f"Failed to render: {output_file}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error rendering {main_video}: {e}")
            return False
    
    def preprocess_backgrounds(self, background_videos: List[str]):
        """Preprocess background videos to cache metadata"""
        logger.info("Caching background video information...")
        for bg_video in background_videos:
            self.processor.get_video_duration(bg_video)
        logger.info(f"Cached {len(background_videos)} background videos")
    
    def get_video_files(self) -> Tuple[List[str], List[str]]:
        """Get input and background video files"""
        input_pattern = f"{self.config.INPUT_DIR}/{self.config.INPUT_PATTERN}"
        bg_pattern = f"{self.config.BACKGROUND_DIR}/{self.config.BACKGROUND_PATTERN}"
        
        download_videos = sorted(glob(input_pattern))
        background_videos = sorted(glob(bg_pattern))
        
        return download_videos, background_videos
    
    def render_all_videos(self, add_effects: bool = True) -> bool:
        """Render all videos with parallel processing"""
        os.makedirs(self.config.OUTPUT_DIR, exist_ok=True)
        
        download_videos, background_videos = self.get_video_files()
        
        if not download_videos or not background_videos:
            logger.error(f"Missing videos in {self.config.INPUT_DIR}/ or {self.config.BACKGROUND_DIR}/")
            return False
        
        # Preprocess backgrounds
        self.preprocess_backgrounds(background_videos)
        
        # For now, process sequentially to ensure config is properly passed
        # TODO: Fix parallel processing config passing
        logger.info("Processing videos sequentially to ensure proper config")
        
        success_count = 0
        total_count = len(download_videos)
        
        for idx, main_video in enumerate(download_videos):
            bg_video = random.choice(background_videos)
            logger.info(f"Processing: {Path(main_video).name} + {Path(bg_video).name}")
            
            if self.render_single_video(main_video, bg_video, idx, add_effects):
                success_count += 1
        
        logger.info(f"Completed: {success_count}/{total_count} videos processed successfully")
        return success_count == total_count
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        temp_patterns = ["temp_main_*.mp4", "temp_bg_loop_*.mp4", "temp_bg_cut_*.mp4"]
        for pattern in temp_patterns:
            for temp_file in glob(pattern):
                try:
                    os.remove(temp_file)
                    logger.info(f"Cleaned up: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to clean up {temp_file}: {e}")

def main():
    """Main entry point"""
    try:
        # Show available effects
        print("\n=== TIKTOK VIDEO PROCESSING TOOL ===")
        print("Available opening effects:")
        print("0. None (no effect)")
        print("1. Slide from right to left")
        print("2. Slide from left to right") 
        print("3. Slide from top to bottom")
        print("4. Slide from bottom to top")
        print("5. Circle expand from center")
        print("6. Circle contract to center")
        print("7. Circle rotate clockwise")
        print("8. Circle rotate counter-clockwise")
        print("9. Fade in")
        
        # Get user choice
        while True:
            try:
                choice = input("\nSelect opening effect (0-9): ").strip()
                # Clean up any special characters
                choice = choice.replace('\r', '').replace('\n', '').strip()
                choice = int(choice)
                if 0 <= choice <= 9:
                    break
                else:
                    print("Please enter a number between 0 and 9")
            except ValueError:
                print("Please enter a valid number")
        
        # Get effect duration
        while True:
            try:
                duration = input("Enter effect duration in seconds (default 2.0): ").strip()
                # Clean up any special characters
                duration = duration.replace('\r', '').replace('\n', '').strip()
                if not duration:
                    duration = 2.0
                else:
                    duration = float(duration)
                if duration > 0:
                    break
                else:
                    print("Duration must be positive")
            except ValueError:
                print("Please enter a valid number")
        
        # Map choice to effect type
        effect_map = {
            0: EffectType.NONE,
            1: EffectType.SLIDE_RIGHT_TO_LEFT,
            2: EffectType.SLIDE_LEFT_TO_RIGHT,
            3: EffectType.SLIDE_TOP_TO_BOTTOM,
            4: EffectType.SLIDE_BOTTOM_TO_TOP,
            5: EffectType.CIRCLE_EXPAND,
            6: EffectType.CIRCLE_CONTRACT,
            7: EffectType.CIRCLE_ROTATE_CW,
            8: EffectType.CIRCLE_ROTATE_CCW,
            9: EffectType.FADE_IN
        }
        
        # Create config with selected effect
        config = VideoConfig()
        config.OPENING_EFFECT = effect_map[choice]
        config.OPENING_DURATION = duration
        
        print(f"\nSelected effect: {config.OPENING_EFFECT.value}")
        print(f"Effect duration: {config.OPENING_DURATION} seconds")
        
        # Ask about GIF effects
        add_gif_effects = input("Add GIF overlay effects? (y/n, default y): ").strip()
        # Clean up any special characters
        add_gif_effects = add_gif_effects.replace('\r', '').replace('\n', '').strip().lower()
        add_gif_effects = add_gif_effects != 'n'
        
        merger = VideoMerger(config)
        merger.cleanup_temp_files()
        success = merger.render_all_videos(add_effects=add_gif_effects)
        
        if success:
            logger.info("All videos processed successfully!")
        else:
            logger.error("Some videos failed to process")
            return 1
        
        return 0
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 