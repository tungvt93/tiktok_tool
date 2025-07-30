"""
Base Exception Classes

Custom exception hierarchy for the video processing application.
"""

from typing import Optional, Dict, Any
from pathlib import Path


class VideoProcessingException(Exception):
    """Base exception for video processing errors"""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize exception.

        Args:
            message: Error message
            context: Additional context information
        """
        self.message = message
        self.context = context or {}
        super().__init__(message)

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context value"""
        return self.context.get(key, default)

    def add_context(self, key: str, value: Any) -> None:
        """Add context information"""
        self.context[key] = value


class VideoNotFoundException(VideoProcessingException):
    """Raised when video file is not found"""

    def __init__(self, video_path: Path, message: Optional[str] = None):
        """
        Initialize exception.

        Args:
            video_path: Path to the missing video file
            message: Custom error message
        """
        self.video_path = video_path

        if message is None:
            message = f"Video file not found: {video_path}"

        context = {'video_path': str(video_path)}
        super().__init__(message, context)


class VideoCorruptedException(VideoProcessingException):
    """Raised when video file is corrupted or unreadable"""

    def __init__(self, video_path: Path, details: Optional[str] = None):
        """
        Initialize exception.

        Args:
            video_path: Path to the corrupted video file
            details: Additional details about the corruption
        """
        self.video_path = video_path
        self.details = details

        message = f"Video file is corrupted or unreadable: {video_path}"
        if details:
            message += f" - {details}"

        context = {
            'video_path': str(video_path),
            'details': details
        }
        super().__init__(message, context)


class FFmpegException(VideoProcessingException):
    """Raised when FFmpeg command fails"""

    def __init__(self, command: str, error_output: str, return_code: int = -1):
        """
        Initialize exception.

        Args:
            command: FFmpeg command that failed
            error_output: Error output from FFmpeg
            return_code: Process return code
        """
        self.command = command
        self.error_output = error_output
        self.return_code = return_code

        message = f"FFmpeg command failed with return code {return_code}: {command}"

        context = {
            'command': command,
            'error_output': error_output,
            'return_code': return_code
        }
        super().__init__(message, context)

    def get_user_friendly_message(self) -> str:
        """Get user-friendly error message"""
        if "No such file or directory" in self.error_output:
            return "Input file not found. Please check the file path."
        elif "Permission denied" in self.error_output:
            return "Permission denied. Please check file permissions."
        elif "Disk full" in self.error_output or "No space left" in self.error_output:
            return "Not enough disk space to complete the operation."
        elif "Invalid data" in self.error_output or "corrupt" in self.error_output.lower():
            return "Input file appears to be corrupted or in an unsupported format."
        else:
            return "Video processing failed. Please check the input files and try again."


class EffectProcessingException(VideoProcessingException):
    """Raised when effect processing fails"""

    def __init__(self, effect_type: str, message: str, video_path: Optional[Path] = None):
        """
        Initialize exception.

        Args:
            effect_type: Type of effect that failed
            message: Error message
            video_path: Path to video being processed (optional)
        """
        self.effect_type = effect_type
        self.video_path = video_path

        full_message = f"Effect processing failed ({effect_type}): {message}"
        if video_path:
            full_message += f" - Video: {video_path}"

        context = {
            'effect_type': effect_type,
            'video_path': str(video_path) if video_path else None
        }
        super().__init__(full_message, context)


class ConfigurationException(VideoProcessingException):
    """Raised when configuration is invalid"""

    def __init__(self, config_section: str, validation_errors: list):
        """
        Initialize exception.

        Args:
            config_section: Configuration section that failed validation
            validation_errors: List of validation error messages
        """
        self.config_section = config_section
        self.validation_errors = validation_errors

        message = f"Configuration validation failed for {config_section}: {'; '.join(validation_errors)}"

        context = {
            'config_section': config_section,
            'validation_errors': validation_errors
        }
        super().__init__(message, context)


class ProcessingJobException(VideoProcessingException):
    """Raised when processing job encounters an error"""

    def __init__(self, job_id: str, message: str, job_status: Optional[str] = None):
        """
        Initialize exception.

        Args:
            job_id: ID of the processing job
            message: Error message
            job_status: Current job status (optional)
        """
        self.job_id = job_id
        self.job_status = job_status

        full_message = f"Processing job {job_id} failed: {message}"
        if job_status:
            full_message += f" (Status: {job_status})"

        context = {
            'job_id': job_id,
            'job_status': job_status
        }
        super().__init__(full_message, context)


class DependencyException(VideoProcessingException):
    """Raised when required dependency is missing or invalid"""

    def __init__(self, dependency_name: str, message: Optional[str] = None):
        """
        Initialize exception.

        Args:
            dependency_name: Name of the missing dependency
            message: Custom error message
        """
        self.dependency_name = dependency_name

        if message is None:
            message = f"Required dependency not found or invalid: {dependency_name}"

        context = {'dependency_name': dependency_name}
        super().__init__(message, context)


class ResourceException(VideoProcessingException):
    """Raised when system resources are insufficient"""

    def __init__(self, resource_type: str, required: str, available: str):
        """
        Initialize exception.

        Args:
            resource_type: Type of resource (memory, disk, etc.)
            required: Required amount
            available: Available amount
        """
        self.resource_type = resource_type
        self.required = required
        self.available = available

        message = f"Insufficient {resource_type}: required {required}, available {available}"

        context = {
            'resource_type': resource_type,
            'required': required,
            'available': available
        }
        super().__init__(message, context)


class CacheException(VideoProcessingException):
    """Raised when cache operations fail"""

    def __init__(self, operation: str, cache_key: Optional[str] = None,
                 message: Optional[str] = None):
        """
        Initialize exception.

        Args:
            operation: Cache operation that failed
            cache_key: Cache key involved (optional)
            message: Custom error message
        """
        self.operation = operation
        self.cache_key = cache_key

        if message is None:
            message = f"Cache operation failed: {operation}"
            if cache_key:
                message += f" (key: {cache_key})"

        context = {
            'operation': operation,
            'cache_key': cache_key
        }
        super().__init__(message, context)


class ValidationException(VideoProcessingException):
    """Raised when validation fails"""

    def __init__(self, field_name: str, value: Any, message: str):
        """
        Initialize exception.

        Args:
            field_name: Name of the field that failed validation
            value: Value that failed validation
            message: Validation error message
        """
        self.field_name = field_name
        self.value = value

        full_message = f"Validation failed for {field_name}: {message} (value: {value})"

        context = {
            'field_name': field_name,
            'value': str(value),
            'validation_message': message
        }
        super().__init__(full_message, context)


class UserCancelledException(VideoProcessingException):
    """Raised when user cancels an operation"""

    def __init__(self, operation: str, message: Optional[str] = None):
        """
        Initialize exception.

        Args:
            operation: Operation that was cancelled
            message: Custom message
        """
        self.operation = operation

        if message is None:
            message = f"Operation cancelled by user: {operation}"

        context = {'operation': operation}
        super().__init__(message, context)
