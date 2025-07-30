"""
Validation Utilities

Common validation functions and classes.
"""

from pathlib import Path
from typing import List, Optional, Union, Any, Dict
import re
import mimetypes
from urllib.parse import urlparse

from ..config.app_config import AppConfig


class ValidationError(Exception):
    """Custom validation error"""

    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


class ValidationResult:
    """Result of validation operation"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def add_error(self, message: str) -> None:
        """Add validation error"""
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Add validation warning"""
        self.warnings.append(message)

    def is_valid(self) -> bool:
        """Check if validation passed (no errors)"""
        return len(self.errors) == 0

    def has_warnings(self) -> bool:
        """Check if there are warnings"""
        return len(self.warnings) > 0

    def get_summary(self) -> str:
        """Get validation summary"""
        if self.is_valid() and not self.has_warnings():
            return "Validation passed"

        summary = []
        if self.errors:
            summary.append(f"{len(self.errors)} error(s)")
        if self.warnings:
            summary.append(f"{len(self.warnings)} warning(s)")

        return f"Validation completed with {', '.join(summary)}"


class Validator:
    """Main validation class with common validation methods"""

    # Supported video formats
    SUPPORTED_VIDEO_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'}

    # Supported image formats for GIFs/effects
    SUPPORTED_IMAGE_FORMATS = {'.gif', '.png', '.jpg', '.jpeg', '.bmp', '.tiff'}

    @staticmethod
    def validate_video_file(path: Path) -> ValidationResult:
        """
        Validate video file.

        Args:
            path: Path to video file

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        # Check if file exists
        if not path.exists():
            result.add_error(f"Video file does not exist: {path}")
            return result

        # Check if it's a file (not directory)
        if not path.is_file():
            result.add_error(f"Path is not a file: {path}")
            return result

        # Check file extension
        if path.suffix.lower() not in Validator.SUPPORTED_VIDEO_FORMATS:
            result.add_error(f"Unsupported video format: {path.suffix}")

        # Check file size
        try:
            file_size = path.stat().st_size
            if file_size == 0:
                result.add_error("Video file is empty")
            elif file_size < 1024:  # Less than 1KB
                result.add_warning("Video file is very small, may be corrupted")
            elif file_size > 2 * 1024 * 1024 * 1024:  # Larger than 2GB
                result.add_warning("Video file is very large, processing may be slow")
        except Exception as e:
            result.add_error(f"Cannot read file information: {e}")

        # Check MIME type
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type and not mime_type.startswith('video/'):
            result.add_warning(f"File MIME type is not video: {mime_type}")

        return result

    @staticmethod
    def validate_image_file(path: Path) -> ValidationResult:
        """
        Validate image file (for GIFs and effects).

        Args:
            path: Path to image file

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        if not path.exists():
            result.add_error(f"Image file does not exist: {path}")
            return result

        if not path.is_file():
            result.add_error(f"Path is not a file: {path}")
            return result

        if path.suffix.lower() not in Validator.SUPPORTED_IMAGE_FORMATS:
            result.add_error(f"Unsupported image format: {path.suffix}")

        try:
            file_size = path.stat().st_size
            if file_size == 0:
                result.add_error("Image file is empty")
            elif file_size > 50 * 1024 * 1024:  # Larger than 50MB
                result.add_warning("Image file is very large")
        except Exception as e:
            result.add_error(f"Cannot read file information: {e}")

        return result

    @staticmethod
    def validate_directory(path: Path, must_exist: bool = True,
                          must_be_writable: bool = False) -> ValidationResult:
        """
        Validate directory.

        Args:
            path: Path to directory
            must_exist: Whether directory must exist
            must_be_writable: Whether directory must be writable

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        if must_exist and not path.exists():
            result.add_error(f"Directory does not exist: {path}")
            return result

        if path.exists() and not path.is_dir():
            result.add_error(f"Path exists but is not a directory: {path}")
            return result

        if must_be_writable:
            try:
                # Try to create directory if it doesn't exist
                path.mkdir(parents=True, exist_ok=True)

                # Test write access
                test_file = path / ".write_test"
                test_file.touch()
                test_file.unlink()
            except Exception as e:
                result.add_error(f"Directory is not writable: {e}")

        return result

    @staticmethod
    def validate_config(config: AppConfig) -> ValidationResult:
        """
        Validate application configuration.

        Args:
            config: Application configuration

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        # Validate video configuration
        video_result = Validator._validate_video_config(config.video)
        result.errors.extend(video_result.errors)
        result.warnings.extend(video_result.warnings)

        # Validate paths
        paths_result = Validator._validate_paths_config(config.paths)
        result.errors.extend(paths_result.errors)
        result.warnings.extend(paths_result.warnings)

        # Validate performance settings
        perf_result = Validator._validate_performance_config(config.performance)
        result.errors.extend(perf_result.errors)
        result.warnings.extend(perf_result.warnings)

        # Validate UI settings
        ui_result = Validator._validate_ui_config(config.ui)
        result.errors.extend(ui_result.errors)
        result.warnings.extend(ui_result.warnings)

        return result

    @staticmethod
    def _validate_video_config(config) -> ValidationResult:
        """Validate video processing configuration"""
        result = ValidationResult()

        if config.output_width <= 0 or config.output_height <= 0:
            result.add_error("Output dimensions must be positive")

        if config.output_width % 2 != 0 or config.output_height % 2 != 0:
            result.add_warning("Output dimensions should be even numbers for better codec compatibility")

        if config.speed_multiplier <= 0:
            result.add_error("Speed multiplier must be positive")
        elif config.speed_multiplier > 3.0:
            result.add_warning("Very high speed multiplier may cause audio issues")

        if config.frame_rate <= 0:
            result.add_error("Frame rate must be positive")
        elif config.frame_rate > 60:
            result.add_warning("High frame rate may increase processing time significantly")

        if not (0 <= config.crf_value <= 51):
            result.add_error("CRF value must be between 0 and 51")

        return result

    @staticmethod
    def _validate_paths_config(config) -> ValidationResult:
        """Validate paths configuration"""
        result = ValidationResult()

        # Validate input directory
        input_result = Validator.validate_directory(config.input_dir, must_exist=True)
        if not input_result.is_valid():
            result.add_error(f"Input directory invalid: {input_result.errors[0]}")

        # Validate background directory
        bg_result = Validator.validate_directory(config.background_dir, must_exist=True)
        if not bg_result.is_valid():
            result.add_error(f"Background directory invalid: {bg_result.errors[0]}")

        # Validate output directory
        output_result = Validator.validate_directory(config.output_dir, must_exist=False, must_be_writable=True)
        if not output_result.is_valid():
            result.add_error(f"Output directory invalid: {output_result.errors[0]}")

        # Validate patterns
        if not config.input_pattern:
            result.add_error("Input pattern cannot be empty")
        if not config.background_pattern:
            result.add_error("Background pattern cannot be empty")

        return result

    @staticmethod
    def _validate_performance_config(config) -> ValidationResult:
        """Validate performance configuration"""
        result = ValidationResult()

        if config.max_workers <= 0:
            result.add_error("Max workers must be positive")
        elif config.max_workers > 16:
            result.add_warning("Very high worker count may cause system instability")

        if config.memory_limit_mb is not None:
            if config.memory_limit_mb <= 0:
                result.add_error("Memory limit must be positive")
            elif config.memory_limit_mb < 512:
                result.add_warning("Low memory limit may cause processing failures")

        return result

    @staticmethod
    def _validate_ui_config(config) -> ValidationResult:
        """Validate UI configuration"""
        result = ValidationResult()

        if config.window_width <= 0 or config.window_height <= 0:
            result.add_error("Window dimensions must be positive")
        elif config.window_width < 800 or config.window_height < 600:
            result.add_warning("Small window size may affect usability")

        if config.auto_refresh_interval <= 0:
            result.add_error("Auto refresh interval must be positive")
        elif config.auto_refresh_interval < 1:
            result.add_warning("Very short refresh interval may impact performance")

        return result

    @staticmethod
    def validate_filename(filename: str) -> ValidationResult:
        """
        Validate filename for safety.

        Args:
            filename: Filename to validate

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        if not filename:
            result.add_error("Filename cannot be empty")
            return result

        # Check for invalid characters
        invalid_chars = r'[<>:"/\\|?*]'
        if re.search(invalid_chars, filename):
            result.add_error("Filename contains invalid characters")

        # Check length
        if len(filename) > 255:
            result.add_error("Filename is too long (max 255 characters)")

        # Check for reserved names (Windows)
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }

        name_without_ext = Path(filename).stem.upper()
        if name_without_ext in reserved_names:
            result.add_error(f"Filename uses reserved name: {name_without_ext}")

        return result

    @staticmethod
    def validate_url(url: str) -> ValidationResult:
        """
        Validate URL format.

        Args:
            url: URL to validate

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        if not url:
            result.add_error("URL cannot be empty")
            return result

        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                result.add_error("URL must have a scheme (http/https)")
            elif parsed.scheme not in ['http', 'https']:
                result.add_warning(f"Unusual URL scheme: {parsed.scheme}")

            if not parsed.netloc:
                result.add_error("URL must have a domain")
        except Exception as e:
            result.add_error(f"Invalid URL format: {e}")

        return result


# Convenience functions
def validate_video_file(path: Union[str, Path]) -> ValidationResult:
    """Validate video file (convenience function)"""
    return Validator.validate_video_file(Path(path))


def validate_directory(path: Union[str, Path], must_exist: bool = True,
                      must_be_writable: bool = False) -> ValidationResult:
    """Validate directory (convenience function)"""
    return Validator.validate_directory(Path(path), must_exist, must_be_writable)


def validate_config(config: AppConfig) -> ValidationResult:
    """Validate configuration (convenience function)"""
    return Validator.validate_config(config)
