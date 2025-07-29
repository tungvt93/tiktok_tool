"""
Preview System for TikTok Video Processing Tool using PyQt5
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

try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                QHBoxLayout, QLabel, QPushButton, QProgressBar,
                                QSlider, QFrame)
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QMutex
    from PyQt5.QtGui import QPixmap, QImage, QFont
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

from PIL import Image
from main import EffectType, VideoConfig

class PreviewWorker(QThread):
    """Worker thread for video preview"""
    frame_ready = pyqtSignal(QImage)
    progress_updated = pyqtSignal(int)
    time_updated = pyqtSignal(str)
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, video_path: str, bg_video_path: str, 
                 opening_effect: EffectType, gif_path: Optional[str],
                 config: VideoConfig):
        super().__init__()
        self.video_path = video_path
        self.opening_effect = opening_effect
        self.gif_path = gif_path
        self.config = config
        self.is_running = True
        self.is_paused = False
        self.mutex = QMutex()
    
    def run(self):
        try:
            # Open main video only (no background needed for preview)
            main_cap = cv2.VideoCapture(self.video_path)
            
            if not main_cap.isOpened():
                self.error_occurred.emit("Could not open video file")
                return
            
            # Load GIF if provided
            gif_frames = None
            if self.gif_path and os.path.exists(self.gif_path):
                gif_frames = self._load_gif_frames(self.gif_path)
            
            # Faster preview - shorter duration and higher FPS
            preview_duration = 2.0  # 2 seconds instead of 3
            preview_fps = 15  # Higher FPS for smoother preview
            frame_interval = 1.0 / preview_fps
            total_frames = int(preview_duration * preview_fps)
            
            start_time = time.time()
            frame_count = 0
            
            while frame_count < total_frames and self.is_running:
                self.mutex.lock()
                if self.is_paused:
                    self.mutex.unlock()
                    time.sleep(0.1)
                    continue
                self.mutex.unlock()
                
                current_time = time.time() - start_time
                progress = int((frame_count / total_frames) * 100)
                
                # Update progress and time
                self.progress_updated.emit(progress)
                self.time_updated.emit(f"{current_time:.1f}s / {preview_duration:.1f}s")
                
                # Read frame from main video only
                ret, main_frame = main_cap.read()
                
                if not ret:
                    # Loop video
                    main_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, main_frame = main_cap.read()
                
                # Create simple preview frame (no background merging)
                preview_frame = self._create_simple_preview_frame(
                    main_frame, gif_frames, current_time, frame_count
                )
                
                # Convert to QImage and emit
                qimage = self._cv2_to_qimage(preview_frame)
                self.frame_ready.emit(qimage)
                
                frame_count += 1
                time.sleep(frame_interval)
            
            # Cleanup
            main_cap.release()
            
            self.finished.emit()
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def pause(self):
        """Pause preview"""
        self.mutex.lock()
        self.is_paused = True
        self.mutex.unlock()
    
    def resume(self):
        """Resume preview"""
        self.mutex.lock()
        self.is_paused = False
        self.mutex.unlock()
    
    def stop(self):
        """Stop preview"""
        self.is_running = False
    
    def _create_simple_preview_frame(self, main_frame: np.ndarray,
                                   gif_frames: Optional[List[np.ndarray]],
                                   current_time: float, frame_count: int) -> np.ndarray:
        """Create a simple preview frame with effects (no background merging)"""
        # Resize main video to target size
        target_size = (self.config.OUTPUT_WIDTH, self.config.OUTPUT_HEIGHT)
        main_resized = cv2.resize(main_frame, target_size)
        
        # Apply opening effect
        if self.opening_effect != EffectType.NONE:
            main_resized = self._apply_opening_effect_preview(main_resized, current_time)
        
        # Apply GIF overlay
        if gif_frames:
            main_resized = self._apply_gif_overlay_preview(main_resized, gif_frames, frame_count)
        
        return main_resized
    
    def _apply_opening_effect_preview(self, frame: np.ndarray, current_time: float) -> np.ndarray:
        """Apply opening effect preview"""
        height, width = frame.shape[:2]
        effect_duration = self.config.OPENING_DURATION
        
        if current_time > effect_duration:
            return frame
        
        # Create black background
        result = np.zeros_like(frame)
        
        # Calculate effect progress
        progress = current_time / effect_duration
        
        if self.opening_effect == EffectType.SLIDE_RIGHT_TO_LEFT:
            # Slide from right to left
            start_x = int(width * (1 - progress))
            end_x = width
            result[:, start_x:end_x] = frame[:, start_x:end_x]
            
        elif self.opening_effect == EffectType.SLIDE_LEFT_TO_RIGHT:
            # Slide from left to right
            end_x = int(width * progress)
            result[:, 0:end_x] = frame[:, 0:end_x]
            
        elif self.opening_effect == EffectType.SLIDE_TOP_TO_BOTTOM:
            # Slide from top to bottom
            end_y = int(height * progress)
            result[0:end_y, :] = frame[0:end_y, :]
            
        elif self.opening_effect == EffectType.SLIDE_BOTTOM_TO_TOP:
            # Slide from bottom to top
            start_y = int(height * (1 - progress))
            end_y = height
            result[start_y:end_y, :] = frame[start_y:end_y, :]
            
        elif self.opening_effect == EffectType.CIRCLE_EXPAND:
            # Circle expand from center
            center_x, center_y = width // 2, height // 2
            max_radius = int(np.sqrt(center_x**2 + center_y**2))
            current_radius = int(max_radius * progress)
            
            # Create circular mask
            y, x = np.ogrid[:height, :width]
            mask = (x - center_x)**2 + (y - center_y)**2 <= current_radius**2
            result[mask] = frame[mask]
            
        elif self.opening_effect == EffectType.CIRCLE_CONTRACT:
            # Circle contract to center
            center_x, center_y = width // 2, height // 2
            max_radius = int(np.sqrt(center_x**2 + center_y**2))
            current_radius = int(max_radius * (1 - progress))
            
            # Create circular mask
            y, x = np.ogrid[:height, :width]
            mask = (x - center_x)**2 + (y - center_y)**2 <= current_radius**2
            result[mask] = frame[mask]
            
        elif self.opening_effect == EffectType.FADE_IN:
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
    
    def _cv2_to_qimage(self, cv2_image: np.ndarray) -> QImage:
        """Convert OpenCV image to QImage"""
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
        
        # Resize for display
        display_size = (600, 600)
        resized = cv2.resize(rgb_image, display_size)
        
        # Convert to QImage
        height, width, channel = resized.shape
        bytes_per_line = 3 * width
        qimage = QImage(resized.data, width, height, bytes_per_line, QImage.Format_RGB888)
        
        return qimage

class PreviewWindow(QMainWindow):
    """Preview window for video effects"""
    
    def __init__(self, video_path: str, opening_effect: EffectType, 
                 gif_path: Optional[str] = None, config: VideoConfig = None):
        super().__init__()
        if not PYQT_AVAILABLE:
            raise ImportError("PyQt5 is required for preview window")
        
        self.config = config or VideoConfig()
        self.video_path = video_path
        self.opening_effect = opening_effect
        self.gif_path = gif_path
        self.worker = None
        
        # Set window properties for better visibility on macOS
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.WindowMinimizeButtonHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, False)
        
        self.setup_ui()
        
        # Ensure window is always on top
        self.setWindowState(Qt.WindowActive)
    
    def setup_ui(self):
        """Setup the preview window UI"""
        self.setWindowTitle("🎬 Video Preview - Effects Demo")
        self.setGeometry(200, 200, 800, 700)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("🎬 Video Preview - Effects Demo")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #4CAF50; margin: 10px;")
        layout.addWidget(title)
        
        # Video display
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(600, 600)
        self.video_label.setStyleSheet("border: 2px solid #555555; background-color: black;")
        layout.addWidget(self.video_label)
        
        # Control frame
        control_frame = QFrame()
        control_layout = QHBoxLayout(control_frame)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        control_layout.addWidget(self.progress_bar)
        
        # Time label
        self.time_label = QLabel("0.0s / 3.0s")
        self.time_label.setFont(QFont("Arial", 10))
        control_layout.addWidget(self.time_label)
        
        # Play/Pause button
        self.play_btn = QPushButton("▶️ Start Preview")
        self.play_btn.clicked.connect(self.toggle_play_pause)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        control_layout.addWidget(self.play_btn)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        control_layout.addWidget(close_btn)
        
        layout.addWidget(control_frame)
    
    def start_preview(self):
        """Start the preview"""
        try:
            # Force window to be visible
            self.show()
            self.raise_()
            self.activateWindow()
            self.setVisible(True)
            self.setWindowState(Qt.WindowActive)
            
            # Process events to ensure window is displayed
            app = QApplication.instance()
            if app:
                app.processEvents()
            
            print(f"🎬 Preview window visibility check:")
            print(f"   - isVisible: {self.isVisible()}")
            print(f"   - geometry: {self.geometry()}")
            print(f"   - windowState: {self.windowState()}")
            print(f"   - QApplication active window: {app.activeWindow() if app else 'None'}")
            
            # Create worker (no background video needed)
            self.worker = PreviewWorker(
                self.video_path, "", self.opening_effect, 
                self.gif_path, self.config
            )
            
            # Connect signals
            self.worker.frame_ready.connect(self.update_frame)
            self.worker.progress_updated.connect(self.progress_bar.setValue)
            self.worker.time_updated.connect(self.time_label.setText)
            self.worker.finished.connect(self.preview_finished)
            self.worker.error_occurred.connect(self.preview_error)
            
            # Start worker
            self.worker.start()
            
            # Update button state
            self.play_btn.setText("⏸️ Pause")
            
        except Exception as e:
            self.video_label.setText(f"Preview Error: {str(e)}")
            self.video_label.setStyleSheet("color: red; border: 2px solid #555555; background-color: black;")
    
    def update_frame(self, qimage: QImage):
        """Update the video frame"""
        pixmap = QPixmap.fromImage(qimage)
        self.video_label.setPixmap(pixmap)
    
    def toggle_play_pause(self):
        """Toggle play/pause or restart preview"""
        if "Start" in self.play_btn.text() or "▶️" in self.play_btn.text():
            # Start or restart preview
            if self.worker and self.worker.isRunning():
                self.worker.resume()
            else:
                # Start new preview
                self.start_preview()
            self.play_btn.setText("⏸️ Pause")
        else:
            # Pause preview
            if self.worker and self.worker.isRunning():
                self.worker.pause()
                self.play_btn.setText("▶️ Resume")
    
    def preview_finished(self):
        """Handle preview completion"""
        self.play_btn.setText("▶️ Replay")
        self.progress_bar.setValue(100)
        self.time_label.setText("Preview completed - Click ▶️ Replay to watch again")
        
        # Don't close the window, just show completion message
        print("🎬 Preview completed - window remains open")
    
    def preview_error(self, error_message: str):
        """Handle preview error"""
        self.video_label.setText(f"Error: {error_message}")
        self.video_label.setStyleSheet("color: red; border: 2px solid #555555; background-color: black;")
    
    def closeEvent(self, event):
        """Handle window close event"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        event.accept()

