"""
Main Window

Main GUI window using clean architecture with dependency injection.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Optional
from pathlib import Path

from ...application.services.video_service import VideoService
from ...application.services.processing_service import ProcessingService, JobProgressCallback
from ...application.services.effect_service import EffectService
from ...application.use_cases.get_videos_use_case import GetVideosUseCase, GetVideosRequest
from ...application.use_cases.process_video_use_case import ProcessVideoUseCase, ProcessVideoRequest
from ...application.models.video_models import VideoDTO
from ...application.models.processing_models import ProcessingJobDTO
from ...shared.config import AppConfig
from ...shared.utils import get_logger
from ..common.base_presenter import BasePresenter, BaseView
from ..common.ui_helpers import MessageBoxHelper, FormatHelper

logger = get_logger(__name__)


class MainWindowView(BaseView):
    """View interface for main window"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self._setup_window()
        self._create_widgets()
        self._setup_styles()

    def _setup_window(self):
        """Setup main window properties with modern features"""
        self.root.title("TikTok Video Processing Tool - Clean Architecture")
        self.root.geometry("1400x800")
        self.root.configure(bg='#1a1a1a')

        # Make window resizable
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        
        # Set minimum window size
        self.root.minsize(1000, 600)
        
        # Add window icon (placeholder)
        try:
            # You can add actual icon file here
            # self.root.iconbitmap('path/to/icon.ico')
            pass
        except:
            pass
            
        # Add smooth window animations
        self._setup_animations()
        
        # Setup responsive design
        self._setup_responsive_design()
        
        # Setup accessibility features
        self._setup_accessibility()

    def _setup_animations(self):
        """Setup smooth animations and micro-interactions"""
        # Store animation states
        self.animation_states = {
            'processing': False,
            'hover_effects': {},
            'button_states': {}
        }
        
        # Bind hover effects for buttons
        self._bind_hover_effects()
        
        # Setup progress animations
        self._setup_progress_animations()

    def _bind_hover_effects(self):
        """Bind hover effects for interactive elements"""
        def on_enter(event):
            widget = event.widget
            if hasattr(widget, 'configure'):
                try:
                    # Store original style
                    if widget not in self.animation_states['hover_effects']:
                        self.animation_states['hover_effects'][widget] = widget.cget('style')
                    
                    # Apply hover style
                    if 'Primary.TButton' in str(widget.cget('style')):
                        widget.configure()
                    elif 'Secondary.TButton' in str(widget.cget('style')):
                        widget.configure()
                except:
                    pass

        def on_leave(event):
            widget = event.widget
            if hasattr(widget, 'configure') and widget in self.animation_states['hover_effects']:
                try:
                    # Restore original style
                    original_style = self.animation_states['hover_effects'][widget]
                    widget.configure(style=original_style)
                except:
                    pass

        # Bind to all buttons (will be called after buttons are created)
        self.root.bind('<Map>', lambda e: self._apply_hover_bindings())

    def _apply_hover_bindings(self):
        """Apply hover bindings to all buttons"""
        def find_buttons(widget):
            if hasattr(widget, 'winfo_children'):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Button):
                        child.bind('<Enter>', self._on_button_enter)
                        child.bind('<Leave>', self._on_button_leave)
                    find_buttons(child)

        find_buttons(self.root)

    def _on_button_enter(self, event):
        """Handle button hover enter"""
        widget = event.widget
        try:
            # Add subtle scale effect
            widget.configure(cursor="hand2")
        except:
            pass

    def _on_button_leave(self, event):
        """Handle button hover leave"""
        widget = event.widget
        try:
            widget.configure(cursor="")
        except:
            pass

    def _setup_progress_animations(self):
        """Setup smooth progress bar animations"""
        self.progress_animation_id = None
        
    def animate_progress(self, target_value, duration=500):
        """Animate progress bar smoothly"""
        if self.progress_animation_id:
            self.root.after_cancel(self.progress_animation_id)
            
        current_value = self.overall_progress['value']
        step = (target_value - current_value) / (duration / 16)  # 60 FPS
        
        def animate():
            current = self.overall_progress['value']
            if abs(current - target_value) > 0.1:
                new_value = current + step
                self.overall_progress['value'] = min(max(new_value, 0), 100)
                self.overall_label.config(text=f"{self.overall_progress['value']:.1f}%")
                self.progress_animation_id = self.root.after(16, animate)
            else:
                self.overall_progress['value'] = target_value
                self.overall_label.config(text=f"{target_value:.1f}%")
                
        animate()

    def show_loading_animation(self, message="Processing..."):
        """Show loading animation with modern design"""
        # Create loading overlay
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.destroy()
            
        self.loading_overlay = tk.Toplevel(self.root)
        self.loading_overlay.title("")
        self.loading_overlay.geometry("300x150")
        self.loading_overlay.configure(bg='#1a1a1a')
        self.loading_overlay.overrideredirect(True)
        self.loading_overlay.attributes('-topmost', True)
        
        # Center the overlay
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 150
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 75
        self.loading_overlay.geometry(f"300x150+{x}+{y}")
        
        # Loading content
        content_frame = ttk.Frame(self.loading_overlay)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Spinner animation
        spinner_label = ttk.Label(content_frame, text="⏳")
        spinner_label.pack(pady=(0, 10))
        
        # Message
        message_label = ttk.Label(content_frame, text=message)
        message_label.pack()
        
        # Animate spinner
        self._animate_spinner(spinner_label)
        
    def _animate_spinner(self, spinner_label, frame=0):
        """Animate loading spinner"""
        spinner_chars = ["⏳", "⏰", "⏱️", "⏲️"]
        spinner_label.config(text=spinner_chars[frame % len(spinner_chars)])
        if hasattr(self, 'loading_overlay') and self.loading_overlay.winfo_exists():
            self.root.after(200, lambda: self._animate_spinner(spinner_label, frame + 1))
            
    def hide_loading_animation(self):
        """Hide loading animation"""
        if hasattr(self, 'loading_overlay'):
            self.loading_overlay.destroy()
            delattr(self, 'loading_overlay')

    def show_success_notification(self, message, duration=3000):
        """Show success notification with modern design"""
        self._show_notification(message, "success", duration)
        
    def show_error_notification(self, message, duration=5000):
        """Show error notification with modern design"""
        self._show_notification(message, "error", duration)
        
    def _show_notification(self, message, type_="info", duration=3000):
        """Show notification with modern design"""
        # Create notification window
        notification = tk.Toplevel(self.root)
        notification.title("")
        notification.geometry("400x80")
        notification.configure(bg='#1a1a1a')
        notification.overrideredirect(True)
        notification.attributes('-topmost', True)
        
        # Position at top-right
        x = self.root.winfo_x() + self.root.winfo_width() - 420
        y = self.root.winfo_y() + 20
        notification.geometry(f"400x80+{x}+{y}")
        
        # Notification content
        content_frame = ttk.Frame(notification)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Icon and message
        icon_text = "✅" if type_ == "success" else "❌" if type_ == "error" else "ℹ️"
        icon_label = ttk.Label(content_frame, text=icon_text)
        icon_label.pack(side="left", padx=(10, 15))
        
        message_label = ttk.Label(content_frame, text=message, wraplength=300)
        message_label.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Close button
        close_btn = ttk.Button(content_frame, text="✕", width=3,
                              command=notification.destroy)
        close_btn.pack(side="right", padx=(0, 10))
        
        # Auto-close after duration
        notification.after(duration, notification.destroy)
        
        # Slide-in animation
        notification.withdraw()
        notification.after(100, lambda: self._slide_in_notification(notification))
        
    def _slide_in_notification(self, notification):
        """Slide in notification from right"""
        notification.deiconify()
        # Simple slide effect
        for i in range(10):
            x = self.root.winfo_x() + self.root.winfo_width() - 420 + (i * 2)
            notification.geometry(f"400x80+{x}+{self.root.winfo_y() + 20}")
            notification.update()
            self.root.after(10)

    def _create_widgets(self):
        """Create main window widgets with improved layout"""
        # Main container with modern styling
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        self.main_frame.rowconfigure(1, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)

        # Header with improved spacing
        self._create_header()

        # Content area with better organization
        self._create_content_area()

        # Status bar with modern styling
        self._create_status_bar()

    def _create_header(self):
        """Create header section with modern design"""
        header_frame = ttk.Frame(self.main_frame)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 15), padx=5)
        header_frame.columnconfigure(1, weight=1)

        # Title with icon placeholder
        title_frame = ttk.Frame(header_frame)
        title_frame.grid(row=0, column=0, sticky="w", padx=15, pady=10)
        
        # Icon placeholder (you can add actual icon later)
        icon_label = ttk.Label(title_frame, text="🎬")
        icon_label.pack(side="left", padx=(0, 10))
        
        title_label = ttk.Label(
            title_frame,
            text="TikTok Video Processing Tool")
        title_label.pack(side="left")

        # Control buttons with better spacing
        controls_frame = ttk.Frame(header_frame)
        controls_frame.grid(row=0, column=1, sticky="e", padx=15, pady=10)

        self.refresh_btn = ttk.Button(controls_frame, text="🔄 Refresh")
        self.refresh_btn.pack(side="left", padx=(0, 8))

        self.settings_btn = ttk.Button(controls_frame, text="⚙️ Settings")
        self.settings_btn.pack(side="left")

    def _create_content_area(self):
        """Create main content area with improved layout"""
        # Left panel - Video selection with card design
        self._create_video_panel()

        # Right panel - Processing and effects with card design
        self._create_processing_panel()

    def _create_video_panel(self):
        """Create video selection panel with modern card design"""
        video_frame = ttk.LabelFrame(self.main_frame, text="📁 Video Selection")
        video_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        video_frame.rowconfigure(2, weight=1)
        video_frame.columnconfigure(0, weight=1)

        # Video controls with improved layout
        controls_frame = ttk.Frame(video_frame)
        controls_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=8)

        # Left side controls
        left_controls = ttk.Frame(controls_frame)
        left_controls.pack(side="left", fill="x", expand=True)

        self.select_all_btn = ttk.Button(left_controls, text="✓ Select All")
        self.select_all_btn.pack(side="left", padx=(0, 8))

        self.clear_selection_btn = ttk.Button(left_controls, text="✗ Clear")
        self.clear_selection_btn.pack(side="left")

        # Right side search
        search_frame = ttk.Frame(controls_frame)
        search_frame.pack(side="right")

        ttk.Label(search_frame, text="🔍").pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        self.search_entry.pack(side="left")

        # Video list with improved styling
        list_frame = ttk.Frame(video_frame)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=8)
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        # Treeview for videos with better columns
        columns = ("Name", "Duration", "Size", "Status")
        self.video_tree = ttk.Treeview(list_frame, columns=columns, show="tree headings", height=15)

        # Configure columns with better widths
        self.video_tree.heading("#0", text="☐")
        self.video_tree.column("#0", width=40, minwidth=40, stretch=False)

        column_configs = {
            "Name": {"width": 250, "minwidth": 150},
            "Duration": {"width": 80, "minwidth": 60},
            "Size": {"width": 80, "minwidth": 60},
            "Status": {"width": 80, "minwidth": 60}
        }

        for col in columns:
            self.video_tree.heading(col, text=col)
            config = column_configs.get(col, {"width": 100, "minwidth": 50})
            self.video_tree.column(col, width=config["width"], minwidth=config["minwidth"])

        # Scrollbars with modern styling
        v_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.video_tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient="horizontal", command=self.video_tree.xview)

        self.video_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Grid layout
        self.video_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        # Status info with better styling
        status_frame = ttk.Frame(video_frame)
        status_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))
        
        self.video_status_label = ttk.Label(status_frame, text="📁 No videos loaded", foreground="#808080")
        self.video_status_label.pack(side="left", padx=10, pady=5)

    def _create_processing_panel(self):
        """Create processing panel with modern card design"""
        processing_frame = ttk.LabelFrame(self.main_frame, text="⚡ Processing & Effects")
        processing_frame.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        processing_frame.rowconfigure(2, weight=1)
        processing_frame.columnconfigure(0, weight=1)

        # Effects configuration with improved layout
        self._create_effects_section(processing_frame)

        # Processing controls with better organization
        self._create_processing_controls(processing_frame)

        # Processing queue with modern design
        self._create_processing_queue(processing_frame)

    def _create_effects_section(self, parent):
        """Create effects configuration section with modern styling"""
        effects_frame = ttk.LabelFrame(parent, text="🎨 Effects Configuration")
        effects_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        effects_frame.columnconfigure(1, weight=1)

        # Opening Effects Section
        opening_frame = ttk.LabelFrame(effects_frame, text="🎬 Opening Effects")
        opening_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        opening_frame.columnconfigure(1, weight=1)

        # Effect type
        ttk.Label(opening_frame, text="Effect Type:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.effect_var = tk.StringVar(value="none")
        self.effect_combo = ttk.Combobox(opening_frame, textvariable=self.effect_var, 
                                        state="readonly")
        self.effect_combo.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        # Duration
        ttk.Label(opening_frame, text="Duration (s):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.duration_var = tk.StringVar(value="2.0")
        duration_spin = ttk.Spinbox(opening_frame, from_=0.5, to=10.0, increment=0.5, 
                                   textvariable=self.duration_var)
        duration_spin.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        # Random effect
        self.random_effect_var = tk.BooleanVar()
        random_check = ttk.Checkbutton(opening_frame, text="🎲 Use Random Effects", 
                                      variable=self.random_effect_var)
        random_check.grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=2)

        # GIF Effects Section
        gif_frame = ttk.LabelFrame(effects_frame, text="🎭 GIF Effects")
        gif_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        gif_frame.columnconfigure(1, weight=1)

        # GIF selection
        ttk.Label(gif_frame, text="GIF Effect:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.gif_var = tk.StringVar(value="none")
        self.gif_combo = ttk.Combobox(gif_frame, textvariable=self.gif_var, 
                                     state="readonly")
        self.gif_combo.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        # Random GIF
        self.random_gif_var = tk.BooleanVar()
        random_gif_check = ttk.Checkbutton(gif_frame, text="🎲 Use Random GIF", 
                                          variable=self.random_gif_var)
        random_gif_check.grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=2)

    def _create_processing_controls(self, parent):
        """Create processing control buttons"""
        controls_frame = ttk.Frame(parent)
        controls_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        self.start_processing_btn = ttk.Button(controls_frame, text="▶️ Start Processing")
        self.start_processing_btn.pack(side="left", padx=(0, 5))

        self.pause_processing_btn = ttk.Button(controls_frame, text="⏸️ Pause", state="disabled")
        self.pause_processing_btn.pack(side="left", padx=(0, 5))

        self.stop_processing_btn = ttk.Button(controls_frame, text="⏹️ Stop", state="disabled")
        self.stop_processing_btn.pack(side="left")

        # Progress bar with better styling
        self.overall_progress = ttk.Progressbar(controls_frame, mode="determinate")
        self.overall_progress.pack(side="right", fill="x", expand=True, padx=(10, 0))

    def _create_processing_queue(self, parent):
        """Create processing queue display with modern styling"""
        queue_frame = ttk.LabelFrame(parent, text="📋 Processing Queue")
        queue_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        queue_frame.rowconfigure(0, weight=1)
        queue_frame.columnconfigure(0, weight=1)

        # Queue treeview with better column headers
        queue_columns = ("Video", "Status", "Progress", "Time")
        self.queue_tree = ttk.Treeview(queue_frame, columns=queue_columns, show="headings", height=6)

        # Configure columns with better headers and widths
        column_configs = [
            ("Video", "🎬 Video", 200),
            ("Status", "📊 Status", 120),
            ("Progress", "📈 Progress", 100),
            ("Time", "⏱️ Time", 100)
        ]
        
        for col, header, width in column_configs:
            self.queue_tree.heading(col, text=header)
            self.queue_tree.column(col, width=width, minwidth=80)

        # Scrollbar for queue
        queue_scrollbar = ttk.Scrollbar(queue_frame, orient="vertical", command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=queue_scrollbar.set)

        self.queue_tree.grid(row=0, column=0, sticky="nsew")
        queue_scrollbar.grid(row=0, column=1, sticky="ns")

    def _create_status_bar(self):
        """Create status bar with modern styling"""
        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0), padx=5)

        # Status indicator with icon
        status_container = ttk.Frame(self.status_frame)
        status_container.pack(side="left", padx=10, pady=5)
        
        self.status_icon = ttk.Label(status_container, text="✅")
        self.status_icon.pack(side="left", padx=(0, 5))
        
        self.status_label = ttk.Label(status_container, text="Ready")
        self.status_label.pack(side="left")

        # Statistics with better formatting
        stats_container = ttk.Frame(self.status_frame)
        stats_container.pack(side="right", padx=10, pady=5)
        
        self.stats_label = ttk.Label(stats_container, text="")
        self.stats_label.pack(side="right")

    def _setup_styles(self):
        """Setup custom styles with modern design"""
        style = ttk.Style()
        
        # Modern color palette with better contrast
        colors = {
            'bg_primary': '#1e1e1e',      # Darker background
            'bg_secondary': '#2d2d2d',    # Card backgrounds
            'bg_tertiary': '#3d3d3d',     # Input fields
            'accent_primary': '#007acc',   # Blue accent
            'accent_secondary': '#00b4d8', # Light blue
            'accent_success': '#28a745',   # Green
            'accent_warning': '#ffc107',   # Yellow
            'accent_error': '#dc3545',     # Red
            'text_primary': '#ffffff',     # White text
            'text_secondary': '#b0b0b0',   # Light gray text
            'text_muted': '#808080',       # Muted text
            'border': '#404040',           # Borders
            'hover': '#4a4a4a',            # Hover state
            'active': '#5a5a5a'            # Active state
        }
        
        # Configure modern dark theme
        style.theme_use('clam')  # Use clam as base for better customization
        
        # Main window background
        style.configure("Main.TFrame", background=colors['bg_primary'])
        style.configure("Main.TLabel", 
                       background=colors['bg_primary'], 
                       foreground=colors['text_primary'])
        
        # Header styling with accent
        style.configure("Header.TLabel", 
                       background=colors['bg_primary'],
                       foreground=colors['accent_primary'])
        
        # Card styling with better contrast
        style.configure("Card.TFrame", 
                       background=colors['bg_secondary'],
                       relief="flat",
                       borderwidth=1)
        
        style.configure("Card.TLabelFrame", 
                       background=colors['bg_secondary'],
                       foreground=colors['text_primary'],
                       relief="flat",
                       borderwidth=1)
        
        style.configure("Card.TLabelFrame.Label", 
                       background=colors['bg_secondary'],
                       foreground=colors['accent_primary'])
        
        # Button styling with modern design
        style.configure("Primary.TButton",
                       background=colors['accent_primary'],
                       foreground=colors['text_primary'],
                       relief="flat",
                       borderwidth=0,
                       padding=(12, 6))
        
        style.map("Primary.TButton",
                 background=[("active", colors['accent_secondary']),
                           ("pressed", colors['accent_secondary'])])
        
        style.configure("Secondary.TButton",
                       background=colors['bg_tertiary'],
                       foreground=colors['text_primary'],
                       relief="flat",
                       borderwidth=0,
                       padding=(10, 5))
        
        style.map("Secondary.TButton",
                 background=[("active", colors['hover']),
                           ("pressed", colors['active'])])
        
        # Success button for processing
        style.configure("Success.TButton",
                       background=colors['accent_success'],
                       foreground=colors['text_primary'],
                       relief="flat",
                       borderwidth=0,
                       padding=(12, 6))
        
        style.map("Success.TButton",
                 background=[("active", "#218838"),
                           ("pressed", "#1e7e34")])
        
        # Treeview styling with better contrast
        style.configure("Treeview",
                       background=colors['bg_tertiary'],
                       foreground=colors['text_primary'],
                       fieldbackground=colors['bg_tertiary'],
                       rowheight=25)
        
        style.configure("Treeview.Heading",
                       background=colors['bg_secondary'],
                       foreground=colors['text_primary'],
                       relief="flat")
        
        style.map("Treeview",
                 background=[("selected", colors['accent_primary'])],
                 foreground=[("selected", colors['text_primary'])])
        
        # Progress bar styling
        style.configure("Custom.Horizontal.TProgressbar",
                       background=colors['accent_primary'],
                       troughcolor=colors['bg_tertiary'],
                       borderwidth=0,
                       lightcolor=colors['accent_primary'],
                       darkcolor=colors['accent_primary'])
        
        # Entry styling
        style.configure("Custom.TEntry",
                       fieldbackground=colors['bg_tertiary'],
                       foreground=colors['text_primary'],
                       borderwidth=1,
                       relief="flat")
        
        # Combobox styling
        style.configure("Custom.TCombobox",
                       fieldbackground=colors['bg_tertiary'],
                       foreground=colors['text_primary'],
                       background=colors['bg_tertiary'],
                       borderwidth=1,
                       relief="flat")
        
        # Status indicators
        style.configure("Success.TLabel",
                       background=colors['accent_success'],
                       foreground=colors['text_primary'])
        
        style.configure("Warning.TLabel",
                       background=colors['accent_warning'],
                       foreground=colors['bg_primary'])
        
        style.configure("Error.TLabel",
                       background=colors['accent_error'],
                       foreground=colors['text_primary'])
        
        # Apply styles to main window
        self.root.configure(bg=colors['bg_primary'])
        self.main_frame.configure()

    # BaseView interface implementation
    def show_error(self, message: str) -> None:
        """Show error message with modern notification"""
        self.show_error_notification(message)
        # Update status bar
        self.status_icon.config(text="❌")
        self.status_label.config(text="Error")

    def show_success(self, message: str) -> None:
        """Show success message with modern notification"""
        self.show_success_notification(message)
        # Update status bar
        self.status_icon.config(text="✅")
        self.status_label.config(text="Success")

    def show_loading(self, message: str = "Loading...") -> None:
        """Show loading indicator with modern design"""
        self.show_loading_animation(message)
        # Update status bar
        self.status_icon.config(text="⏳")
        self.status_label.config(text=message)
        self.root.update_idletasks()

    def hide_loading(self) -> None:
        """Hide loading indicator"""
        self.hide_loading_animation()
        # Update status bar
        self.status_icon.config(text="✅")
        self.status_label.config(text="Ready")

    def update_ui(self) -> None:
        """Update UI elements"""
        self.root.update_idletasks()

    # Video list management
    def update_video_list(self, videos: List[VideoDTO]) -> None:
        """Update video list display with better formatting"""
        # Clear existing items
        for item in self.video_tree.get_children():
            self.video_tree.delete(item)

        # Add videos with better status display
        for video in videos:
            # Format status with icon
            status = "✅ Cached" if video.is_cached() else "🆕 New"
            
            values = (
                video.filename,
                FormatHelper.format_duration(video.duration),
                FormatHelper.format_file_size(video.file_size or 0),
                status
            )

            item = self.video_tree.insert("", "end", values=values, tags=(video.path))
            
            # Update status label
            if videos:
                total_duration = sum(v.duration for v in videos)
                self.video_status_label.config(
                    text=f"📁 {len(videos)} videos loaded • Total: {FormatHelper.format_duration(total_duration)}",
                    foreground="#b0b0b0"
                )
            else:
                self.video_status_label.config(
                    text="📁 No videos loaded",
                    foreground="#808080"
                )

    def get_selected_videos(self) -> List[str]:
        """Get list of selected video paths"""
        selected = []
        for item in self.video_tree.selection():
            tags = self.video_tree.item(item, "tags")
            if tags:
                selected.append(tags[0])
        return selected

    # Effects management
    def update_effect_options(self, effects: List[str]) -> None:
        """Update available effect options"""
        self.effect_combo['values'] = effects

    def get_selected_effect(self) -> str:
        """Get selected effect type"""
        return self.effect_var.get()

    def update_gif_options(self, gifs: List[str]) -> None:
        """Update available GIF options"""
        self.gif_combo['values'] = gifs

    def get_selected_gif(self) -> str:
        """Get selected GIF effect"""
        return self.gif_var.get()

    def is_random_gif_enabled(self) -> bool:
        """Check if random GIF is enabled"""
        return self.random_gif_var.get()

    def get_effect_duration(self) -> float:
        """Get effect duration"""
        try:
            return float(self.duration_var.get())
        except ValueError:
            return 2.0

    def is_random_effects_enabled(self) -> bool:
        """Check if random effects is enabled"""
        return self.random_effect_var.get()

    # Processing queue management
    def update_processing_queue(self, jobs: List[ProcessingJobDTO]) -> None:
        """Update processing queue display with better formatting"""
        # Clear existing items
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)

        # Add jobs with better status display
        for job in jobs:
            # Format status with icons
            status_icons = {
                "queued": "⏳ Queued",
                "processing": "⚡ Processing", 
                "completed": "✅ Completed",
                "failed": "❌ Failed",
                "cancelled": "🚫 Cancelled"
            }
            
            status = status_icons.get(job.status.lower(), job.status.title())
            
            values = (
                job.main_video_name,
                status,
                f"{job.progress:.1f}%",
                FormatHelper.format_duration(job.actual_duration or 0)
            )

            self.queue_tree.insert("", "end", values=values, tags=(job.id, job.status))

    def update_overall_progress(self, progress: float) -> None:
        """Update overall progress bar"""
        self.overall_progress['value'] = progress

    def update_statistics(self, stats_text: str) -> None:
        """Update statistics display with better formatting"""
        # Format statistics with icons
        formatted_stats = f"📊 {stats_text}"
        self.stats_label.config(text=formatted_stats)

    def _setup_responsive_design(self):
        """Setup responsive design features"""
        # Bind resize events
        self.root.bind('<Configure>', self._on_window_resize)
        
        # Store original widget sizes for responsive scaling
        self.original_sizes = {}
        
        # Responsive breakpoints
        self.breakpoints = {
            'small': 1000,
            'medium': 1200,
            'large': 1400
        }

    def _on_window_resize(self, event):
        """Handle window resize for responsive design"""
        if event.widget == self.root:
            width = event.width
            height = event.height
            
            # Determine current breakpoint
            current_breakpoint = 'large'
            for breakpoint, min_width in self.breakpoints.items():
                if width < min_width:
                    current_breakpoint = breakpoint
                    break
            
            # Apply responsive adjustments
            self._apply_responsive_layout(current_breakpoint, width, height)

    def _apply_responsive_layout(self, breakpoint, width, height):
        """Apply responsive layout based on breakpoint"""
        # Adjust font sizes
        font_scales = {
            'small': 0.8,
            'medium': 0.9,
            'large': 1.0
        }
        
        scale = font_scales.get(breakpoint, 1.0)
        
        # Adjust column widths for video tree
        if hasattr(self, 'video_tree'):
            column_widths = {
                'small': {"Name": 180, "Duration": 60, "Size": 60, "Status": 60},
                'medium': {"Name": 220, "Duration": 70, "Size": 70, "Status": 70},
                'large': {"Name": 250, "Duration": 80, "Size": 80, "Status": 80}
            }
            
            widths = column_widths.get(breakpoint, column_widths['large'])
            for col, width_val in widths.items():
                self.video_tree.column(col, width=width_val)

    def _setup_accessibility(self):
        """Setup accessibility features"""
        # Add keyboard shortcuts
        self.root.bind('<Control-r>', lambda e: self._on_refresh_videos())
        self.root.bind('<Control-s>', lambda e: self._on_start_processing())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        self.root.bind('<F5>', lambda e: self._on_refresh_videos())
        
        # Add tooltips for better accessibility
        self._setup_tooltips()
        
        # High contrast mode support
        self.high_contrast_mode = False
        self.root.bind('<Control-h>', lambda e: self._toggle_high_contrast())

    def _setup_tooltips(self):
        """Setup tooltips for better accessibility"""
        tooltips = {
            'refresh_btn': 'Refresh video list (Ctrl+R)',
            'start_processing_btn': 'Start processing selected videos (Ctrl+S)',
            'select_all_btn': 'Select all videos in the list',
            'clear_selection_btn': 'Clear current selection',
            'search_entry': 'Search videos by filename'
        }
        
        # Apply tooltips after widgets are created
        self.root.after(100, lambda: self._apply_tooltips(tooltips))

    def _apply_tooltips(self, tooltips):
        """Apply tooltips to widgets"""
        for widget_name, tooltip_text in tooltips.items():
            if hasattr(self, widget_name):
                widget = getattr(self, widget_name)
                self._create_tooltip(widget, tooltip_text)

    def _create_tooltip(self, widget, text):
        """Create tooltip for widget"""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = ttk.Label(tooltip, text=text,
                             background='#2d2d2d', relief='solid', borderwidth=1)
            label.pack()
            
            def hide_tooltip():
                tooltip.destroy()
            
            widget.tooltip = tooltip
            widget.bind('<Leave>', lambda e: hide_tooltip())
            widget.bind('<Button-1>', lambda e: hide_tooltip())
        
        widget.bind('<Enter>', show_tooltip)

    def _toggle_high_contrast(self):
        """Toggle high contrast mode"""
        self.high_contrast_mode = not self.high_contrast_mode
        
        if self.high_contrast_mode:
            # Apply high contrast colors
            style = ttk.Style()
            style.configure("Main.TLabel", 
                           background="#000000", 
                           foreground="#ffffff")
            style.configure("Card.TFrame", 
                           background="#000000")
            style.configure("Primary.TButton",
                           background="#ffffff",
                           foreground="#000000")
        else:
            # Restore normal colors
            self._setup_styles()


