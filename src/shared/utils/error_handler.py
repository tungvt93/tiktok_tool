"""
Error Handler

Centralized error handling and user-friendly message generation.
"""

import logging
import traceback
from typing import Optional, Dict, Any, Callable, Type
from pathlib import Path

from ..exceptions.base_exceptions import (
    VideoProcessingException, VideoNotFoundException, VideoCorruptedException,
    FFmpegException, EffectProcessingException, ConfigurationException,
    ProcessingJobException, DependencyException, ResourceException,
    CacheException, ValidationException, UserCancelledException
)


class ErrorResult:
    """Result of error handling operation"""

    def __init__(self, user_message: str, technical_message: str,
                 error_code: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        """
        Initialize error result.

        Args:
            user_message: User-friendly error message
            technical_message: Technical error message for logging
            error_code: Error code for categorization
            context: Additional context information
        """
        self.user_message = user_message
        self.technical_message = technical_message
        self.error_code = error_code
        self.context = context or {}

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context value"""
        return self.context.get(key, default)


class ErrorHandler:
    """Centralized error handler"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize error handler.

        Args:
            logger: Logger instance (optional)
        """
        self.logger = logger or logging.getLogger(__name__)
        self._error_handlers: Dict[Type[Exception], Callable] = {}
        self._setup_default_handlers()

    def _setup_default_handlers(self) -> None:
        """Setup default error handlers"""
        self._error_handlers.update({
            VideoNotFoundException: self._handle_video_not_found,
            VideoCorruptedException: self._handle_video_corrupted,
            FFmpegException: self._handle_ffmpeg_error,
            EffectProcessingException: self._handle_effect_error,
            ConfigurationException: self._handle_configuration_error,
            ProcessingJobException: self._handle_job_error,
            DependencyException: self._handle_dependency_error,
            ResourceException: self._handle_resource_error,
            CacheException: self._handle_cache_error,
            ValidationException: self._handle_validation_error,
            UserCancelledException: self._handle_user_cancelled,
            FileNotFoundError: self._handle_file_not_found,
            PermissionError: self._handle_permission_error,
            OSError: self._handle_os_error,
            MemoryError: self._handle_memory_error,
            KeyboardInterrupt: self._handle_keyboard_interrupt
        })

    def handle_exception(self, exc: Exception, context: Optional[str] = None) -> ErrorResult:
        """
        Handle exception and return user-friendly result.

        Args:
            exc: Exception to handle
            context: Additional context about where the error occurred

        Returns:
            ErrorResult with user and technical messages
        """
        # Log the exception
        self._log_exception(exc, context)

        # Find appropriate handler
        handler = self._find_handler(type(exc))

        if handler:
            try:
                return handler(exc, context)
            except Exception as handler_exc:
                self.logger.error(f"Error handler failed: {handler_exc}")
                return self._handle_generic_error(exc, context)
        else:
            return self._handle_generic_error(exc, context)

    def _find_handler(self, exc_type: Type[Exception]) -> Optional[Callable]:
        """Find appropriate error handler for exception type"""
        # Check for exact match first
        if exc_type in self._error_handlers:
            return self._error_handlers[exc_type]

        # Check for parent class matches
        for registered_type, handler in self._error_handlers.items():
            if issubclass(exc_type, registered_type):
                return handler

        return None

    def _log_exception(self, exc: Exception, context: Optional[str] = None) -> None:
        """Log exception with appropriate level"""
        context_str = f" (Context: {context})" if context else ""

        if isinstance(exc, UserCancelledException):
            # User cancellation is not really an error
            self.logger.info(f"User cancelled operation: {exc}{context_str}")
        elif isinstance(exc, (ValidationException, ConfigurationException)):
            # Validation errors are usually user input issues
            self.logger.warning(f"Validation error: {exc}{context_str}")
        elif isinstance(exc, VideoProcessingException):
            # Application-specific errors
            self.logger.error(f"Video processing error: {exc}{context_str}")
        else:
            # System errors and unexpected exceptions
            self.logger.error(f"Unexpected error: {exc}{context_str}", exc_info=True)

    def register_handler(self, exc_type: Type[Exception],
                        handler: Callable[[Exception, Optional[str]], ErrorResult]) -> None:
        """
        Register custom error handler.

        Args:
            exc_type: Exception type to handle
            handler: Handler function
        """
        self._error_handlers[exc_type] = handler
        self.logger.debug(f"Registered error handler for {exc_type.__name__}")

    # Specific error handlers

    def _handle_video_not_found(self, exc: VideoNotFoundException, context: Optional[str]) -> ErrorResult:
        """Handle video not found error"""
        return ErrorResult(
            user_message=f"Video file not found: {exc.video_path.name}. Please check the file path and try again.",
            technical_message=str(exc),
            error_code="VIDEO_NOT_FOUND",
            context={'video_path': str(exc.video_path)}
        )

    def _handle_video_corrupted(self, exc: VideoCorruptedException, context: Optional[str]) -> ErrorResult:
        """Handle corrupted video error"""
        return ErrorResult(
            user_message=f"Video file '{exc.video_path.name}' appears to be corrupted or in an unsupported format. Please try a different file.",
            technical_message=str(exc),
            error_code="VIDEO_CORRUPTED",
            context={'video_path': str(exc.video_path), 'details': exc.details}
        )

    def _handle_ffmpeg_error(self, exc: FFmpegException, context: Optional[str]) -> ErrorResult:
        """Handle FFmpeg error"""
        user_message = exc.get_user_friendly_message()

        return ErrorResult(
            user_message=user_message,
            technical_message=f"FFmpeg error: {exc.command} - {exc.error_output}",
            error_code="FFMPEG_ERROR",
            context={
                'command': exc.command,
                'return_code': exc.return_code,
                'error_output': exc.error_output
            }
        )

    def _handle_effect_error(self, exc: EffectProcessingException, context: Optional[str]) -> ErrorResult:
        """Handle effect processing error"""
        return ErrorResult(
            user_message=f"Failed to apply {exc.effect_type} effect. Please try a different effect or check the input video.",
            technical_message=str(exc),
            error_code="EFFECT_ERROR",
            context={
                'effect_type': exc.effect_type,
                'video_path': str(exc.video_path) if exc.video_path else None
            }
        )

    def _handle_configuration_error(self, exc: ConfigurationException, context: Optional[str]) -> ErrorResult:
        """Handle configuration error"""
        errors_text = "; ".join(exc.validation_errors)

        return ErrorResult(
            user_message=f"Configuration error in {exc.config_section}: {errors_text}",
            technical_message=str(exc),
            error_code="CONFIG_ERROR",
            context={
                'config_section': exc.config_section,
                'validation_errors': exc.validation_errors
            }
        )

    def _handle_job_error(self, exc: ProcessingJobException, context: Optional[str]) -> ErrorResult:
        """Handle processing job error"""
        return ErrorResult(
            user_message=f"Video processing failed. Please check the input files and try again.",
            technical_message=str(exc),
            error_code="JOB_ERROR",
            context={
                'job_id': exc.job_id,
                'job_status': exc.job_status
            }
        )

    def _handle_dependency_error(self, exc: DependencyException, context: Optional[str]) -> ErrorResult:
        """Handle dependency error"""
        return ErrorResult(
            user_message=f"Required component '{exc.dependency_name}' is missing or not working properly. Please check the installation.",
            technical_message=str(exc),
            error_code="DEPENDENCY_ERROR",
            context={'dependency_name': exc.dependency_name}
        )

    def _handle_resource_error(self, exc: ResourceException, context: Optional[str]) -> ErrorResult:
        """Handle resource error"""
        if exc.resource_type.lower() == 'memory':
            user_message = "Not enough memory to complete the operation. Try closing other applications or processing smaller files."
        elif exc.resource_type.lower() == 'disk':
            user_message = "Not enough disk space to complete the operation. Please free up some space and try again."
        else:
            user_message = f"Insufficient system resources ({exc.resource_type}) to complete the operation."

        return ErrorResult(
            user_message=user_message,
            technical_message=str(exc),
            error_code="RESOURCE_ERROR",
            context={
                'resource_type': exc.resource_type,
                'required': exc.required,
                'available': exc.available
            }
        )

    def _handle_cache_error(self, exc: CacheException, context: Optional[str]) -> ErrorResult:
        """Handle cache error"""
        return ErrorResult(
            user_message="Cache operation failed. The application will continue but may be slower. Try restarting the application.",
            technical_message=str(exc),
            error_code="CACHE_ERROR",
            context={
                'operation': exc.operation,
                'cache_key': exc.cache_key
            }
        )

    def _handle_validation_error(self, exc: ValidationException, context: Optional[str]) -> ErrorResult:
        """Handle validation error"""
        return ErrorResult(
            user_message=f"Invalid {exc.field_name}: {exc.message}",
            technical_message=str(exc),
            error_code="VALIDATION_ERROR",
            context={
                'field_name': exc.field_name,
                'value': str(exc.value)
            }
        )

    def _handle_user_cancelled(self, exc: UserCancelledException, context: Optional[str]) -> ErrorResult:
        """Handle user cancellation"""
        return ErrorResult(
            user_message=f"Operation cancelled: {exc.operation}",
            technical_message=str(exc),
            error_code="USER_CANCELLED",
            context={'operation': exc.operation}
        )

    def _handle_file_not_found(self, exc: FileNotFoundError, context: Optional[str]) -> ErrorResult:
        """Handle file not found error"""
        return ErrorResult(
            user_message=f"File not found: {exc.filename}. Please check the file path.",
            technical_message=str(exc),
            error_code="FILE_NOT_FOUND",
            context={'filename': exc.filename}
        )

    def _handle_permission_error(self, exc: PermissionError, context: Optional[str]) -> ErrorResult:
        """Handle permission error"""
        return ErrorResult(
            user_message=f"Permission denied: {exc.filename}. Please check file permissions or run as administrator.",
            technical_message=str(exc),
            error_code="PERMISSION_ERROR",
            context={'filename': exc.filename}
        )

    def _handle_os_error(self, exc: OSError, context: Optional[str]) -> ErrorResult:
        """Handle OS error"""
        if exc.errno == 28:  # No space left on device
            user_message = "Not enough disk space to complete the operation."
        elif exc.errno == 13:  # Permission denied
            user_message = "Permission denied. Please check file permissions."
        else:
            user_message = f"System error occurred: {exc.strerror}"

        return ErrorResult(
            user_message=user_message,
            technical_message=str(exc),
            error_code="OS_ERROR",
            context={'errno': exc.errno, 'strerror': exc.strerror}
        )

    def _handle_memory_error(self, exc: MemoryError, context: Optional[str]) -> ErrorResult:
        """Handle memory error"""
        return ErrorResult(
            user_message="Not enough memory to complete the operation. Try closing other applications or processing smaller files.",
            technical_message=str(exc),
            error_code="MEMORY_ERROR"
        )

    def _handle_keyboard_interrupt(self, exc: KeyboardInterrupt, context: Optional[str]) -> ErrorResult:
        """Handle keyboard interrupt"""
        return ErrorResult(
            user_message="Operation interrupted by user (Ctrl+C).",
            technical_message="KeyboardInterrupt",
            error_code="USER_INTERRUPT"
        )

    def _handle_generic_error(self, exc: Exception, context: Optional[str]) -> ErrorResult:
        """Handle generic/unknown error"""
        return ErrorResult(
            user_message="An unexpected error occurred. Please try again or contact support if the problem persists.",
            technical_message=f"{type(exc).__name__}: {str(exc)}",
            error_code="UNKNOWN_ERROR",
            context={'exception_type': type(exc).__name__}
        )


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def handle_exception(exc: Exception, context: Optional[str] = None) -> ErrorResult:
    """
    Handle exception using global error handler.

    Args:
        exc: Exception to handle
        context: Additional context

    Returns:
        ErrorResult
    """
    return get_error_handler().handle_exception(exc, context)


def register_error_handler(exc_type: Type[Exception],
                          handler: Callable[[Exception, Optional[str]], ErrorResult]) -> None:
    """
    Register custom error handler.

    Args:
        exc_type: Exception type
        handler: Handler function
    """
    get_error_handler().register_handler(exc_type, handler)
