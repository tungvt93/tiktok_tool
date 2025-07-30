"""
Shared Utilities

Common utilities for logging, validation, error handling, and other
cross-cutting concerns.
"""

from .logging_config import setup_logging, get_logger, get_performance_logger, set_log_level, cleanup_old_logs
from .validation import Validator, ValidationResult, ValidationError, validate_video_file, validate_directory, validate_config
from .error_handler import ErrorHandler, ErrorResult, handle_exception, register_error_handler, get_error_handler

__all__ = [
    # Logging
    'setup_logging',
    'get_logger',
    'get_performance_logger',
    'set_log_level',
    'cleanup_old_logs',
    # Validation
    'Validator',
    'ValidationResult',
    'ValidationError',
    'validate_video_file',
    'validate_directory',
    'validate_config',
    # Error handling
    'ErrorHandler',
    'ErrorResult',
    'handle_exception',
    'register_error_handler',
    'get_error_handler'
]
