"""
GUI Application for TikTok Video Processing Tool using PyQt5
Modern interface with video selection, effects configuration, and rendering progress
"""

import sys
import os
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional
import queue
import time
import threading
import json

try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                QHBoxLayout, QLabel, QPushButton, QListWidget, 
                                QCheckBox, QRadioButton, QButtonGroup, QLineEdit,
                                QProgressBar, QTextEdit, QGroupBox, QFrame,
                                QSplitter, QMessageBox, QListWidgetItem)
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
    from PyQt5.QtGui import QFont, QPalette, QColor
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("PyQt5 not available. Please install: pip install PyQt5")

# Import from main.py
from main import VideoMerger, VideoConfig, EffectType, GIFProcessor

class RenderingWorker(QThread):
    """Worker thread for video rendering"""
    progress_updated = pyqtSignal(int, int)  # current, total
    status_updated = pyqtSignal(str)
    video_completed = pyqtSignal(int, bool)  # index, success
    finished = pyqtSignal()
    
    def __init__(self, video_merger, selected_videos, video_files, config):
        super().__init__()
        self.video_merger = video_merger
        self.selected_videos = selected_videos
        self.video_files = video_files
        self.config = config
        self.is_running = True
    
    def run(self):
        try:
            total_videos = len(self.selected_videos)
            completed = 0
            
            for video_index in self.selected_videos:
                if not self.is_running:
                    break
                
                video_file = self.video_files[video_index]
                filename = Path(video_file).name
                
                self.status_updated.emit(f"Processing: {filename}")
                
                # Get random background video
                background_videos = glob.glob(f"{self.config.BACKGROUND_DIR}/*.mp4")
                if not background_videos:
                    self.status_updated.emit("Error: No background videos found")
                    continue
                
                import random
                bg_video = random.choice(background_videos)
                
                # Render video
                success = self.video_merger.render_single_video(video_file, bg_video, completed, add_effects=True)
                
                self.video_completed.emit(completed, success)
                
                if success:
                    self.status_updated.emit(f"✓ Completed: {filename}")
                else:
                    self.status_updated.emit(f"✗ Failed: {filename}")
                
                completed += 1
                self.progress_updated.emit(completed, total_videos)
            
            self.finished.emit()
            
        except Exception as e:
            self.status_updated.emit(f"Rendering error: {str(e)}")
            self.finished.emit()
    
    def stop(self):
        self.is_running = False

class VideoProcessingGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        if not PYQT_AVAILABLE:
            QMessageBox.critical(None, "Error", "PyQt5 is not installed. Please install: pip install PyQt5")
            sys.exit(1)
        
        # Configuration
        self.config = VideoConfig()
        self.video_merger = VideoMerger(self.config)
        
        # Data storage
        self.video_files = []
        self.selected_videos = set()
        self.effects_files = []
        self.selected_effects = set()
        self.rendering_worker = None
        
        # Load data
        self.load_video_files()
        self.load_effects_files()
        
        # Setup UI
        self.setup_ui()
        self.setup_styles()
        
        # Setup timer for progress updates
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progress)
        self.progress_timer.start(100)  # Update every 100ms
    
    def setup_ui(self):
        """Setup the main UI"""
        self.setWindowTitle("TikTok Video Processing Tool")
        self.setGeometry(100, 100, 1400, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("TikTok Video Processing Tool")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        main_layout.addWidget(title_label)
        
        # Create three main sections
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Video selection
        self.create_video_selection_panel(splitter)
        
        # Center panel - Effects configuration
        self.create_effects_panel(splitter)
        
        # Right panel - Rendering queue and progress
        self.create_rendering_panel(splitter)
        
        # Set splitter proportions
        splitter.setSizes([400, 500, 500])
    
    def create_video_selection_panel(self, parent):
        """Create the left panel for video selection"""
        panel = QWidget()
        parent.addWidget(panel)
        
        layout = QVBoxLayout(panel)
        
        # Title
        title = QLabel("Video Selection")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        # Select all checkbox
        self.select_all_cb = QCheckBox("Select All Videos")
        self.select_all_cb.stateChanged.connect(self.toggle_select_all)
        layout.addWidget(self.select_all_cb)
        
        # Video list
        self.video_list = QListWidget()
        self.video_list.setSelectionMode(QListWidget.MultiSelection)
        self.video_list.itemSelectionChanged.connect(self.on_video_selection_change)
        layout.addWidget(self.video_list)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh Videos")
        refresh_btn.clicked.connect(self.refresh_video_list)
        layout.addWidget(refresh_btn)
        
        # Populate video list
        self.populate_video_list()
    
    def create_effects_panel(self, parent):
        """Create the center panel for effects configuration"""
        panel = QWidget()
        parent.addWidget(panel)
        
        layout = QVBoxLayout(panel)
        
        # Title
        title = QLabel("Effects Configuration")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        # Opening Effects Section
        opening_group = QGroupBox("Opening Effects")
        opening_layout = QVBoxLayout(opening_group)
        
        # Opening effects options
        self.opening_effect_group = QButtonGroup()
        effects = [
            ("None", "none"),
            ("Slide Right to Left", "slide_right_to_left"),
            ("Slide Left to Right", "slide_left_to_right"),
            ("Slide Top to Bottom", "slide_top_to_bottom"),
            ("Slide Bottom to Top", "slide_bottom_to_top"),
            ("Circle Expand", "circle_expand"),
            ("Circle Contract", "circle_contract"),
            ("Circle Rotate CW", "circle_rotate_cw"),
            ("Circle Rotate CCW", "circle_rotate_ccw"),
            ("Fade In", "fade_in")
        ]
        
        for text, value in effects:
            rb = QRadioButton(text)
            rb.setProperty("value", value)
            self.opening_effect_group.addButton(rb)
            opening_layout.addWidget(rb)
        
        # Set default selection
        self.opening_effect_group.buttons()[0].setChecked(True)
        
        # Random checkbox
        self.opening_random_cb = QCheckBox("Random Effect")
        opening_layout.addWidget(self.opening_random_cb)
        
        # Effect duration
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duration (seconds):"))
        self.duration_edit = QLineEdit("2.0")
        duration_layout.addWidget(self.duration_edit)
        opening_layout.addLayout(duration_layout)
        
        layout.addWidget(opening_group)
        
        # GIF Effects Section
        gif_group = QGroupBox("GIF Effects")
        gif_layout = QVBoxLayout(gif_group)
        
        # GIF selection options
        self.gif_random_cb = QCheckBox("Random GIF")
        gif_layout.addWidget(self.gif_random_cb)
        
        # GIF list
        self.gif_list = QListWidget()
        self.gif_list.setSelectionMode(QListWidget.MultiSelection)
        self.gif_list.itemSelectionChanged.connect(self.on_gif_selection_change)
        gif_layout.addWidget(self.gif_list)
        
        layout.addWidget(gif_group)
        
        # Preview button
        preview_btn = QPushButton("Preview Effects")
        preview_btn.clicked.connect(self.preview_effects)
        layout.addWidget(preview_btn)
        
        # Populate GIF list
        self.populate_gif_list()
    
    def create_rendering_panel(self, parent):
        """Create the right panel for rendering queue and progress"""
        panel = QWidget()
        parent.addWidget(panel)
        
        layout = QVBoxLayout(panel)
        
        # Title
        title = QLabel("Rendering Queue")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Start Rendering")
        self.start_btn.clicked.connect(self.start_rendering)
        control_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_rendering)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.pause_rendering)
        self.pause_btn.setEnabled(False)
        control_layout.addWidget(self.pause_btn)
        
        layout.addLayout(control_layout)
        
        # Progress frame
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        # Overall progress
        progress_layout.addWidget(QLabel("Overall Progress:"))
        self.overall_progress = QProgressBar()
        progress_layout.addWidget(self.overall_progress)
        
        # Current video progress
        progress_layout.addWidget(QLabel("Current Video:"))
        self.current_progress = QProgressBar()
        progress_layout.addWidget(self.current_progress)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Arial", 10, QFont.Bold))
        progress_layout.addWidget(self.status_label)
        
        layout.addWidget(progress_group)
        
        # Queue list frame
        queue_group = QGroupBox("Rendering Queue")
        queue_layout = QVBoxLayout(queue_group)
        
        # Queue listbox
        self.queue_list = QListWidget()
        queue_layout.addWidget(self.queue_list)
        
        layout.addWidget(queue_group)
        
        # Log frame
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
    
    def setup_styles(self):
        """Setup modern dark theme styles"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                border: 1px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
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
            QPushButton:disabled {
                background-color: #666666;
            }
            QListWidget {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #4CAF50;
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
            QTextEdit {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
                font-family: 'Consolas', monospace;
            }
            QLineEdit {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 4px;
                color: #ffffff;
                padding: 5px;
            }
        """)
    
    def load_video_files(self):
        """Load video files from dongphuc folder"""
        video_pattern = f"{self.config.INPUT_DIR}/*.mp4"
        self.video_files = sorted(glob.glob(video_pattern))
    
    def load_effects_files(self):
        """Load GIF effects from effects folder"""
        effects_pattern = f"{self.config.EFFECTS_DIR}/*.gif"
        self.effects_files = sorted(glob.glob(effects_pattern))
    
    def populate_video_list(self):
        """Populate the video listbox"""
        self.video_list.clear()
        for video_file in self.video_files:
            filename = Path(video_file).name
            item = QListWidgetItem(filename)
            self.video_list.addItem(item)
    
    def populate_gif_list(self):
        """Populate the GIF listbox"""
        self.gif_list.clear()
        for gif_file in self.effects_files:
            filename = Path(gif_file).name
            item = QListWidgetItem(filename)
            self.gif_list.addItem(item)
    
    def toggle_select_all(self, state):
        """Toggle select all videos"""
        if state == Qt.Checked:
            for i in range(self.video_list.count()):
                self.video_list.item(i).setSelected(True)
        else:
            self.video_list.clearSelection()
        self.on_video_selection_change()
    
    def on_video_selection_change(self):
        """Handle video selection change"""
        selected_items = self.video_list.selectedItems()
        self.selected_videos = set()
        
        for item in selected_items:
            index = self.video_list.row(item)
            self.selected_videos.add(index)
        
        # Update select all checkbox
        if len(selected_items) == len(self.video_files):
            self.select_all_cb.setChecked(True)
        else:
            self.select_all_cb.setChecked(False)
    
    def on_gif_selection_change(self):
        """Handle GIF selection change"""
        selected_items = self.gif_list.selectedItems()
        self.selected_effects = set()
        
        for item in selected_items:
            index = self.gif_list.row(item)
            self.selected_effects.add(index)
    
    def refresh_video_list(self):
        """Refresh the video list"""
        self.load_video_files()
        self.populate_video_list()
        self.log_message("Video list refreshed")
    
    def preview_effects(self):
        """Preview effects on a selected video"""
        if not self.selected_videos:
            QMessageBox.warning(self, "Warning", "Please select at least one video for preview")
            return
        
        # Get first selected video
        video_index = list(self.selected_videos)[0]
        video_file = self.video_files[video_index]
        
        # Get selected effects
        opening_effect = self.opening_effect_group.checkedButton().property("value")
        gif_effect = None
        if self.selected_effects:
            gif_index = list(self.selected_effects)[0]
            gif_effect = self.effects_files[gif_index]
        
        # Show preview dialog
        content = f"Video: {Path(video_file).name}\n"
        content += f"Opening Effect: {opening_effect}\n"
        content += f"GIF Effect: {Path(gif_effect).name if gif_effect else 'None'}\n"
        content += f"Duration: {self.duration_edit.text()} seconds"
        
        QMessageBox.information(self, "Effect Preview", content)
    
    def start_rendering(self):
        """Start the rendering process"""
        if not self.selected_videos:
            QMessageBox.warning(self, "Warning", "Please select at least one video to render")
            return
        
        # Prepare rendering queue
        self.prepare_rendering_queue()
        
        # Configure effects
        self.configure_effects()
        
        # Start rendering worker
        self.rendering_worker = RenderingWorker(
            self.video_merger, self.selected_videos, self.video_files, self.config
        )
        self.rendering_worker.progress_updated.connect(self.update_overall_progress)
        self.rendering_worker.status_updated.connect(self.update_status)
        self.rendering_worker.video_completed.connect(self.update_video_status)
        self.rendering_worker.finished.connect(self.rendering_completed)
        
        self.rendering_worker.start()
        
        # Update UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        
        self.log_message("Rendering started")
    
    def prepare_rendering_queue(self):
        """Prepare the rendering queue with selected videos"""
        self.queue_list.clear()
        
        for video_index in self.selected_videos:
            video_file = self.video_files[video_index]
            filename = Path(video_file).name
            item = QListWidgetItem(f"⏳ {filename}")
            self.queue_list.addItem(item)
        
        self.overall_progress.setMaximum(len(self.selected_videos))
        self.overall_progress.setValue(0)
        self.current_progress.setValue(0)
    
    def configure_effects(self):
        """Configure effects based on user selection"""
        # Opening effect
        if self.opening_random_cb.isChecked():
            import random
            effects = list(EffectType)
            self.config.OPENING_EFFECT = random.choice(effects)
        else:
            effect_map = {
                "none": EffectType.NONE,
                "slide_right_to_left": EffectType.SLIDE_RIGHT_TO_LEFT,
                "slide_left_to_right": EffectType.SLIDE_LEFT_TO_RIGHT,
                "slide_top_to_bottom": EffectType.SLIDE_TOP_TO_BOTTOM,
                "slide_bottom_to_top": EffectType.SLIDE_BOTTOM_TO_TOP,
                "circle_expand": EffectType.CIRCLE_EXPAND,
                "circle_contract": EffectType.CIRCLE_CONTRACT,
                "circle_rotate_cw": EffectType.CIRCLE_ROTATE_CW,
                "circle_rotate_ccw": EffectType.CIRCLE_ROTATE_CCW,
                "fade_in": EffectType.FADE_IN
            }
            selected_button = self.opening_effect_group.checkedButton()
            effect_value = selected_button.property("value")
            self.config.OPENING_EFFECT = effect_map.get(effect_value, EffectType.NONE)
        
        # Duration
        try:
            self.config.OPENING_DURATION = float(self.duration_edit.text())
        except ValueError:
            self.config.OPENING_DURATION = 2.0
    
    def update_overall_progress(self, current, total):
        """Update overall progress bar"""
        self.overall_progress.setValue(current)
    
    def update_status(self, status):
        """Update status label"""
        self.status_label.setText(status)
        self.log_message(status)
    
    def update_video_status(self, index, success):
        """Update video status in queue"""
        if index < self.queue_list.count():
            item = self.queue_list.item(index)
            if success:
                item.setBackground(QColor("#4CAF50"))
            else:
                item.setBackground(QColor("#f44336"))
    
    def stop_rendering(self):
        """Stop the rendering process"""
        if self.rendering_worker:
            self.rendering_worker.stop()
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.status_label.setText("Stopped")
        self.log_message("Rendering stopped")
    
    def pause_rendering(self):
        """Pause/resume rendering"""
        if self.pause_btn.text() == "Pause":
            if self.rendering_worker:
                self.rendering_worker.stop()
            self.pause_btn.setText("Resume")
            self.status_label.setText("Paused")
            self.log_message("Rendering paused")
        else:
            # Restart rendering
            self.pause_btn.setText("Pause")
            self.status_label.setText("Resumed")
            self.log_message("Rendering resumed")
            self.start_rendering()
    
    def rendering_completed(self):
        """Handle rendering completion"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.status_label.setText("Completed")
        self.log_message("Rendering completed")
    
    def update_progress(self):
        """Update progress bars"""
        if self.rendering_worker and self.rendering_worker.isRunning():
            # Simulate current video progress
            current_value = self.current_progress.value()
            if current_value < 100:
                self.current_progress.setValue(current_value + 1)
            else:
                self.current_progress.setValue(0)
    
    def log_message(self, message):
        """Add message to log"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log_text.append(log_entry)

def main():
    """Main entry point for GUI application"""
    app = QApplication(sys.argv)
    
    # Check if PyQt5 is available
    if not PYQT_AVAILABLE:
        print("PyQt5 is not installed. Please install: pip install PyQt5")
        sys.exit(1)
    
    window = VideoProcessingGUI()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 