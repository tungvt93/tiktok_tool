"""
UI Helpers

Common UI utilities and helper functions.
"""

import threading
from typing import Callable, Any, Optional
from pathlib import Path
import time

from ...shared.utils import get_logger

logger = get_logger(__name__)


class UIThread:
    """Helper for UI thread operations"""

    @staticmethod
    def invoke(callback: Callable, *args, **kwargs) -> None:
        """
        Invoke callback on UI thread (placeholder - framework specific).

        Args:
            callback: Function to call
            *args: Arguments
            **kwargs: Keyword arguments
        """
        # This would be implemented differently for each UI framework
        # For now, just call directly
        try:
            callback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in UI thread callback: {e}")

    @staticmethod
    def invoke_async(callback: Callable, *args, **kwargs) -> None:
        """
        Invoke callback on UI thread asynchronously.

        Args:
            callback: Function to call
            *args: Arguments
            **kwargs: Keyword arguments
        """
        def worker():
            UIThread.invoke(callback, *args, **kwargs)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()


class ProgressTracker:
    """Helper for tracking and reporting progress"""

    def __init__(self, total_steps: int, callback: Optional[Callable[[float, str], None]] = None):
        """
        Initialize progress tracker.

        Args:
            total_steps: Total number of steps
            callback: Progress callback (progress_percent, message)
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.callback = callback
        self._start_time = time.time()

    def update(self, step: int, message: str = "") -> None:
        """
        Update progress.

        Args:
            step: Current step number
            message: Progress message
        """
        self.current_step = min(step, self.total_steps)
        progress_percent = (self.current_step / self.total_steps) * 100 if self.total_steps > 0 else 0

        if self.callback:
            self.callback(progress_percent, message)

    def increment(self, message: str = "") -> None:
        """
        Increment progress by one step.

        Args:
            message: Progress message
        """
        self.update(self.current_step + 1, message)

    def complete(self, message: str = "Complete") -> None:
        """
        Mark progress as complete.

        Args:
            message: Completion message
        """
        self.update(self.total_steps, message)

    @property
    def progress_percent(self) -> float:
        """Get current progress percentage"""
        return (self.current_step / self.total_steps) * 100 if self.total_steps > 0 else 0

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        return time.time() - self._start_time

    @property
    def estimated_remaining_time(self) -> Optional[float]:
        """Get estimated remaining time in seconds"""
        if self.current_step == 0:
            return None

        elapsed = self.elapsed_time
        rate = self.current_step / elapsed
        remaining_steps = self.total_steps - self.current_step

        return remaining_steps / rate if rate > 0 else None


class FileDialogHelper:
    """Helper for file dialog operations"""

    @staticmethod
    def select_video_file(title: str = "Select Video File") -> Optional[Path]:
        """
        Show file dialog to select video file.

        Args:
            title: Dialog title

        Returns:
            Selected file path or None if cancelled
        """
        # This would be implemented with actual file dialog
        # For now, return None as placeholder
        logger.info(f"File dialog requested: {title}")
        return None

    @staticmethod
    def select_multiple_video_files(title: str = "Select Video Files") -> list[Path]:
        """
        Show file dialog to select multiple video files.

        Args:
            title: Dialog title

        Returns:
            List of selected file paths
        """
        # This would be implemented with actual file dialog
        logger.info(f"Multiple file dialog requested: {title}")
        return []

    @staticmethod
    def select_directory(title: str = "Select Directory") -> Optional[Path]:
        """
        Show dialog to select directory.

        Args:
            title: Dialog title

        Returns:
            Selected directory path or None if cancelled
        """
        # This would be implemented with actual directory dialog
        logger.info(f"Directory dialog requested: {title}")
        return None

    @staticmethod
    def save_file(title: str = "Save File", default_extension: str = ".mp4") -> Optional[Path]:
        """
        Show save file dialog.

        Args:
            title: Dialog title
            default_extension: Default file extension

        Returns:
            Selected save path or None if cancelled
        """
        # This would be implemented with actual save dialog
        logger.info(f"Save dialog requested: {title}")
        return None


class MessageBoxHelper:
    """Helper for message box operations"""

    @staticmethod
    def show_info(title: str, message: str) -> None:
        """
        Show information message box.

        Args:
            title: Message box title
            message: Message text
        """
        logger.info(f"Info message: {title} - {message}")

    @staticmethod
    def show_warning(title: str, message: str) -> None:
        """
        Show warning message box.

        Args:
            title: Message box title
            message: Message text
        """
        logger.warning(f"Warning message: {title} - {message}")

    @staticmethod
    def show_error(title: str, message: str) -> None:
        """
        Show error message box.

        Args:
            title: Message box title
            message: Message text
        """
        logger.error(f"Error message: {title} - {message}")

    @staticmethod
    def show_question(title: str, message: str) -> bool:
        """
        Show question message box.

        Args:
            title: Message box title
            message: Question text

        Returns:
            True if user clicked Yes/OK, False otherwise
        """
        logger.info(f"Question message: {title} - {message}")
        return False  # Placeholder


class ValidationHelper:
    """Helper for UI validation"""

    @staticmethod
    def validate_required_field(value: str, field_name: str) -> Optional[str]:
        """
        Validate required field.

        Args:
            value: Field value
            field_name: Name of the field

        Returns:
            Error message or None if valid
        """
        if not value or not value.strip():
            return f"{field_name} is required"
        return None

    @staticmethod
    def validate_numeric_field(value: str, field_name: str,
                             min_value: Optional[float] = None,
                             max_value: Optional[float] = None) -> Optional[str]:
        """
        Validate numeric field.

        Args:
            value: Field value
            field_name: Name of the field
            min_value: Minimum allowed value
            max_value: Maximum allowed value

        Returns:
            Error message or None if valid
        """
        try:
            num_value = float(value)

            if min_value is not None and num_value < min_value:
                return f"{field_name} must be at least {min_value}"

            if max_value is not None and num_value > max_value:
                return f"{field_name} must be at most {max_value}"

            return None

        except ValueError:
            return f"{field_name} must be a valid number"

    @staticmethod
    def validate_file_path(path: str, field_name: str, must_exist: bool = True) -> Optional[str]:
        """
        Validate file path.

        Args:
            path: File path
            field_name: Name of the field
            must_exist: Whether file must exist

        Returns:
            Error message or None if valid
        """
        if not path or not path.strip():
            return f"{field_name} is required"

        try:
            file_path = Path(path)

            if must_exist and not file_path.exists():
                return f"{field_name} file does not exist"

            if must_exist and not file_path.is_file():
                return f"{field_name} must be a file"

            return None

        except Exception:
            return f"{field_name} is not a valid file path"


class FormatHelper:
    """Helper for formatting values for display"""

    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        Format duration in seconds to human-readable string.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes:02d}:{secs:02d}"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def format_file_size(bytes_size: int) -> str:
        """
        Format file size in bytes to human-readable string.

        Args:
            bytes_size: Size in bytes

        Returns:
            Formatted size string
        """
        if bytes_size < 1024:
            return f"{bytes_size} B"
        elif bytes_size < 1024 * 1024:
            return f"{bytes_size / 1024:.1f} KB"
        elif bytes_size < 1024 * 1024 * 1024:
            return f"{bytes_size / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_size / (1024 * 1024 * 1024):.1f} GB"

    @staticmethod
    def format_percentage(value: float, decimal_places: int = 1) -> str:
        """
        Format percentage value.

        Args:
            value: Percentage value (0-100)
            decimal_places: Number of decimal places

        Returns:
            Formatted percentage string
        """
        return f"{value:.{decimal_places}f}%"

    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
        """
        Truncate text to maximum length.

        Args:
            text: Text to truncate
            max_length: Maximum length
            suffix: Suffix to add if truncated

        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text

        return text[:max_length - len(suffix)] + suffix
