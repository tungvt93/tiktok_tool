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
        """Setup main window properties"""
        self.root.title("TikTok Video Processing Tool - Clean Architecture")
        self.root.geometry("1400x800")
        self.root.configure(bg='#2b2b2b')

        # Make window resizable
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

    def _create_widgets(self):
        """Create main window widgets"""
        # Main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.main_frame.rowconfigure(1, weight=1)
        self.main_frame.columnconfigure(1, weight=1)

        # Header
        self._create_header()

        # Content area
        self._create_content_area()

        # Status bar
        self._create_status_bar()

    def _create_header(self):
        """Create header section"""
        header_frame = ttk.Frame(self.main_frame)
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # Title
        title_label = ttk.Label(
            header_frame,
            text="TikTok Video Processing Tool",
            font=("Arial", 16, "bold")
        )
        title_label.pack(side="left")

        # Control buttons
        controls_frame = ttk.Frame(header_frame)
        controls_frame.pack(side="right")

        self.refresh_btn = ttk.Button(controls_frame, text="Refresh Videos")
        self.refresh_btn.pack(side="left", padx=(0, 5))

        self.settings_btn = ttk.Button(controls_frame, text="Settings")
        self.settings_btn.pack(side="left")

    def _create_content_area(self):
        """Create main content area"""
        # Left panel - Video selection
        self._create_video_panel()

        # Right panel - Processing and effects
        self._create_processing_panel()

    def _create_video_panel(self):
        """Create video selection panel"""
        video_frame = ttk.LabelFrame(self.main_frame, text="Video Selection")
        video_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        video_frame.rowconfigure(1, weight=1)
        video_frame.columnconfigure(0, weight=1)

        # Video controls
        controls_frame = ttk.Frame(video_frame)
        controls_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        self.select_all_btn = ttk.Button(controls_frame, text="Select All")
        self.select_all_btn.pack(side="left", padx=(0, 5))

        self.clear_selection_btn = ttk.Button(controls_frame, text="Clear Selection")
        self.clear_selection_btn.pack(side="left")

        # Video list
        list_frame = ttk.Frame(video_frame)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        # Treeview for videos
        columns = ("Name", "Duration", "Size", "Status")
        self.video_tree = ttk.Treeview(list_frame, columns=columns, show="tree headings")

        # Configure columns
        self.video_tree.heading("#0", text="Select")
        self.video_tree.column("#0", width=60, minwidth=60)

        for col in columns:
            self.video_tree.heading(col, text=col)
            self.video_tree.column(col, width=100)

        # Scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.video_tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient="horizontal", command=self.video_tree.xview)

        self.video_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Grid layout
        self.video_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

    def _create_processing_panel(self):
        """Create processing panel"""
        processing_frame = ttk.LabelFrame(self.main_frame, text="Processing")
        processing_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        processing_frame.rowconfigure(2, weight=1)
        processing_frame.columnconfigure(0, weight=1)

        # Effects configuration
        self._create_effects_section(processing_frame)

        # Processing controls
        self._create_processing_controls(processing_frame)

        # Processing queue
        self._create_processing_queue(processing_frame)

    def _create_effects_section(self, parent):
        """Create effects configuration section"""
        effects_frame = ttk.LabelFrame(parent, text="Effects Configuration")
        effects_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        effects_frame.columnconfigure(1, weight=1)

        # Effect type
        ttk.Label(effects_frame, text="Effect Type:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.effect_var = tk.StringVar(value="none")
        self.effect_combo = ttk.Combobox(effects_frame, textvariable=self.effect_var, state="readonly")
        self.effect_combo.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        # Duration
        ttk.Label(effects_frame, text="Duration (s):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.duration_var = tk.StringVar(value="2.0")
        duration_spin = ttk.Spinbox(effects_frame, from_=0.5, to=10.0, increment=0.5, textvariable=self.duration_var)
        duration_spin.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        # Random effect
        self.random_effect_var = tk.BooleanVar()
        random_check = ttk.Checkbutton(effects_frame, text="Use Random Effects", variable=self.random_effect_var)
        random_check.grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=2)

    def _create_processing_controls(self, parent):
        """Create processing control buttons"""
        controls_frame = ttk.Frame(parent)
        controls_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

        self.start_processing_btn = ttk.Button(controls_frame, text="Start Processing")
        self.start_processing_btn.pack(side="left", padx=(0, 5))

        self.pause_processing_btn = ttk.Button(controls_frame, text="Pause", state="disabled")
        self.pause_processing_btn.pack(side="left", padx=(0, 5))

        self.stop_processing_btn = ttk.Button(controls_frame, text="Stop", state="disabled")
        self.stop_processing_btn.pack(side="left")

        # Progress bar
        self.overall_progress = ttk.Progressbar(controls_frame, mode="determinate")
        self.overall_progress.pack(side="right", fill="x", expand=True, padx=(10, 0))

    def _create_processing_queue(self, parent):
        """Create processing queue display"""
        queue_frame = ttk.LabelFrame(parent, text="Processing Queue")
        queue_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)
        queue_frame.rowconfigure(0, weight=1)
        queue_frame.columnconfigure(0, weight=1)

        # Queue treeview
        queue_columns = ("Video", "Status", "Progress", "Time")
        self.queue_tree = ttk.Treeview(queue_frame, columns=queue_columns, show="headings")

        for col in queue_columns:
            self.queue_tree.heading(col, text=col)
            self.queue_tree.column(col, width=100)

        # Scrollbar for queue
        queue_scrollbar = ttk.Scrollbar(queue_frame, orient="vertical", command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=queue_scrollbar.set)

        self.queue_tree.grid(row=0, column=0, sticky="nsew")
        queue_scrollbar.grid(row=0, column=1, sticky="ns")

    def _create_status_bar(self):
        """Create status bar"""
        self.status_frame = ttk.Frame(self.main_frame)
        self.status_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        self.status_label = ttk.Label(self.status_frame, text="Ready")
        self.status_label.pack(side="left")

        # Statistics
        self.stats_label = ttk.Label(self.status_frame, text="")
        self.stats_label.pack(side="right")

    def _setup_styles(self):
        """Setup custom styles"""
        style = ttk.Style()

        # Configure dark theme colors
        style.configure("TLabel", background="#2b2b2b", foreground="white")
        style.configure("TFrame", background="#2b2b2b")
        style.configure("TLabelFrame", background="#2b2b2b", foreground="white")
        style.configure("TButton", background="#404040", foreground="white")
        style.map("TButton", background=[("active", "#505050")])

    # BaseView interface implementation
    def show_error(self, message: str) -> None:
        """Show error message"""
        MessageBoxHelper.show_error("Error", message)

    def show_success(self, message: str) -> None:
        """Show success message"""
        MessageBoxHelper.show_info("Success", message)

    def show_loading(self, message: str = "Loading...") -> None:
        """Show loading indicator"""
        self.status_label.config(text=message)
        self.root.update_idletasks()

    def hide_loading(self) -> None:
        """Hide loading indicator"""
        self.status_label.config(text="Ready")

    def update_ui(self) -> None:
        """Update UI elements"""
        self.root.update_idletasks()

    # Video list management
    def update_video_list(self, videos: List[VideoDTO]) -> None:
        """Update video list display"""
        # Clear existing items
        for item in self.video_tree.get_children():
            self.video_tree.delete(item)

        # Add videos
        for video in videos:
            values = (
                video.filename,
                FormatHelper.format_duration(video.duration),
                FormatHelper.format_file_size(video.file_size or 0),
                "Cached" if video.is_cached() else "New"
            )

            item = self.video_tree.insert("", "end", values=values, tags=(video.path,))

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
        """Update processing queue display"""
        # Clear existing items
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)

        # Add jobs
        for job in jobs:
            values = (
                job.main_video_name,
                job.status.title(),
                f"{job.progress:.1f}%",
                FormatHelper.format_duration(job.actual_duration or 0)
            )

            self.queue_tree.insert("", "end", values=values, tags=(job.id,))

    def update_overall_progress(self, progress: float) -> None:
        """Update overall progress bar"""
        self.overall_progress['value'] = progress

    def update_statistics(self, stats_text: str) -> None:
        """Update statistics display"""
        self.stats_label.config(text=stats_text)


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
            available_effects = self.effect_service.get_available_effects()
            effect_names = [effect.value for effect in available_effects]
            self.view.update_effect_options(effect_names)
        except Exception as e:
            self.handle_error(e, "loading effects")

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

            # Create processing jobs
            import random
            for video_path in selected_paths:
                # Find video DTO
                video_dto = next((v for v in self._current_videos if v.path == video_path), None)
                if not video_dto:
                    continue

                # Select random background
                bg_video = random.choice(background_videos)

                # Create output path
                output_path = self.config.paths.output_dir / f"processed_{video_dto.filename}"

                # Create effects
                effects = []
                if self.view.is_random_effects_enabled():
                    effect = self.effect_service.create_random_effect()
                    effects.append({
                        'type': effect.type.value,
                        'duration': effect.duration,
                        'parameters': effect.parameters
                    })
                else:
                    effect_type = self.view.get_selected_effect()
                    if effect_type != "none":
                        effects.append({
                            'type': effect_type,
                            'duration': self.view.get_effect_duration(),
                            'parameters': {}
                        })

                # Create and submit job
                request = ProcessVideoRequest(
                    main_video_path=Path(video_path),
                    background_video_path=bg_video.path,
                    output_path=output_path,
                    effects=effects
                )

                # Execute processing (this would be async in real implementation)
                response = self.process_video_use_case.execute(request)
                if not response.success:
                    self.view.show_error(f"Failed to process {video_dto.filename}: {response.error_message}")

            self.view.show_success("Processing started")

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
