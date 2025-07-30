"""
Video List Widget

Reusable widget for displaying and selecting videos.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Callable, Optional, Set

from ....application.models.video_models import VideoDTO
from ...common.ui_helpers import FormatHelper


class VideoListWidget:
    """Widget for displaying video list with selection"""

    def __init__(self, parent, on_selection_changed: Optional[Callable] = None):
        """
        Initialize video list widget.

        Args:
            parent: Parent widget
            on_selection_changed: Callback when selection changes
        """
        self.parent = parent
        self.on_selection_changed = on_selection_changed
        self._videos: List[VideoDTO] = []
        self._create_widgets()
        self._setup_events()

    def _create_widgets(self):
        """Create widget components"""
        # Main frame
        self.frame = ttk.LabelFrame(self.parent, text="Video Selection")

        # Controls frame
        self.controls_frame = ttk.Frame(self.frame)
        self.controls_frame.pack(fill="x", padx=5, pady=5)

        # Control buttons
        self.select_all_btn = ttk.Button(self.controls_frame, text="Select All")
        self.select_all_btn.pack(side="left", padx=(0, 5))

        self.clear_selection_btn = ttk.Button(self.controls_frame, text="Clear Selection")
        self.clear_selection_btn.pack(side="left", padx=(0, 5))

        self.refresh_btn = ttk.Button(self.controls_frame, text="Refresh")
        self.refresh_btn.pack(side="left")

        # Search frame
        search_frame = ttk.Frame(self.controls_frame)
        search_frame.pack(side="right")

        ttk.Label(search_frame, text="Search:").pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        self.search_entry.pack(side="left")

        # List frame
        self.list_frame = ttk.Frame(self.frame)
        self.list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Configure grid
        self.list_frame.rowconfigure(0, weight=1)
        self.list_frame.columnconfigure(0, weight=1)

        # Treeview
        columns = ("Name", "Duration", "Resolution", "Size", "Format", "Status")
        self.tree = ttk.Treeview(self.list_frame, columns=columns, show="tree headings", selectmode="extended")

        # Configure columns
        self.tree.heading("#0", text="☐")
        self.tree.column("#0", width=30, minwidth=30, stretch=False)

        column_widths = {"Name": 200, "Duration": 80, "Resolution": 100, "Size": 80, "Format": 60, "Status": 80}
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=column_widths.get(col, 100), minwidth=50)

        # Scrollbars
        self.v_scrollbar = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.tree.yview)
        self.h_scrollbar = ttk.Scrollbar(self.list_frame, orient="horizontal", command=self.tree.xview)

        self.tree.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)

        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")

        # Status label
        self.status_label = ttk.Label(self.frame, text="No videos loaded")
        self.status_label.pack(fill="x", padx=5, pady=(0, 5))

    def _setup_events(self):
        """Setup event handlers"""
        self.select_all_btn.config(command=self._on_select_all)
        self.clear_selection_btn.config(command=self._on_clear_selection)
        self.search_var.trace("w", self._on_search_changed)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_selection_changed)
        self.tree.bind("<Button-1>", self._on_tree_click)

    def pack(self, **kwargs):
        """Pack the widget"""
        self.frame.pack(**kwargs)

    def grid(self, **kwargs):
        """Grid the widget"""
        self.frame.grid(**kwargs)

    def update_videos(self, videos: List[VideoDTO]) -> None:
        """
        Update video list.

        Args:
            videos: List of video DTOs
        """
        self._videos = videos
        self._refresh_display()
        self._update_status()

    def get_selected_videos(self) -> List[VideoDTO]:
        """
        Get selected videos.

        Returns:
            List of selected video DTOs
        """
        selected = []
        for item in self.tree.selection():
            video_path = self.tree.item(item, "tags")[0] if self.tree.item(item, "tags") else None
            if video_path:
                video = next((v for v in self._videos if v.path == video_path), None)
                if video:
                    selected.append(video)
        return selected

    def get_selected_paths(self) -> List[str]:
        """
        Get selected video paths.

        Returns:
            List of selected video paths
        """
        return [video.path for video in self.get_selected_videos()]

    def set_refresh_callback(self, callback: Callable) -> None:
        """Set refresh button callback"""
        self.refresh_btn.config(command=callback)

    def _refresh_display(self) -> None:
        """Refresh the display with current videos"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Get search filter
        search_text = self.search_var.get().lower()

        # Add videos
        for video in self._videos:
            # Apply search filter
            if search_text and search_text not in video.filename.lower():
                continue

            values = (
                video.filename,
                FormatHelper.format_duration(video.duration),
                video.resolution_string,
                FormatHelper.format_file_size(video.file_size or 0),
                video.format or "Unknown",
                "Cached" if video.cached else "New"
            )

            # Insert item
            item = self.tree.insert("", "end", values=values, tags=(video.path,))

            # Set checkbox state (empty for now)
            self.tree.set(item, "#0", "☐")

    def _update_status(self) -> None:
        """Update status label"""
        total_count = len(self._videos)
        selected_count = len(self.get_selected_videos())

        if total_count == 0:
            status_text = "No videos loaded"
        else:
            total_duration = sum(video.duration for video in self._videos)
            status_text = f"{total_count} videos ({FormatHelper.format_duration(total_duration)}) | {selected_count} selected"

        self.status_label.config(text=status_text)

    def _on_select_all(self) -> None:
        """Handle select all button"""
        for item in self.tree.get_children():
            self.tree.selection_add(item)
            self.tree.set(item, "#0", "☑")
        self._update_status()
        self._notify_selection_changed()

    def _on_clear_selection(self) -> None:
        """Handle clear selection button"""
        for item in self.tree.get_children():
            self.tree.selection_remove(item)
            self.tree.set(item, "#0", "☐")
        self._update_status()
        self._notify_selection_changed()

    def _on_search_changed(self, *args) -> None:
        """Handle search text change"""
        self._refresh_display()

    def _on_tree_selection_changed(self, event) -> None:
        """Handle tree selection change"""
        # Update checkboxes
        for item in self.tree.get_children():
            if item in self.tree.selection():
                self.tree.set(item, "#0", "☑")
            else:
                self.tree.set(item, "#0", "☐")

        self._update_status()
        self._notify_selection_changed()

    def _on_tree_click(self, event) -> None:
        """Handle tree click (for checkbox toggle)"""
        region = self.tree.identify_region(event.x, event.y)
        if region == "tree":
            item = self.tree.identify_row(event.y)
            if item:
                # Toggle selection
                if item in self.tree.selection():
                    self.tree.selection_remove(item)
                else:
                    self.tree.selection_add(item)

    def _notify_selection_changed(self) -> None:
        """Notify selection changed callback"""
        if self.on_selection_changed:
            try:
                selected_videos = self.get_selected_videos()
                self.on_selection_changed(selected_videos)
            except Exception as e:
                print(f"Error in selection changed callback: {e}")  # Use logger in real implementation
