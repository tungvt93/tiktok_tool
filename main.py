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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    
    # Paths
    INPUT_DIR: str = "dongphuc"
    BACKGROUND_DIR: str = "video_chia_2"
    OUTPUT_DIR: str = "output"
    EFFECTS_DIR: str = "effects"
    
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

class VideoRenderer:
    """Handles video rendering operations"""
    
    def __init__(self, config: VideoConfig, processor: VideoProcessor):
        self.config = config
        self.processor = processor
        self.gif_processor = GIFProcessor(config)
    
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
            output_file
        ]
        return self.processor.run_ffmpeg(cmd)
    
    def render_without_effects(self, main_video: str, bg_video: str, 
                              output_file: str) -> bool:
        """Render video without effects"""
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
            output_file
        ]
        return self.processor.run_ffmpeg(cmd)

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
            output_gif_path = f"{self.config.EFFECTS_DIR}/star_tiled_{self.config.OUTPUT_WIDTH}x{self.config.OUTPUT_HEIGHT}.gif"
            
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
        
        # Determine optimal worker count
        max_workers = min(os.cpu_count() or 1, len(download_videos))
        logger.info(f"Using {max_workers} processes for rendering")
        
        # Process videos in parallel
        success_count = 0
        total_count = len(download_videos)
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for idx, main_video in enumerate(download_videos):
                bg_video = random.choice(background_videos)
                logger.info(f"Queue: {Path(main_video).name} + {Path(bg_video).name}")
                
                future = executor.submit(self.render_single_video, main_video, bg_video, idx, add_effects)
                futures.append(future)
            
            # Wait for completion
            for future in as_completed(futures):
                try:
                    if future.result():
                        success_count += 1
                except Exception as e:
                    logger.error(f"Processing error: {e}")
        
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
        merger = VideoMerger()
        merger.cleanup_temp_files()
        success = merger.render_all_videos(add_effects=True)
        
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