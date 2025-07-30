"""
Preview System for TikTok Video Processing Tool
Shows video previews with effects without actually merging videos
"""

import cv2
import numpy as np
import os
import glob
from pathlib import Path
from typing import Tuple, Optional, List
import threading
import time
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk
from main import EffectType, VideoConfig

class VideoPreview:
    """Video preview with effects simulation"""
    
    def __init__(self, config: VideoConfig):
        self.config = config
        self.preview_duration = 3.0  # Preview duration in seconds
        self.preview_fps = 10  # Preview frame rate
    
    def create_preview_window(self, video_path: str, bg_video_path: str, 
                            opening_effect: EffectType, gif_path: Optional[str] = None):
        """Create a preview window showing the final result"""
        # Create preview window
        preview_window = tk.Toplevel()
        preview_window.title("Video Preview")
        preview_window.geometry("800x600")
        preview_window.configure(bg='#2b2b2b')
        
        # Video display
        video_frame = tk.Frame(preview_window, bg='#2b2b2b')
        video_frame.pack(expand=True, fill='both', padx=10, pady=10)
        
        video_label = tk.Label(video_frame, bg='black')
        video_label.pack(expand=True, fill='both')
        
        # Control frame
        control_frame = tk.Frame(preview_window, bg='#2b2b2b')
        control_frame.pack(fill='x', padx=10, pady=(0, 10))
        
        # Progress bar
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(control_frame, variable=progress_var, 
                                     maximum=100, length=400)
        progress_bar.pack(side='left', padx=(0, 10))
        
        # Time label
        time_label = tk.Label(control_frame, text="0.0s / 3.0s", 
                            bg='#2b2b2b', fg='white')
        time_label.pack(side='left', padx=(0, 10))
        
        # Play/Pause button
        play_var = tk.BooleanVar(value=True)
        play_btn = tk.Button(control_frame, text="⏸️", 
                           command=lambda: play_var.set(not play_var.get()))
        play_btn.pack(side='left', padx=(0, 10))
        
        # Close button
        close_btn = tk.Button(control_frame, text="Close", 
                            command=preview_window.destroy)
        close_btn.pack(side='right')
        
        # Start preview thread
        preview_thread = threading.Thread(
            target=self._run_preview,
            args=(video_path, bg_video_path, opening_effect, gif_path,
                  video_label, progress_var, time_label, play_var, preview_window)
        )
        preview_thread.daemon = True
        preview_thread.start()
        
        return preview_window
    
    def _run_preview(self, video_path: str, bg_video_path: str, 
                    opening_effect: EffectType, gif_path: Optional[str],
                    video_label: tk.Label, progress_var: tk.DoubleVar,
                    time_label: tk.Label, play_var: tk.BooleanVar,
                    preview_window: tk.Toplevel):
        """Run the preview in a separate thread"""
        try:
            # Open video captures
            main_cap = cv2.VideoCapture(video_path)
            bg_cap = cv2.VideoCapture(bg_video_path)
            
            if not main_cap.isOpened() or not bg_cap.isOpened():
                raise Exception("Could not open video files")
            
            # Get video properties
            main_fps = main_cap.get(cv2.CAP_PROP_FPS)
            bg_fps = bg_cap.get(cv2.CAP_PROP_FPS)
            
            # Calculate frame intervals
            frame_interval = 1.0 / self.preview_fps
            total_frames = int(self.preview_duration * self.preview_fps)
            
            # Load GIF if provided
            gif_frames = None
            if gif_path and os.path.exists(gif_path):
                gif_frames = self._load_gif_frames(gif_path)
            
            start_time = time.time()
            frame_count = 0
            
            while frame_count < total_frames:
                if not play_var.get():
                    time.sleep(0.1)
                    continue
                
                current_time = time.time() - start_time
                progress = (frame_count / total_frames) * 100
                
                # Update progress
                preview_window.after(0, lambda p=progress: progress_var.set(p))
                preview_window.after(0, lambda t=current_time: 
                                   time_label.config(text=f"{t:.1f}s / {self.preview_duration:.1f}s"))
                
                # Read frames
                main_ret, main_frame = main_cap.read()
                bg_ret, bg_frame = bg_cap.read()
                
                if not main_ret or not bg_ret:
                    # Loop videos
                    main_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    bg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    main_ret, main_frame = main_cap.read()
                    bg_ret, bg_frame = bg_cap.read()
                
                # Create preview frame
                preview_frame = self._create_preview_frame(
                    main_frame, bg_frame, opening_effect, gif_frames, 
                    current_time, frame_count
                )
                
                # Convert to PhotoImage and display
                preview_image = self._cv2_to_photoimage(preview_frame)
                preview_window.after(0, lambda img=preview_image: 
                                   video_label.config(image=img))
                preview_window.after(0, lambda: video_label.image(img))
                
                frame_count += 1
                time.sleep(frame_interval)
            
            # Cleanup
            main_cap.release()
            bg_cap.release()
            
        except Exception as e:
            print(f"Preview error: {e}")
            preview_window.after(0, lambda: video_label.config(
                text=f"Preview Error: {str(e)}", fg='red'))
    
    def _create_preview_frame(self, main_frame: np.ndarray, bg_frame: np.ndarray,
                            opening_effect: EffectType, gif_frames: Optional[List[np.ndarray]],
                            current_time: float, frame_count: int) -> np.ndarray:
        """Create a preview frame with effects"""
        # Resize frames to target size
        target_size = (self.config.OUTPUT_WIDTH, self.config.OUTPUT_HEIGHT)
        half_width = self.config.HALF_WIDTH
        
        # Resize main video to left half
        main_resized = cv2.resize(main_frame, (half_width, target_size[1]))
        
        # Resize background video to right half
        bg_resized = cv2.resize(bg_frame, (half_width, target_size[1]))
        
        # Combine videos side by side
        combined = np.hstack([main_resized, bg_resized])
        
        # Apply opening effect
        if opening_effect != EffectType.NONE:
            combined = self._apply_opening_effect_preview(
                combined, opening_effect, current_time
            )
        
        # Apply GIF overlay if available
        if gif_frames:
            combined = self._apply_gif_overlay_preview(combined, gif_frames, frame_count)
        
        return combined
    
    def _apply_opening_effect_preview(self, frame: np.ndarray, 
                                    effect: EffectType, current_time: float) -> np.ndarray:
        """Apply opening effect preview"""
        height, width = frame.shape[:2]
        effect_duration = self.config.OPENING_DURATION
        
        if current_time > effect_duration:
            return frame
        
        # Create black background
        result = np.zeros_like(frame)
        
        # Calculate effect progress
        progress = current_time / effect_duration
        
        if effect == EffectType.SLIDE_RIGHT_TO_LEFT:
            # Slide from right to left
            start_x = int(width * (1 - progress))
            end_x = width
            result[:, start_x:end_x] = frame[:, start_x:end_x]
            
        elif effect == EffectType.SLIDE_LEFT_TO_RIGHT:
            # Slide from left to right
            end_x = int(width * progress)
            result[:, 0:end_x] = frame[:, 0:end_x]
            
        elif effect == EffectType.SLIDE_TOP_TO_BOTTOM:
            # Slide from top to bottom
            end_y = int(height * progress)
            result[0:end_y, :] = frame[0:end_y, :]
            
        elif effect == EffectType.SLIDE_BOTTOM_TO_TOP:
            # Slide from bottom to top
            start_y = int(height * (1 - progress))
            end_y = height
            result[start_y:end_y, :] = frame[start_y:end_y, :]
            
        elif effect == EffectType.CIRCLE_EXPAND:
            # Circle expand from center
            center_x, center_y = width // 2, height // 2
            max_radius = int(np.sqrt(center_x**2 + center_y**2))
            current_radius = int(max_radius * progress)
            
            # Create circular mask
            y, x = np.ogrid[:height, :width]
            mask = (x - center_x)**2 + (y - center_y)**2 <= current_radius**2
            result[mask] = frame[mask]
            
        elif effect == EffectType.CIRCLE_CONTRACT:
            # Circle contract to center
            center_x, center_y = width // 2, height // 2
            max_radius = int(np.sqrt(center_x**2 + center_y**2))
            current_radius = int(max_radius * (1 - progress))
            
            # Create circular mask
            y, x = np.ogrid[:height, :width]
            mask = (x - center_x)**2 + (y - center_y)**2 <= current_radius**2
            result[mask] = frame[mask]
            
        elif effect == EffectType.FADE_IN:
            # Fade in
            alpha = progress
            result = cv2.addWeighted(np.zeros_like(frame), 1 - alpha, frame, alpha, 0)
        
        else:
            # Default: no effect
            result = frame
        
        return result
    
    def _apply_gif_overlay_preview(self, frame: np.ndarray, 
                                 gif_frames: List[np.ndarray], 
                                 frame_count: int) -> np.ndarray:
        """Apply GIF overlay preview"""
        if not gif_frames:
            return frame
        
        # Get current GIF frame
        gif_frame_index = frame_count % len(gif_frames)
        gif_frame = gif_frames[gif_frame_index]
        
        # Resize GIF frame to match target size
        gif_resized = cv2.resize(gif_frame, (frame.shape[1], frame.shape[0]))
        
        # Apply alpha blending if GIF has alpha channel
        if gif_resized.shape[2] == 4:  # RGBA
            alpha = gif_resized[:, :, 3] / 255.0
            alpha = np.expand_dims(alpha, axis=2)
            
            # Blend with background
            result = frame * (1 - alpha) + gif_resized[:, :, :3] * alpha
            return result.astype(np.uint8)
        else:
            # No alpha channel, overlay directly
            return cv2.addWeighted(frame, 0.7, gif_resized, 0.3, 0)
    
    def _load_gif_frames(self, gif_path: str) -> List[np.ndarray]:
        """Load GIF frames as numpy arrays"""
        try:
            gif = Image.open(gif_path)
            frames = []
            
            for frame_idx in range(gif.n_frames):
                gif.seek(frame_idx)
                frame = gif.convert('RGBA')
                frame_array = np.array(frame)
                frames.append(frame_array)
            
            return frames
        except Exception as e:
            print(f"Error loading GIF: {e}")
            return []
    
    def _cv2_to_photoimage(self, cv2_image: np.ndarray) -> tk.PhotoImage:
        """Convert OpenCV image to Tkinter PhotoImage"""
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
        
        # Resize for display
        display_size = (600, 600)
        resized = cv2.resize(rgb_image, display_size)
        
        # Convert to PIL Image
        pil_image = Image.fromarray(resized)
        
        # Convert to PhotoImage
        photo_image = ImageTk.PhotoImage(pil_image)
        
        return photo_image

class PreviewManager:
    """Manager for video previews"""
    
    def __init__(self, config: VideoConfig):
        self.config = config
        self.preview = VideoPreview(config)
    
    def show_preview(self, video_path: str, opening_effect: EffectType, 
                    gif_path: Optional[str] = None):
        """Show preview for a video with effects"""
        # Get random background video
        background_videos = glob.glob(f"{self.config.BACKGROUND_DIR}/*.mp4")
        if not background_videos:
            raise Exception("No background videos found")
        
        import random
        bg_video = random.choice(background_videos)
        
        # Create preview window
        preview_window = self.preview.create_preview_window(
            video_path, bg_video, opening_effect, gif_path
        )
        
        return preview_window

def create_preview_dialog(video_path: str, opening_effect: EffectType, 
                         gif_path: Optional[str] = None):
    """Create a simple preview dialog"""
    config = VideoConfig()
    manager = PreviewManager(config)
    
    try:
        preview_window = manager.show_preview(video_path, opening_effect, gif_path)
        return preview_window
    except Exception as e:
        print(f"Preview error: {e}")
        return None 