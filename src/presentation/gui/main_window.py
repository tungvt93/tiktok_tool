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

        # Opening Effects Section
        opening_frame = ttk.LabelFrame(effects_frame, text="Opening Effects")
        opening_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        opening_frame.columnconfigure(1, weight=1)

        # Effect type
        ttk.Label(opening_frame, text="Effect Type:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.effect_var = tk.StringVar(value="none")
        self.effect_combo = ttk.Combobox(opening_frame, textvariable=self.effect_var, state="readonly")
        self.effect_combo.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        # Duration
        ttk.Label(opening_frame, text="Duration (s):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.duration_var = tk.StringVar(value="2.0")
        duration_spin = ttk.Spinbox(opening_frame, from_=0.5, to=10.0, increment=0.5, textvariable=self.duration_var)
        duration_spin.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        # Random effect
        self.random_effect_var = tk.BooleanVar()
        random_check = ttk.Checkbutton(opening_frame, text="Use Random Effects", variable=self.random_effect_var)
        random_check.grid(row=2, column=0, columnspan=2, sticky="w", padx=5, pady=2)

        # GIF Effects Section
        gif_frame = ttk.LabelFrame(effects_frame, text="GIF Effects")
        gif_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        gif_frame.columnconfigure(1, weight=1)

        # GIF selection
        ttk.Label(gif_frame, text="GIF Effect:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.gif_var = tk.StringVar(value="none")
        self.gif_combo = ttk.Combobox(gif_frame, textvariable=self.gif_var, state="readonly")
        self.gif_combo.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        # Random GIF
        self.random_gif_var = tk.BooleanVar()
        random_gif_check = ttk.Checkbutton(gif_frame, text="Use Random GIF", variable=self.random_gif_var)
        random_gif_check.grid(row=1, column=0, columnspan=2, sticky="w", padx=5, pady=2)

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
