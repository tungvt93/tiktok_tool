#!/usr/bin/env python3
"""
Circle Effects Processor using numpy masks
Based on the reference code provided by user
"""

import cv2
import numpy as np
import subprocess
import tempfile
import os
from typing import Tuple, Callable

class CircleEffectsProcessor:
    """Process circle effects using numpy masks"""
    
    def __init__(self, width: int, height: int, duration: float, input_video: str = None):
        self.width = width
        self.height = height
        self.duration = duration
        self.input_video = input_video
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
        
        # ✅ FIXED: Mask = 1 outside circle (black background), 0 inside circle (video visible)
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
    
    def create_mask_video(self, mask_func: Callable, output_path: str, fps: int = 30) -> bool:
        """Create a video from mask function"""
        try:
            # Get input video duration
            result = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries", "format=duration", 
                "-of", "default=noprint_wrappers=1:nokey=1", self.input_video
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
                
                # Convert to 8-bit grayscale
                mask_8bit = (mask * 255).astype(np.uint8)
                
                # Create 3-channel video
                frame = cv2.cvtColor(mask_8bit, cv2.COLOR_GRAY2BGR)
                out.write(frame)
            
            out.release()
            return True
        except Exception as e:
            print(f"Error creating mask video: {e}")
            return False
    
    def apply_circle_effect(self, input_video: str, output_video: str, 
                          effect_type: str) -> bool:
        """Apply circle effect to video"""
        try:
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                mask_video = os.path.join(temp_dir, "mask.mp4")
                
                # Update input video for mask creation
                self.input_video = input_video
                
                # Create mask based on effect type
                if effect_type == "expand":
                    success = self.create_mask_video(self.circle_expand_mask, mask_video)
                elif effect_type == "shrink":
                    success = self.create_mask_video(self.circle_shrink_mask, mask_video)
                elif effect_type == "rotate_cw":
                    success = self.create_mask_video(
                        lambda t: self.circle_rotate_mask(t, clockwise=True), 
                        mask_video
                    )
                elif effect_type == "rotate_ccw":
                    success = self.create_mask_video(
                        lambda t: self.circle_rotate_mask(t, clockwise=False), 
                        mask_video
                    )
                else:
                    print(f"Unknown effect type: {effect_type}")
                    return False
                
                if not success:
                    return False
                
                # Apply mask to video using FFmpeg
                if effect_type == "shrink":
                    # ✅ FIXED: For shrink: black background with video overlaid using inverted mask
                    cmd = [
                        "ffmpeg", "-y",
                        "-i", input_video,
                        "-i", mask_video,
                        "-filter_complex",
                        f"color=black:{self.width}x{self.height}[bg];"
                        f"[0:v]scale={self.width}:{self.height}[video];"
                        f"[1:v]scale={self.width}:{self.height}[mask];"
                        f"[video][mask]alphamerge[alpha];"
                        f"[bg][alpha]overlay=shortest=1",
                        "-c:v", "libx264", "-preset", "ultrafast",
                        "-c:a", "copy",
                        output_video
                    ]
                else:
                    # For expand/rotate: black background with masked video
                    cmd = [
                        "ffmpeg", "-y",
                        "-i", input_video,
                        "-i", mask_video,
                        "-filter_complex",
                        f"color=black:{self.width}x{self.height}[bg];"
                        f"[0:v]scale={self.width}:{self.height}[video];"
                        f"[1:v]scale={self.width}:{self.height}[mask];"
                        f"[video][mask]alphamerge[alpha];"
                        f"[bg][alpha]overlay=shortest=1",
                        "-c:v", "libx264", "-preset", "ultrafast",
                        "-c:a", "copy",
                        output_video
                    ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.returncode == 0
                
        except Exception as e:
            print(f"Error applying circle effect: {e}")
            return False

def test_circle_effects():
    """Test circle effects"""
    # Test parameters
    width, height = 1080, 1080
    duration = 2.0
    
    processor = CircleEffectsProcessor(width, height, duration)
    
    # Test with a sample video
    input_video = "dongphuc/1.mp4"
    if not os.path.exists(input_video):
        print(f"Test video not found: {input_video}")
        return
    
    effects = ["expand", "shrink", "rotate_cw", "rotate_ccw"]
    
    for effect in effects:
        output_video = f"test_circle_{effect}.mp4"
        print(f"Testing {effect} effect...")
        
        success = processor.apply_circle_effect(input_video, output_video, effect)
        if success:
            print(f"✅ {effect} effect created: {output_video}")
        else:
            print(f"❌ {effect} effect failed")

if __name__ == "__main__":
    test_circle_effects() 