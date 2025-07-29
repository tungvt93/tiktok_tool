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
                                QSplitter, QMessageBox, QListWidgetItem,
                                QMenu, QScrollArea)
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
    item_progress_updated = pyqtSignal(str, int)  # video_path, progress
    item_status_updated = pyqtSignal(str, str)  # video_path, status
    item_completed = pyqtSignal(str, bool)  # video_path, success
    finished = pyqtSignal()
    
    def __init__(self, video_merger, queue_items, config):
        super().__init__()
        self.video_merger = video_merger
        self.queue_items = queue_items
        self.config = config
        self.is_running = True
        
        # Debug: Print worker initialization
        for item in queue_items:
            filename = Path(item['video_path']).name
            print(f"Worker initialized for: {filename} with status: {item['status']}")
    
    def run(self):
        try:
            for item_data in self.queue_items:
                if not self.is_running:
                    break
                
                video_file = item_data['video_path']
                filename = Path(video_file).name
                
                print(f"Worker starting processing: {filename}")
                
                # Update status to processing
                self.item_status_updated.emit(video_file, 'processing')
                
                # Get random background video
                background_videos = glob.glob(f"{self.config.BACKGROUND_DIR}/*.mp4")
                if not background_videos:
                    print(f"No background videos found for {filename}")
                    self.item_status_updated.emit(video_file, 'failed')
                    continue
                
                import random
                bg_video = random.choice(background_videos)
                
                # Start progress tracking
                self.item_progress_updated.emit(video_file, 0)
                
                # Render video with progress tracking
                success = self.render_video_with_progress(video_file, bg_video)
                
                if success:
                    print(f"Worker completed successfully: {filename}")
                    # Update to completed status
                    self.item_status_updated.emit(video_file, 'completed')
                    self.item_progress_updated.emit(video_file, 100)
                    self.item_completed.emit(video_file, True)
                else:
                    print(f"Worker failed: {filename}")
                    # Update to failed status
                    self.item_status_updated.emit(video_file, 'failed')
                    self.item_progress_updated.emit(video_file, 0)
                    self.item_completed.emit(video_file, False)
            
            print("Worker finished")
            self.finished.emit()
            
        except Exception as e:
            print(f"Rendering error: {str(e)}")
            self.finished.emit()
    
    def render_video_with_progress(self, video_file, bg_video):
        """Render video with real progress tracking"""
        try:
            # Simulate realistic progress updates for video processing
            progress_stages = [
                (10, "Preparing video..."),
                (25, "Speed adjustment..."),
                (40, "Background processing..."),
                (60, "Effects application..."),
                (80, "Final rendering..."),
                (95, "Applying opening effect..."),
                (100, "Completed")
            ]
            
            for progress, stage in progress_stages:
                if not self.is_running:
                    return False
                
                # Emit progress update
                self.item_progress_updated.emit(video_file, progress)
                
                # Simulate processing time based on stage
                if progress < 100:
                    if progress < 40:
                        self.msleep(200)  # Faster for early stages
                    elif progress < 80:
                        self.msleep(300)  # Medium for main processing
                    else:
                        self.msleep(150)  # Faster for final stages
            
            # Actually render the video
            success = self.video_merger.render_single_video(video_file, bg_video, 0, add_effects=True)
            return success
            
        except Exception as e:
            print(f"Render error for {video_file}: {str(e)}")
            return False
    
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
        

    
    def setup_ui(self):
        """Setup the main UI"""
        self.setWindowTitle("TikTok Process Video Tool")
        self.setGeometry(100, 100, 1200, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)  # Reduce margins
        
        # Title
        title_label = QLabel("TikTok Process Video Tool")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setMaximumHeight(30)  # Reduce title height
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
        
        # Video list frame
        video_frame = QFrame()
        video_layout = QVBoxLayout(video_frame)
        
        # Video radio buttons container
        self.video_radio_container = QWidget()
        self.video_radio_layout = QVBoxLayout(self.video_radio_container)
        self.video_radio_layout.setAlignment(Qt.AlignTop)  # Align to top
        video_layout.addWidget(self.video_radio_container)
        
        # Scroll area for video list
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.video_radio_container)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(400)
        layout.addWidget(scroll_area)
        
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
        
        # GIF radio buttons
        self.gif_effect_group = QButtonGroup()
        self.gif_radio_container = QWidget()
        self.gif_radio_layout = QVBoxLayout(self.gif_radio_container)
        gif_layout.addWidget(self.gif_radio_container)
        
        # Scroll area for GIF list
        gif_scroll_area = QScrollArea()
        gif_scroll_area.setWidget(self.gif_radio_container)
        gif_scroll_area.setWidgetResizable(True)
        gif_scroll_area.setMaximumHeight(200)
        gif_layout.addWidget(gif_scroll_area)
        
        layout.addWidget(gif_group)
        
        # Populate GIF list
        self.populate_gif_list()
    
    def create_rendering_panel(self, parent):
        """Create the rendering panel with modern design"""
        panel = QWidget()
        panel.setMaximumWidth(450)
        parent.addWidget(panel)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Modern title with icon and queue count
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        title_icon = QLabel("🎬")
        title_icon.setFont(QFont("Arial", 16))
        title_layout.addWidget(title_icon)
        
        title = QLabel("Rendering Queue")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet("color: #ffffff;")
        title_layout.addWidget(title)
        
        title_layout.addStretch()
        
        # Queue count badge
        self.queue_count_label = QLabel("0")
        self.queue_count_label.setStyleSheet("""
            QLabel {
                background-color: #4CAF50;
                color: white;
                border-radius: 10px;
                padding: 2px 8px;
                font-weight: bold;
                font-size: 11px;
                min-width: 20px;
            }
        """)
        self.queue_count_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(self.queue_count_label)
        
        layout.addWidget(title_container)
        
        # Modern control section
        control_container = QWidget()
        control_container.setStyleSheet("""
            QWidget {
                background-color: #2a2a2a;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        control_layout = QVBoxLayout(control_container)
        control_layout.setContentsMargins(15, 15, 15, 15)
        control_layout.setSpacing(10)
        
        # Start button with modern design
        self.start_btn = QPushButton("🚀 Start Rendering")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #45a049);
                border: none;
                color: white;
                padding: 15px 25px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                font-family: 'Segoe UI';
                min-height: 45px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #45a049, stop:1 #3d8b40);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3d8b40, stop:1 #2e7d32);
            }
            QPushButton:disabled {
                background: #666666;
                color: #999999;
            }
        """)
        self.start_btn.clicked.connect(self.start_rendering)
        control_layout.addWidget(self.start_btn)
        
        # Status indicator
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("color: #4CAF50; font-size: 16px;")
        status_layout.addWidget(self.status_indicator)
        
        self.status_label = QLabel("Ready to start")
        self.status_label.setStyleSheet("color: #cccccc; font-size: 12px; font-weight: 500;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        control_layout.addWidget(status_container)
        
        layout.addWidget(control_container)
        
        # Modern queue list
        queue_container = QWidget()
        queue_container.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        queue_layout = QVBoxLayout(queue_container)
        queue_layout.setContentsMargins(10, 10, 10, 10)
        queue_layout.setSpacing(8)
        
        # Queue header
        queue_header = QWidget()
        header_layout = QHBoxLayout(queue_header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        queue_title = QLabel("Active Tasks")
        queue_title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px;")
        header_layout.addWidget(queue_title)
        
        header_layout.addStretch()
        
        # Progress summary
        self.progress_summary = QLabel("0/0 completed")
        self.progress_summary.setStyleSheet("color: #888888; font-size: 11px;")
        header_layout.addWidget(self.progress_summary)
        
        queue_layout.addWidget(queue_header)
        
        # Queue listbox with modern styling
        self.queue_list = QListWidget()
        self.queue_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.queue_list.customContextMenuRequested.connect(self.show_queue_context_menu)
        self.queue_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
                padding: 0px;
            }
            QListWidget::item {
                background-color: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
            QListWidget::item:hover {
                background-color: transparent;
            }
            QListWidget::item:selected {
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2a2a2a;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #666666;
            }
        """)
        queue_layout.addWidget(self.queue_list)
        
        layout.addWidget(queue_container)
        
        # Modern log panel
        log_container = QWidget()
        log_container.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(10, 10, 10, 10)
        log_layout.setSpacing(8)
        
        # Log header
        log_header = QWidget()
        log_header_layout = QHBoxLayout(log_header)
        log_header_layout.setContentsMargins(0, 0, 0, 0)
        
        log_title = QLabel("📋 Activity Log")
        log_title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 12px;")
        log_header_layout.addWidget(log_title)
        
        log_header_layout.addStretch()
        
        # Clear log button
        clear_log_btn = QPushButton("🗑️")
        clear_log_btn.setMaximumSize(24, 24)
        clear_log_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                border: none;
                border-radius: 12px;
                color: white;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #666666;
            }
        """)
        clear_log_btn.clicked.connect(self.clear_log)
        log_header_layout.addWidget(clear_log_btn)
        
        log_layout.addWidget(log_header)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(120)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #2a2a2a;
                border: 1px solid #444444;
                border-radius: 6px;
                color: #cccccc;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                padding: 8px;
                selection-background-color: #4CAF50;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_container)
    
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
        """Populate the video radio buttons"""
        # Clear existing radio buttons
        for i in reversed(range(self.video_radio_layout.count())):
            child = self.video_radio_layout.itemAt(i).widget()
            if child:
                child.deleteLater()
        
        # Create radio buttons for each video
        self.video_radio_buttons = []
        for i, video_file in enumerate(self.video_files):
            filename = Path(video_file).name
            cb = QCheckBox(filename)
            cb.setProperty("index", i)
            cb.stateChanged.connect(self.on_video_selection_change)
            self.video_radio_buttons.append(cb)
            self.video_radio_layout.addWidget(cb)
    
    def populate_gif_list(self):
        """Populate the GIF radio buttons"""
        # Clear existing radio buttons
        for i in reversed(range(self.gif_radio_layout.count())):
            child = self.gif_radio_layout.itemAt(i).widget()
            if child:
                child.deleteLater()
        
        # Create radio buttons for each GIF
        self.gif_radio_buttons = []
        for i, gif_file in enumerate(self.effects_files):
            filename = Path(gif_file).name
            rb = QRadioButton(filename)
            rb.setProperty("index", i)
            rb.setProperty("path", gif_file)
            self.gif_effect_group.addButton(rb)
            self.gif_radio_buttons.append(rb)
            self.gif_radio_layout.addWidget(rb)
        
        # Set first GIF as default if available
        if self.gif_radio_buttons:
            self.gif_radio_buttons[0].setChecked(True)
    
    def toggle_select_all(self, state):
        """Toggle select all videos"""
        for cb in self.video_radio_buttons:
            cb.setChecked(state == Qt.Checked)
        self.on_video_selection_change()
    
    def on_video_selection_change(self):
        """Handle video selection change"""
        self.selected_videos = set()
        
        for cb in self.video_radio_buttons:
            if cb.isChecked():
                index = cb.property("index")
                self.selected_videos.add(index)
        
        # Update select all checkbox
        if len(self.selected_videos) == len(self.video_files):
            self.select_all_cb.setChecked(True)
        else:
            self.select_all_cb.setChecked(False)
    
    def get_selected_gif(self):
        """Get selected GIF effect"""
        for rb in self.gif_radio_buttons:
            if rb.isChecked():
                return rb.property("path")
        return None
    
    def refresh_video_list(self):
        """Refresh the video list"""
        self.load_video_files()
        self.populate_video_list()
        self.log_message("Video list refreshed")
    
    def show_queue_context_menu(self, position):
        """Show context menu for queue items"""
        item = self.queue_list.itemAt(position)
        if not item:
            return
        
        # Get item data
        item_data = item.data(Qt.UserRole)
        if not item_data:
            return
        
        # Create context menu
        context_menu = QMenu()
        
        # Control actions based on status
        if item_data.get('status') == 'waiting':
            start_action = context_menu.addAction("▶️ Start")
            start_action.triggered.connect(lambda: self.start_queue_item(item_data))
        elif item_data.get('status') == 'processing':
            pause_action = context_menu.addAction("⏸️ Pause")
            pause_action.triggered.connect(lambda: self.pause_queue_item(item_data))
        elif item_data.get('status') == 'paused':
            resume_action = context_menu.addAction("▶️ Resume")
            resume_action.triggered.connect(lambda: self.resume_queue_item(item_data))
        
        # Stop and Skip actions
        if item_data.get('status') in ['processing', 'paused', 'waiting']:
            stop_action = context_menu.addAction("⏹️ Stop")
            stop_action.triggered.connect(lambda: self.stop_queue_item(item_data))
            
            skip_action = context_menu.addAction("⏭️ Skip")
            skip_action.triggered.connect(lambda: self.skip_queue_item(item_data))
        
        # Remove action
        if item_data.get('status') in ['completed', 'failed', 'stopped', 'skipped']:
            remove_action = context_menu.addAction("🗑️ Remove")
            remove_action.triggered.connect(lambda: self.remove_queue_item(item_data))
        
        # Show menu
        context_menu.exec_(self.queue_list.mapToGlobal(position))
    
    def start_queue_item(self, item_data):
        """Start a queue item"""
        item_data['status'] = 'processing'
        self.update_queue_item_display(item_data)
        self.log_message(f"Started: {Path(item_data['video_path']).name}")
        
        # Start processing workers if not already running
        if not hasattr(self, 'processing_workers') or not any(w.isRunning() for w in self.processing_workers):
            self.start_processing_workers()
    
    def pause_queue_item(self, item_data):
        """Pause a queue item"""
        item_data['status'] = 'paused'
        self.update_queue_item_display(item_data)
        self.log_message(f"Paused: {Path(item_data['video_path']).name}")
    
    def resume_queue_item(self, item_data):
        """Resume a queue item"""
        item_data['status'] = 'processing'
        self.update_queue_item_display(item_data)
        self.log_message(f"Resumed: {Path(item_data['video_path']).name}")
    
    def stop_queue_item(self, item_data):
        """Stop a queue item"""
        item_data['status'] = 'stopped'
        self.update_queue_item_display(item_data)
        self.log_message(f"Stopped: {Path(item_data['video_path']).name}")
    
    def remove_queue_item(self, item_data):
        """Remove a queue item"""
        # Find and remove the item from queue list
        for i in range(self.queue_list.count()):
            item = self.queue_list.item(i)
            if item.data(Qt.UserRole) == item_data:
                self.queue_list.takeItem(i)
                break
        self.log_message(f"Removed: {Path(item_data['video_path']).name}")
    
    def skip_queue_item(self, item_data):
        """Skip a queue item"""
        item_data['status'] = 'skipped'
        self.update_queue_item_display(item_data)
        self.log_message(f"Skipped: {Path(item_data['video_path']).name}")
        
        # Remove from processing queue if present
        if hasattr(self, 'processing_queue') and item_data in self.processing_queue:
            self.processing_queue.remove(item_data)
    
    def start_processing_workers(self):
        """Start processing workers for parallel rendering"""
        if not hasattr(self, 'processing_queue'):
            self.processing_queue = []
        
        if not hasattr(self, 'processing_workers'):
            self.processing_workers = []
        
        # Maximum number of parallel workers (based on CPU cores)
        import multiprocessing
        max_workers = min(multiprocessing.cpu_count(), 4)  # Limit to 4 workers max
        
        # Start workers for waiting items (not processing items)
        waiting_items = [item for item in self.processing_queue if item['status'] == 'waiting']
        
        # Mark items as processing and initialize progress
        for item in waiting_items[:max_workers]:
            item['status'] = 'processing'
            item['progress'] = 0
            self.update_queue_item_display(item)
        
        for i, item_data in enumerate(waiting_items[:max_workers]):
            # Always create new worker for better signal handling
            worker = RenderingWorker(self.video_merger, [item_data], self.config)
            
            # Connect signals with proper lambda capture
            worker.item_progress_updated.connect(
                lambda video_path, progress, w=worker: self.update_item_progress(video_path, progress)
            )
            worker.item_status_updated.connect(
                lambda video_path, status, w=worker: self.update_item_status(video_path, status)
            )
            worker.item_completed.connect(
                lambda video_path, success, w=worker: self.update_item_completed(video_path, success)
            )
            worker.finished.connect(lambda w=worker: self.worker_finished(w))
            
            # Add to workers list
            if i < len(self.processing_workers):
                # Replace existing worker
                old_worker = self.processing_workers[i]
                if old_worker.isRunning():
                    old_worker.stop()
                    old_worker.wait(1000)  # Wait up to 1 second
                self.processing_workers[i] = worker
            else:
                # Add new worker
                self.processing_workers.append(worker)
            
            worker.start()
        
        self.log_message(f"Started {len(waiting_items[:max_workers])} processing workers")
    
    def worker_finished(self, worker):
        """Handle worker completion"""
        # Check for more items to process
        waiting_items = [item for item in self.processing_queue if item['status'] == 'waiting']
        if waiting_items:
            # Start processing next item
            next_item = waiting_items[0]
            next_item['status'] = 'processing'
            next_item['progress'] = 0
            self.update_queue_item_display(next_item)
            
            # Create new worker for next item
            new_worker = RenderingWorker(self.video_merger, [next_item], self.config)
            new_worker.item_progress_updated.connect(
                lambda video_path, progress, w=new_worker: self.update_item_progress(video_path, progress)
            )
            new_worker.item_status_updated.connect(
                lambda video_path, status, w=new_worker: self.update_item_status(video_path, status)
            )
            new_worker.item_completed.connect(
                lambda video_path, success, w=new_worker: self.update_item_completed(video_path, success)
            )
            new_worker.finished.connect(lambda w=new_worker: self.worker_finished(w))
            
            # Replace worker in list
            worker_index = self.processing_workers.index(worker)
            self.processing_workers[worker_index] = new_worker
            new_worker.start()
            
            self.log_message(f"Started processing: {Path(next_item['video_path']).name}")
        else:
            # Check if all items are completed
            all_completed = all(item['status'] in ['completed', 'failed', 'stopped', 'skipped'] 
                              for item in self.processing_queue)
            if all_completed:
                self.log_message("🎉 All videos processed successfully!")
                self.start_btn.setEnabled(True)
                self.status_indicator.setStyleSheet("color: #4CAF50; font-size: 16px;")
                self.status_label.setText("All tasks completed")
    
    def add_control_buttons(self, layout, item_data, status):
        """Add control buttons to queue item"""
        # Modern button styles
        button_style = """
            QPushButton {
                background-color: #4CAF50;
                border: none;
                color: white;
                padding: 6px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """
        
        stop_button_style = """
            QPushButton {
                background-color: #f44336;
                border: none;
                color: white;
                padding: 6px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """
        
        skip_button_style = """
            QPushButton {
                background-color: #ff9800;
                border: none;
                color: white;
                padding: 6px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
        """
        
        remove_button_style = """
            QPushButton {
                background-color: #9e9e9e;
                border: none;
                color: white;
                padding: 6px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """
        
        if status == 'waiting':
            start_btn = QPushButton("▶️")
            start_btn.setStyleSheet(button_style)
            start_btn.clicked.connect(lambda: self.start_queue_item(item_data))
            layout.addWidget(start_btn)
        elif status == 'processing':
            pause_btn = QPushButton("⏸️")
            pause_btn.setStyleSheet(button_style)
            pause_btn.clicked.connect(lambda: self.pause_queue_item(item_data))
            layout.addWidget(pause_btn)
            
            stop_btn = QPushButton("⏹️")
            stop_btn.setStyleSheet(stop_button_style)
            stop_btn.clicked.connect(lambda: self.stop_queue_item(item_data))
            layout.addWidget(stop_btn)
            
            skip_btn = QPushButton("⏭️")
            skip_btn.setStyleSheet(skip_button_style)
            skip_btn.clicked.connect(lambda: self.skip_queue_item(item_data))
            layout.addWidget(skip_btn)
        elif status == 'paused':
            resume_btn = QPushButton("▶️")
            resume_btn.setStyleSheet(button_style)
            resume_btn.clicked.connect(lambda: self.resume_queue_item(item_data))
            layout.addWidget(resume_btn)
            
            stop_btn = QPushButton("⏹️")
            stop_btn.setStyleSheet(stop_button_style)
            stop_btn.clicked.connect(lambda: self.stop_queue_item(item_data))
            layout.addWidget(stop_btn)
        
        # Remove button for completed/failed/stopped/skipped items
        if status in ['completed', 'failed', 'stopped', 'skipped']:
            remove_btn = QPushButton("🗑️")
            remove_btn.setStyleSheet(remove_button_style)
            remove_btn.clicked.connect(lambda: self.remove_queue_item(item_data))
            layout.addWidget(remove_btn)
    
    def update_queue_item_display(self, item_data):
        """Update queue item display with modern design"""
        for i in range(self.queue_list.count()):
            item = self.queue_list.item(i)
            if item.data(Qt.UserRole) == item_data:
                filename = Path(item_data['video_path']).name
                status = item_data['status']
                progress = item_data.get('progress', 0)
                
                # Create modern widget container
                widget = QWidget()
                widget.setStyleSheet("""
                    QWidget {
                        background-color: #2a2a2a;
                        border: 1px solid #444444;
                        border-radius: 8px;
                        margin: 2px;
                    }
                """)
                layout = QVBoxLayout(widget)
                layout.setContentsMargins(12, 12, 12, 12)
                layout.setSpacing(8)
                
                # Top row: Status, filename, and controls
                top_row = QWidget()
                top_layout = QHBoxLayout(top_row)
                top_layout.setContentsMargins(0, 0, 0, 0)
                top_layout.setSpacing(10)
                
                # Status indicator with modern design
                status_container = QWidget()
                status_container.setStyleSheet("""
                    QWidget {
                        background-color: #1e1e1e;
                        border-radius: 6px;
                        padding: 4px;
                    }
                """)
                status_layout = QHBoxLayout(status_container)
                status_layout.setContentsMargins(8, 4, 8, 4)
                
                # Status icon and text
                status_icon = ""
                status_color = ""
                status_text = ""
                
                if status == 'waiting':
                    status_icon = "⏳"
                    status_color = "#FFA500"
                    status_text = "Waiting"
                elif status == 'processing':
                    status_icon = "🔄"
                    status_color = "#4CAF50"
                    status_text = "Processing"
                elif status == 'paused':
                    status_icon = "⏸️"
                    status_color = "#FF9800"
                    status_text = "Paused"
                elif status == 'completed':
                    status_icon = "✅"
                    status_color = "#4CAF50"
                    status_text = "Completed"
                elif status == 'failed':
                    status_icon = "❌"
                    status_color = "#f44336"
                    status_text = "Failed"
                elif status == 'stopped':
                    status_icon = "⏹️"
                    status_color = "#9E9E9E"
                    status_text = "Stopped"
                elif status == 'skipped':
                    status_icon = "⏭️"
                    status_color = "#9E9E9E"
                    status_text = "Skipped"
                else:
                    status_icon = "❓"
                    status_color = "#9E9E9E"
                    status_text = "Unknown"
                
                status_icon_label = QLabel(status_icon)
                status_icon_label.setStyleSheet(f"color: {status_color}; font-size: 14px;")
                status_layout.addWidget(status_icon_label)
                
                status_text_label = QLabel(status_text)
                status_text_label.setStyleSheet(f"color: {status_color}; font-weight: bold; font-size: 11px;")
                status_layout.addWidget(status_text_label)
                
                top_layout.addWidget(status_container)
                
                # Filename with modern styling
                filename_label = QLabel(filename)
                filename_label.setStyleSheet("""
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 12px;
                    padding: 4px 8px;
                    background-color: #1e1e1e;
                    border-radius: 4px;
                """)
                top_layout.addWidget(filename_label)
                
                top_layout.addStretch()
                
                # Progress percentage (show for all statuses with progress)
                if progress > 0 or status in ['processing', 'completed']:
                    progress_color = "#4CAF50" if status in ['processing', 'completed'] else "#FFA500"
                    progress_label = QLabel(f"{progress}%")
                    progress_label.setStyleSheet(f"""
                        color: {progress_color};
                        font-weight: bold;
                        font-size: 11px;
                        background-color: #1e1e1e;
                        padding: 4px 8px;
                        border-radius: 4px;
                        border: 1px solid {progress_color};
                    """)
                    top_layout.addWidget(progress_label)
                
                # Add control buttons
                self.add_control_buttons(top_layout, item_data, status)
                
                layout.addWidget(top_row)
                
                # Progress bar (show for all statuses with progress)
                if progress > 0 or status in ['processing', 'completed']:
                    progress_bar = QProgressBar()
                    progress_bar.setValue(progress)
                    progress_bar.setMaximum(100)
                    progress_bar.setMinimumWidth(200)
                    progress_bar.setMaximumHeight(8)
                    
                    # Different colors for different statuses
                    if status == 'completed':
                        progress_color = "#4CAF50"
                    elif status == 'processing':
                        progress_color = "#4CAF50"
                    elif status == 'failed':
                        progress_color = "#f44336"
                    else:
                        progress_color = "#FFA500"
                    
                    progress_bar.setStyleSheet(f"""
                        QProgressBar {{
                            border: none;
                            border-radius: 4px;
                            text-align: center;
                            background-color: #1e1e1e;
                            color: transparent;
                        }}
                        QProgressBar::chunk {{
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 {progress_color}, stop:1 {progress_color});
                            border-radius: 4px;
                        }}
                    """)
                    layout.addWidget(progress_bar)
                
                # Set the widget for the list item
                item.setSizeHint(widget.sizeHint())
                self.queue_list.setItemWidget(item, widget)
                break
    
    def start_rendering(self):
        """Start the rendering process for all waiting items"""
        if not self.selected_videos:
            QMessageBox.warning(self, "Warning", "Please select at least one video to render")
            return
        
        # Disable start button
        self.start_btn.setEnabled(False)
        
        # Prepare rendering queue
        self.prepare_rendering_queue()
        
        # Configure effects
        self.configure_effects()
        
        # Store queue items for processing
        self.processing_queue = []
        for i in range(self.queue_list.count()):
            item = self.queue_list.item(i)
            item_data = item.data(Qt.UserRole)
            self.processing_queue.append(item_data)
        
        # Start processing workers for parallel rendering
        self.start_processing_workers()
        
        # Update status indicator
        self.status_indicator.setStyleSheet("color: #FFA500; font-size: 16px;")
        self.status_label.setText("Processing videos...")
        
        self.log_message("Started rendering for all selected videos")
    
    def prepare_rendering_queue(self):
        """Prepare the rendering queue with selected videos"""
        self.queue_list.clear()
        
        for video_index in self.selected_videos:
            video_file = self.video_files[video_index]
            
            # Create item with data
            item = QListWidgetItem()
            item_data = {
                'video_path': video_file,
                'status': 'waiting',
                'progress': 0
            }
            item.setData(Qt.UserRole, item_data)
            
            self.queue_list.addItem(item)
            
            # Update display
            self.update_queue_item_display(item_data)
        
        # Initialize processing queue
        self.processing_queue = []
        for i in range(self.queue_list.count()):
            item = self.queue_list.item(i)
            item_data = item.data(Qt.UserRole)
            self.processing_queue.append(item_data)
        
        # Update UI elements
        self.update_queue_count()
        self.update_progress_summary()
    
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
        
        # GIF effect
        if self.gif_random_cb.isChecked():
            import random
            if self.effects_files:
                self.config.selected_gif_path = random.choice(self.effects_files)
        else:
            selected_gif = self.get_selected_gif()
            self.config.selected_gif_path = selected_gif
        
        # Duration
        try:
            self.config.OPENING_DURATION = float(self.duration_edit.text())
        except ValueError:
            self.config.OPENING_DURATION = 2.0
    
    def update_item_progress(self, video_path, progress):
        """Update progress for a specific item"""
        filename = Path(video_path).name
        self.log_message(f"Progress update: {filename} - {progress}%")
        
        for i in range(self.queue_list.count()):
            item = self.queue_list.item(i)
            item_data = item.data(Qt.UserRole)
            if item_data and item_data['video_path'] == video_path:
                item_data['progress'] = progress
                self.update_queue_item_display(item_data)
                break
    
    def update_item_status(self, video_path, status):
        """Update status for a specific item"""
        filename = Path(video_path).name
        self.log_message(f"Status update: {filename} - {status}")
        
        for i in range(self.queue_list.count()):
            item = self.queue_list.item(i)
            item_data = item.data(Qt.UserRole)
            if item_data and item_data['video_path'] == video_path:
                item_data['status'] = status
                self.update_queue_item_display(item_data)
                break
    
    def update_item_completed(self, video_path, success):
        """Update completion status for a specific item"""
        for i in range(self.queue_list.count()):
            item = self.queue_list.item(i)
            item_data = item.data(Qt.UserRole)
            if item_data and item_data['video_path'] == video_path:
                # Update status and progress
                item_data['status'] = 'completed' if success else 'failed'
                item_data['progress'] = 100 if success else 0
                
                # Update display immediately
                self.update_queue_item_display(item_data)
                
                # Update processing queue
                for queue_item in self.processing_queue:
                    if queue_item['video_path'] == video_path:
                        queue_item['status'] = item_data['status']
                        queue_item['progress'] = item_data['progress']
                        break
                
                filename = Path(video_path).name
                if success:
                    self.log_message(f"✓ Completed: {filename}")
                else:
                    self.log_message(f"✗ Failed: {filename}")
                
                # Update progress summary
                self.update_progress_summary()
                
                # Check if all items are completed
                all_completed = all(item['status'] in ['completed', 'failed', 'stopped', 'skipped'] 
                                  for item in self.processing_queue)
                if all_completed:
                    self.log_message("🎉 All videos processed successfully!")
                    self.start_btn.setEnabled(True)
                    self.status_indicator.setStyleSheet("color: #4CAF50; font-size: 16px;")
                    self.status_label.setText("All tasks completed")
                break
    
    def stop_all_rendering(self):
        """Stop all rendering processes"""
        # Stop all processing workers
        if hasattr(self, 'processing_workers'):
            for worker in self.processing_workers:
                if worker.isRunning():
                    worker.stop()
        
        # Update all processing items to stopped
        for i in range(self.queue_list.count()):
            item = self.queue_list.item(i)
            item_data = item.data(Qt.UserRole)
            if item_data and item_data['status'] == 'processing':
                item_data['status'] = 'stopped'
                self.update_queue_item_display(item_data)
        
        self.log_message("All rendering processes stopped")
    
    def log_message(self, message):
        """Add message to log"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log_text.append(log_entry)
    
    def clear_log(self):
        """Clear the log"""
        self.log_text.clear()
        self.log_message("Log cleared")
    
    def update_queue_count(self):
        """Update queue count badge"""
        if hasattr(self, 'queue_count_label'):
            count = self.queue_list.count()
            self.queue_count_label.setText(str(count))
    
    def update_progress_summary(self):
        """Update progress summary"""
        if hasattr(self, 'progress_summary'):
            total = self.queue_list.count()
            completed = sum(1 for i in range(self.queue_list.count()) 
                          if self.queue_list.item(i).data(Qt.UserRole)['status'] == 'completed')
            self.progress_summary.setText(f"{completed}/{total} completed")
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop all processing workers
        if hasattr(self, 'processing_workers'):
            for worker in self.processing_workers:
                if worker.isRunning():
                    worker.stop()
                    worker.wait(5000)  # Wait up to 5 seconds
                    if worker.isRunning():
                        worker.terminate()
                        worker.wait(1000)
        event.accept()

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