class MainWindowPresenter(BasePresenter):
    """Presenter for main window"""

    def __init__(self, view: MainWindowView, video_service: VideoService,
                 processing_service: ProcessingService, effect_service: EffectService,
                 get_videos_use_case: GetVideosUseCase, process_video_use_case: ProcessVideoUseCase,
                 config: AppConfig):
        """
        Initialize presenter.

        Args:
            view: Main window view
            video_service: Video service
            processing_service: Processing service
            effect_service: Effect service
            get_videos_use_case: Get videos use case
            process_video_use_case: Process video use case
            config: Application configuration
        """
        super().__init__(view)
        self.video_service = video_service
        self.processing_service = processing_service
        self.effect_service = effect_service
        self.get_videos_use_case = get_videos_use_case
        self.process_video_use_case = process_video_use_case
        self.config = config

        self._current_videos: List[VideoDTO] = []
        self._setup_event_handlers()

    def initialize(self) -> None:
        """Initialize presenter"""
        self._load_videos()
        self._load_effects()
        self._start_queue_monitoring()

    def _setup_event_handlers(self) -> None:
        """Setup UI event handlers"""
        # Button handlers
        self.view.refresh_btn.config(command=self._on_refresh_videos)
        self.view.start_processing_btn.config(command=self._on_start_processing)
        self.view.stop_processing_btn.config(command=self._on_stop_processing)
        self.view.select_all_btn.config(command=self._on_select_all)
        self.view.clear_selection_btn.config(command=self._on_clear_selection)

    def _load_videos(self) -> None:
        """Load videos from configured directory"""
        def load_operation():
            request = GetVideosRequest(refresh_cache=False)
            response = self.get_videos_use_case.execute(request)
            return response

        def on_success(response):
            if response.success:
                self._current_videos = response.videos
                self.view.update_video_list(response.videos)

                # Update statistics
                stats_text = f"Videos: {response.total_count} | Duration: {FormatHelper.format_duration(response.total_duration)}"
                self.view.update_statistics(stats_text)
            else:
                self.view.show_error(response.error_message or "Failed to load videos")

        self.execute_async(load_operation, on_success, loading_message="Loading videos...")

    def _load_effects(self) -> None:
        """Load available effects"""
        try:
            # Load opening effects
            available_effects = self.effect_service.get_available_effects()
            effect_names = [effect.value for effect in available_effects]
            self.view.update_effect_options(effect_names)
            
            # Load GIF effects
            self._load_gif_effects()
        except Exception as e:
            self.handle_error(e, "loading effects")

    def _load_gif_effects(self) -> None:
        """Load available GIF effects"""
        try:
            import glob
            from pathlib import Path
            
            # Get GIF files from effects directory
            effects_dir = self.config.paths.effects_dir if hasattr(self.config.paths, 'effects_dir') else Path("effects")
            gif_files = glob.glob(str(effects_dir / "*.gif"))
            
            # Extract filenames
            gif_names = ["none"] + [Path(gif).name for gif in gif_files]
            self.view.update_gif_options(gif_names)
            
            logger.info(f"Loaded {len(gif_files)} GIF effects")
        except Exception as e:
            logger.error(f"Error loading GIF effects: {e}")
            self.view.update_gif_options(["none"])

    def _start_queue_monitoring(self) -> None:
        """Start monitoring processing queue"""
        def update_queue():
            try:
                jobs = self.processing_service.get_all_jobs()
                job_dtos = [ProcessingJobDTO.from_entity(job) for job in jobs]
                self.view.update_processing_queue(job_dtos)

                # Update overall progress
                queue_status = self.processing_service.get_queue_status()
                if queue_status['total_jobs'] > 0:
                    completed = queue_status['completed_count']
                    total = queue_status['total_jobs']
                    progress = (completed / total) * 100
                    self.view.update_overall_progress(progress)

            except Exception as e:
                logger.error(f"Error updating queue display: {e}")

            # Schedule next update
            self.view.root.after(1000, update_queue)  # Update every second

        # Start monitoring
        update_queue()

    def _on_refresh_videos(self) -> None:
        """Handle refresh videos button"""
        def refresh_operation():
            request = GetVideosRequest(refresh_cache=True)
            response = self.get_videos_use_case.execute(request)
            return response

        def on_success(response):
            if response.success:
                self._current_videos = response.videos
                self.view.update_video_list(response.videos)
                self.view.show_success(f"Refreshed {response.total_count} videos")
            else:
                self.view.show_error(response.error_message or "Failed to refresh videos")

        self.execute_async(refresh_operation, on_success, loading_message="Refreshing videos...")

    def _on_start_processing(self) -> None:
        """Handle start processing button"""
        try:
            selected_paths = self.view.get_selected_videos()
            if not selected_paths:
                self.view.show_error("Please select videos to process")
                return

            # Get background videos
            background_videos = self.video_service.get_background_videos()
            if not background_videos:
                self.view.show_error("No background videos found")
                return

            # Create and submit processing jobs
            import random
            from ...domain.entities.processing_job import ProcessingJob
            from ...domain.entities.video import Video
            from ...domain.entities.effect import Effect
            from ...domain.value_objects.effect_type import EffectType
            from ...application.services.processing_service import JobProgressCallback
            
            jobs_submitted = 0
            
            for video_path in selected_paths:
                # Find video DTO
                video_dto = next((v for v in self._current_videos if str(v.path) == str(video_path)), None)
                if not video_dto:
                    logger.warning(f"Video DTO not found for path: {video_path}")
                    continue

                # Select random background
                bg_video = random.choice(background_videos)

                # Create unique output path with timestamp
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename_without_ext = Path(video_dto.filename).stem
                output_path = self.config.paths.output_dir / f"processed_{filename_without_ext}_{timestamp}.mp4"

                # Create Video entities
                main_video = Video(
                    path=Path(video_path),
                    duration=video_dto.duration,
                    dimensions=video_dto.dimensions
                )
                
                background_video = Video(
                    path=bg_video.path,
                    duration=bg_video.duration,
                    dimensions=bg_video.dimensions
                )

                # Create effects
                effects = []
                
                # Add opening effect
                if self.view.is_random_effects_enabled():
                    effect_dto = self.effect_service.create_random_effect()
                    effect = Effect(
                        type=effect_dto.type,
                        duration=effect_dto.duration,
                        parameters=effect_dto.parameters
                    )
                    effects.append(effect)
                else:
                    effect_type_str = self.view.get_selected_effect()
                    if effect_type_str != "none":
                        # Convert string to EffectType enum
                        effect_type = EffectType(effect_type_str)
                        effect = Effect(
                            type=effect_type,
                            duration=self.view.get_effect_duration(),
                            parameters={}
                        )
                        effects.append(effect)

                # Add GIF effect
                gif_path = self._get_selected_gif_path()
                if gif_path:
                    # Create a GIF overlay effect (use video duration or default to 10 seconds)
                    gif_duration = video_dto.duration if video_dto.duration > 0 else 10.0
                    gif_effect = Effect(
                        type=EffectType.GIF_OVERLAY,
                        duration=gif_duration,  # Use video duration for GIF overlay
                        parameters={'gif_path': str(gif_path)}
                    )
                    effects.append(gif_effect)

                # Create processing job
                job = ProcessingJob(
                    main_video=main_video,
                    background_video=background_video,
                    effects=effects,
                    output_path=output_path
                )

                # Create progress callback
                callback = JobProgressCallback(
                    on_progress=lambda job_id, progress: self._on_job_progress(job_id, progress),
                    on_status_change=lambda job_id, status: self._on_job_status_change(job_id, status),
                    on_complete=lambda job_id, success: self._on_job_complete(job_id, success)
                )

                # Submit job to processing service
                job_id = self.processing_service.submit_job(job, callback)
                jobs_submitted += 1
                logger.info(f"Submitted job {job_id} for video {video_dto.filename}")

            if jobs_submitted > 0:
                self.view.show_success(f"Processing started - {jobs_submitted} job(s) queued")
                # Start queue monitoring
                self._start_queue_monitoring()
            else:
                self.view.show_error("No jobs were created")

        except Exception as e:
            self.handle_error(e, "starting processing")

    def _on_stop_processing(self) -> None:
        """Handle stop processing button"""
        try:
            self.processing_service.stop_processing()
            self.view.show_success("Processing stopped")
        except Exception as e:
            self.handle_error(e, "stopping processing")

    def _on_select_all(self) -> None:
        """Handle select all button"""
        for item in self.view.video_tree.get_children():
            self.view.video_tree.selection_add(item)

    def _on_clear_selection(self) -> None:
        """Handle clear selection button"""
        self.view.video_tree.selection_remove(self.view.video_tree.selection())

    def _on_job_progress(self, job_id: str, progress: float) -> None:
        """Handle job progress update"""
        try:
            # Update progress in the UI (this would update progress bars)
            logger.debug(f"Job {job_id} progress: {progress}%")
            # TODO: Update progress widget with job progress
        except Exception as e:
            logger.error(f"Error updating job progress: {e}")

    def _on_job_status_change(self, job_id: str, status) -> None:
        """Handle job status change"""
        try:
            logger.info(f"Job {job_id} status changed to: {status}")
            # TODO: Update progress widget with job status
        except Exception as e:
            logger.error(f"Error updating job status: {e}")

    def _on_job_complete(self, job_id: str, success: bool) -> None:
        """Handle job completion"""
        try:
            if success:
                logger.info(f"Job {job_id} completed successfully")
                # TODO: Update UI to show completion
            else:
                logger.error(f"Job {job_id} failed")
                # TODO: Update UI to show failure
        except Exception as e:
            logger.error(f"Error handling job completion: {e}")

    def _get_selected_gif_path(self) -> Optional[Path]:
        """Get the path to the selected GIF effect"""
        try:
            if self.view.is_random_gif_enabled():
                # Select random GIF
                import glob
                from pathlib import Path
                effects_dir = self.config.paths.effects_dir if hasattr(self.config.paths, 'effects_dir') else Path("effects")
                gif_files = glob.glob(str(effects_dir / "*.gif"))
                if gif_files:
                    import random
                    return Path(random.choice(gif_files))
            else:
                # Get selected GIF
                selected_gif = self.view.get_selected_gif()
                if selected_gif != "none":
                    effects_dir = self.config.paths.effects_dir if hasattr(self.config.paths, 'effects_dir') else Path("effects")
                    return effects_dir / selected_gif
            return None
        except Exception as e:
            logger.error(f"Error getting selected GIF path: {e}")
            return None