def create_preview_dialog(video_path: str, opening_effect: EffectType, 
                         gif_path: Optional[str] = None, config: VideoConfig = None):
    """Create a preview dialog"""
    if not PYQT_AVAILABLE:
        print("PyQt5 is required for preview")
        return None
    
    try:
        # Ensure we have a QApplication instance
        app = QApplication.instance()
        if app is None:
            print("❌ No QApplication instance found")
            return None
        
        print(f"🎬 Creating preview window...")
        preview_window = PreviewWindow(video_path, opening_effect, gif_path, config)
        
        # Set window properties for macOS visibility
        preview_window.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.WindowMinimizeButtonHint)
        preview_window.setAttribute(Qt.WA_ShowWithoutActivating, False)
        
        # Show window with multiple methods to ensure visibility
        preview_window.show()
        preview_window.raise_()
        preview_window.activateWindow()
        preview_window.setVisible(True)
        preview_window.showNormal()
        
        # Force window to front on macOS
        preview_window.setWindowState(Qt.WindowActive)
        
        # Process events to ensure window is displayed
        app.processEvents()
        
        # Don't auto-start preview, let user click play button
        # QTimer.singleShot(1000, preview_window.start_preview)
        
        print(f"🎬 Preview window created and shown: {preview_window.isVisible()}")
        print(f"🎬 Window geometry: {preview_window.geometry()}")
        print(f"🎬 Window state: {preview_window.windowState()}")
        print(f"🎬 QApplication active window: {app.activeWindow()}")
        
        return preview_window
    except Exception as e:
        print(f"Preview error: {e}")
        import traceback
        traceback.print_exc()
        return None 