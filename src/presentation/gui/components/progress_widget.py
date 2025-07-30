"""
Progress Widget

Widget for displaying processing progress with individual video tracking.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any, Optional, Callable

from ....application.models.processing_models import ProcessingJobDTO, QueueStatus
from ...common.ui_helpers import FormatHelper


class ProgressWidget:
    """Widget for displaying processing progress"""

    def __init__(self, parent, on_job_action: Optional[Callable] = None):
        """
        Initialize progress widget.

        Args:
            parent: Parent widget
            on_job_action: Callback for job actions (action, job_id)
        """
        self.parent = parent
        self.on_job_action = on_job_action
        self._jobs: List[ProcessingJobDTO] = []
        self._create_widgets()
        self._setup_events()

    def _create_widgets(self):
        """Create widget components with modern design"""
        # Main frame with modern styling
        self.frame = ttk.LabelFrame(self.parent, text="📊 Processing Progress")

        # Controls frame with improved layout
        self.controls_frame = ttk.Frame(self.frame)
        self.controls_frame.pack(fill="x", padx=10, pady=8)

        # Left side - Processing controls
        left_controls = ttk.Frame(self.controls_frame)
        left_controls.pack(side="left", fill="x", expand=True)

        self.start_btn = ttk.Button(left_controls, text="▶️ Start")
        self.start_btn.pack(side="left", padx=(0, 8))

        self.pause_btn = ttk.Button(left_controls, text="⏸️ Pause", state="disabled")
        self.pause_btn.pack(side="left", padx=(0, 8))

        self.stop_btn = ttk.Button(left_controls, text="⏹️ Stop", state="disabled")
        self.stop_btn.pack(side="left", padx=(0, 8))

        self.clear_btn = ttk.Button(left_controls, text="🗑️ Clear")
        self.clear_btn.pack(side="left")

        # Right side - Overall progress
        progress_frame = ttk.Frame(self.controls_frame)
        progress_frame.pack(side="right", fill="x", expand=True, padx=(15, 0))

        progress_header = ttk.Frame(progress_frame)
        progress_header.pack(fill="x", pady=(0, 5))

        ttk.Label(progress_header, text="Overall Progress:").pack(side="left")
        self.overall_label = ttk.Label(progress_header, text="0%", width=8)
        self.overall_label.pack(side="right")

        self.overall_progress = ttk.Progressbar(progress_frame, mode="determinate")
        self.overall_progress.pack(fill="x")

        # Statistics frame with modern cards
        self.stats_frame = ttk.Frame(self.frame)
        self.stats_frame.pack(fill="x", padx=10, pady=8)

        # Create stat cards
        self._create_stat_cards()

        # Job list frame with improved design
        self.job_list_frame = ttk.Frame(self.frame)
        self.job_list_frame.pack(fill="both", expand=True, padx=10, pady=8)
        self.job_list_frame.rowconfigure(0, weight=1)
        self.job_list_frame.columnconfigure(0, weight=1)

        # Job list header
        list_header = ttk.Frame(self.job_list_frame)
        list_header.pack(fill="x", pady=(0, 5))

        ttk.Label(list_header, text="📋 Processing Queue").pack(side="left")

        # Job treeview with modern styling
        columns = ("Video", "Status", "Progress", "Time", "Actions")
        self.job_tree = ttk.Treeview(self.job_list_frame, columns=columns, show="headings", height=10)

        # Configure columns with better widths and icons
        column_configs = {
            "Video": {"width": 250, "minwidth": 150, "text": "🎬 Video"},
            "Status": {"width": 100, "minwidth": 80, "text": "📊 Status"},
            "Progress": {"width": 100, "minwidth": 80, "text": "📈 Progress"},
            "Time": {"width": 80, "minwidth": 60, "text": "⏱️ Time"},
            "Actions": {"width": 100, "minwidth": 80, "text": "⚙️ Actions"}
        }

        for col, config in column_configs.items():
            self.job_tree.heading(col, text=config["text"])
            self.job_tree.column(col, width=config["width"], minwidth=config["minwidth"])

        # Scrollbars with modern styling
        self.job_v_scrollbar = ttk.Scrollbar(self.job_list_frame, orient="vertical", command=self.job_tree.yview)
        self.job_h_scrollbar = ttk.Scrollbar(self.job_list_frame, orient="horizontal", command=self.job_tree.xview)

        self.job_tree.configure(yscrollcommand=self.job_v_scrollbar.set, xscrollcommand=self.job_h_scrollbar.set)

        # Grid layout
        self.job_tree.pack(side="left", fill="both", expand=True)
        self.job_v_scrollbar.pack(side="right", fill="y")
        self.job_h_scrollbar.pack(side="bottom", fill="x")

        # Context menu for jobs with modern styling
        self.job_context_menu = tk.Menu(self.job_tree, tearoff=0, bg='#2d2d2d', fg='#ffffff', 
                                       activebackground='#007acc', activeforeground='#ffffff')
        self.job_context_menu.add_command(label="❌ Cancel Job", command=self._on_cancel_job)
        self.job_context_menu.add_command(label="🔄 Retry Job", command=self._on_retry_job)
        self.job_context_menu.add_separator()
        self.job_context_menu.add_command(label="👁️ Show Details", command=self._on_show_job_details)

    def _create_stat_cards(self):
        """Create modern stat cards"""
        # Queue stat card
        queue_card = ttk.LabelFrame(self.stats_frame, text="📋 Queue")
        queue_card.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=2)
        queue_card.columnconfigure(0, weight=1)
        
        self.queue_label = ttk.Label(queue_card, text="0")
        self.queue_label.grid(row=0, column=0, padx=10, pady=5)

        # Processing stat card
        processing_card = ttk.LabelFrame(self.stats_frame, text="⚡ Processing")
        processing_card.grid(row=0, column=1, sticky="ew", padx=4, pady=2)
        processing_card.columnconfigure(0, weight=1)
        
        self.processing_label = ttk.Label(processing_card, text="0")
        self.processing_label.grid(row=0, column=0, padx=10, pady=5)

        # Completed stat card
        completed_card = ttk.LabelFrame(self.stats_frame, text="✅ Completed")
        completed_card.grid(row=0, column=2, sticky="ew", padx=4, pady=2)
        completed_card.columnconfigure(0, weight=1)
        
        self.completed_label = ttk.Label(completed_card, text="0")
        self.completed_label.grid(row=0, column=0, padx=10, pady=5)

        # Failed stat card
        failed_card = ttk.LabelFrame(self.stats_frame, text="❌ Failed")
        failed_card.grid(row=0, column=3, sticky="ew", padx=4, pady=2)
        failed_card.columnconfigure(0, weight=1)
        
        self.failed_label = ttk.Label(failed_card, text="0")
        self.failed_label.grid(row=0, column=0, padx=10, pady=5)

        # Success rate stat card
        success_card = ttk.LabelFrame(self.stats_frame, text="📊 Success Rate")
        success_card.grid(row=0, column=4, sticky="ew", padx=(8, 0), pady=2)
        success_card.columnconfigure(0, weight=1)
        
        self.success_rate_label = ttk.Label(success_card, text="0%")
        self.success_rate_label.grid(row=0, column=0, padx=10, pady=5)

        # Configure grid weights
        for i in range(5):
            self.stats_frame.columnconfigure(i, weight=1)

    def _setup_events(self):
        """Setup event handlers"""
        self.job_tree.bind("<Button-3>", self._on_job_right_click)  # Right click
        self.job_tree.bind("<Double-1>", self._on_job_double_click)  # Double click

    def pack(self, **kwargs):
        """Pack the widget"""
        self.frame.pack(**kwargs)

    def grid(self, **kwargs):
        """Grid the widget"""
        self.frame.grid(**kwargs)

    def set_button_callbacks(self, start_callback: Callable, pause_callback: Callable,
                           stop_callback: Callable, clear_callback: Callable) -> None:
        """
        Set button callbacks.

        Args:
            start_callback: Start processing callback
            pause_callback: Pause processing callback
            stop_callback: Stop processing callback
            clear_callback: Clear completed jobs callback
        """
        self.start_btn.config(command=start_callback)
        self.pause_btn.config(command=pause_callback)
        self.stop_btn.config(command=stop_callback)
        self.clear_btn.config(command=clear_callback)

    def update_jobs(self, jobs: List[ProcessingJobDTO]) -> None:
        """
        Update job list.

        Args:
            jobs: List of processing job DTOs
        """
        self._jobs = jobs
        self._refresh_job_display()

    def update_queue_status(self, status: QueueStatus) -> None:
        """
        Update queue status display.

        Args:
            status: Queue status
        """
        # Update statistics labels with modern cards
        self.queue_label.config(text=str(status.queue_size))
        self.processing_label.config(text=str(status.processing_count))
        self.completed_label.config(text=str(status.completed_count))
        self.failed_label.config(text=str(status.failed_count))

        # Calculate and update success rate
        total_finished = status.completed_count + status.failed_count
        if total_finished > 0:
            success_rate = (status.completed_count / total_finished) * 100
            self.success_rate_label.config(text=f"{success_rate:.1f}%")
        else:
            self.success_rate_label.config(text="0%")

        # Update overall progress
        if status.total_jobs > 0:
            progress = (status.completed_count / status.total_jobs) * 100
            self.overall_progress['value'] = progress
            self.overall_label.config(text=f"{progress:.1f}%")
        else:
            self.overall_progress['value'] = 0
            self.overall_label.config(text="0%")

        # Update button states
        if status.is_processing:
            self.start_btn.config(state="disabled")
            self.pause_btn.config(state="normal")
            self.stop_btn.config(state="normal")
        else:
            self.start_btn.config(state="normal")
            self.pause_btn.config(state="disabled")
            self.stop_btn.config(state="disabled")

    def _refresh_job_display(self) -> None:
        """Refresh job display"""
        # Clear existing items
        for item in self.job_tree.get_children():
            self.job_tree.delete(item)

        # Add jobs
        for job in self._jobs:
            # Format time
            time_text = ""
            if job.actual_duration:
                time_text = FormatHelper.format_duration(job.actual_duration)
            elif job.estimated_duration:
                time_text = f"~{FormatHelper.format_duration(job.estimated_duration)}"

            # Format actions based on status
            actions_text = ""
            if job.status == "processing":
                actions_text = "Cancel"
            elif job.status == "failed":
                actions_text = "Retry"
            elif job.status in ["queued", "pending"]:
                actions_text = "Cancel"

            values = (
                job.main_video_name,
                job.status.title(),
                f"{job.progress:.1f}%",
                time_text,
                actions_text
            )

            # Insert item with status-based tags for styling
            item = self.job_tree.insert("", "end", values=values, tags=(job.id, job.status))

        # Configure tags for different statuses
        self.job_tree.tag_configure("completed", background="#d4edda")
        self.job_tree.tag_configure("failed", background="#f8d7da")
        self.job_tree.tag_configure("processing", background="#d1ecf1")
        self.job_tree.tag_configure("queued", background="#fff3cd")

    def _on_job_right_click(self, event) -> None:
        """Handle job right click"""
        item = self.job_tree.identify_row(event.y)
        if item:
            self.job_tree.selection_set(item)

            # Get job info
            tags = self.job_tree.item(item, "tags")
            if len(tags) >= 2:
                job_id, status = tags[0], tags[1]

                # Update context menu based on status
                self.job_context_menu.entryconfig("❌ Cancel Job",
                                                 state="normal" if status in ["queued", "processing"] else "disabled")
                self.job_context_menu.entryconfig("🔄 Retry Job",
                                                 state="normal" if status == "failed" else "disabled")

                # Show context menu
                self.job_context_menu.post(event.x_root, event.y_root)

    def _on_job_double_click(self, event) -> None:
        """Handle job double click"""
        item = self.job_tree.identify_row(event.y)
        if item:
            self._on_show_job_details()

    def _on_cancel_job(self) -> None:
        """Handle cancel job action"""
        selected_item = self.job_tree.selection()
        if selected_item:
            tags = self.job_tree.item(selected_item[0], "tags")
            if tags:
                job_id = tags[0]
                self._notify_job_action("cancel", job_id)

    def _on_retry_job(self) -> None:
        """Handle retry job action"""
        selected_item = self.job_tree.selection()
        if selected_item:
            tags = self.job_tree.item(selected_item[0], "tags")
            if tags:
                job_id = tags[0]
                self._notify_job_action("retry", job_id)

    def _on_show_job_details(self) -> None:
        """Handle show job details action"""
        selected_item = self.job_tree.selection()
        if selected_item:
            tags = self.job_tree.item(selected_item[0], "tags")
            if tags:
                job_id = tags[0]
                self._notify_job_action("details", job_id)

    def _notify_job_action(self, action: str, job_id: str) -> None:
        """Notify job action callback"""
        if self.on_job_action:
            try:
                self.on_job_action(action, job_id)
            except Exception as e:
                print(f"Error in job action callback: {e}")  # Use logger in real implementation

    def show_job_details_dialog(self, job: ProcessingJobDTO) -> None:
        """
        Show job details in a dialog.

        Args:
            job: Job to show details for
        """
        # Create details window
        details_window = tk.Toplevel(self.frame)
        details_window.title(f"Job Details - {job.main_video_name}")
        details_window.geometry("500x400")
        details_window.transient(self.frame.winfo_toplevel())
        details_window.grab_set()

        # Create notebook for different detail sections
        notebook = ttk.Notebook(details_window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # General info tab
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="General")

        # Add general info
        info_items = [
            ("Job ID", job.id),
            ("Main Video", job.main_video_name),
            ("Background Video", job.background_video_name or "None"),
            ("Output File", job.output_filename or "None"),
            ("Status", job.status.title()),
            ("Progress", f"{job.progress:.1f}%"),
            ("Created", job.created_at or "Unknown"),
            ("Started", job.started_at or "Not started"),
            ("Completed", job.completed_at or "Not completed"),
            ("Estimated Duration", FormatHelper.format_duration(job.estimated_duration) if job.estimated_duration else "Unknown"),
            ("Actual Duration", FormatHelper.format_duration(job.actual_duration) if job.actual_duration else "Not completed")
        ]

        for i, (label, value) in enumerate(info_items):
            ttk.Label(general_frame, text=f"{label}:").grid(
                row=i, column=0, sticky="w", padx=5, pady=2)
            ttk.Label(general_frame, text=str(value)).grid(
                row=i, column=1, sticky="w", padx=5, pady=2)

        # Effects tab
        effects_frame = ttk.Frame(notebook)
        notebook.add(effects_frame, text="Effects")

        if job.effects:
            effects_tree = ttk.Treeview(effects_frame, columns=("Duration", "Parameters"), show="tree headings")
            effects_tree.heading("#0", text="Effect Type")
            effects_tree.heading("Duration", text="Duration")
            effects_tree.heading("Parameters", text="Parameters")

            for effect in job.effects:
                params_text = ", ".join(f"{k}={v}" for k, v in effect.parameters.items()) if effect.parameters else "None"
                effects_tree.insert("", "end", text=effect.display_name,
                                  values=(f"{effect.duration}s", params_text))

            effects_tree.pack(fill="both", expand=True, padx=5, pady=5)
        else:
            ttk.Label(effects_frame, text="No effects configured").pack(padx=5, pady=5)

        # Error tab (if there's an error)
        if job.error_message:
            error_frame = ttk.Frame(notebook)
            notebook.add(error_frame, text="Error")

            error_text = tk.Text(error_frame, wrap="word", height=10)
            error_scrollbar = ttk.Scrollbar(error_frame, orient="vertical", command=error_text.yview)
            error_text.configure(yscrollcommand=error_scrollbar.set)

            error_text.insert("1.0", job.error_message)
            error_text.config(state="disabled")

            error_text.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=5)
            error_scrollbar.pack(side="right", fill="y", padx=(0, 5), pady=5)

        # Close button
        close_btn = ttk.Button(details_window, text="Close", command=details_window.destroy)
        close_btn.pack(pady=10)
