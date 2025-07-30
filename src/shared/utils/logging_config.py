"""
Logging Configuration

Centralized logging setup and configuration.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any
import sys
from datetime import datetime

from ..config.app_config import AppConfig


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for better readability"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        """Format log record with colors"""
        # Add color to level name
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{level_color}{record.levelname}{self.COLORS['RESET']}"

        # Format the message
        formatted = super().format(record)

        return formatted


class LoggingConfig:
    """Logging configuration manager"""

    def __init__(self, config: AppConfig):
        """
        Initialize logging configuration.

        Args:
            config: Application configuration
        """
        self.config = config
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)

    def setup_logging(self) -> None:
        """Setup logging configuration"""
        # Get log level from config
        log_level = getattr(logging, self.config.ui.log_level.upper(), logging.INFO)

        # Create root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Clear existing handlers
        root_logger.handlers.clear()

        # Console handler with colors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        console_formatter = ColoredFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        # File handler for all logs
        log_file = self.log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file

        file_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # Error file handler for errors only
        error_file = self.log_dir / f"errors_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)

        # Setup specific loggers
        self._setup_application_loggers()

        # Log startup message
        logger = logging.getLogger(__name__)
        logger.info(f"Logging initialized - Level: {self.config.ui.log_level}")
        logger.info(f"Log files: {log_file}, {error_file}")

    def _setup_application_loggers(self) -> None:
        """Setup application-specific loggers"""
        # Video processing logger
        video_logger = logging.getLogger('video_processing')
        video_logger.setLevel(logging.INFO)

        # FFmpeg logger (usually more verbose)
        ffmpeg_logger = logging.getLogger('ffmpeg')
        ffmpeg_logger.setLevel(logging.WARNING)

        # GUI logger
        gui_logger = logging.getLogger('gui')
        gui_logger.setLevel(logging.INFO)

        # Performance logger for timing operations
        perf_logger = logging.getLogger('performance')
        perf_logger.setLevel(logging.INFO)

        # Create performance log file
        perf_file = self.log_dir / f"performance_{datetime.now().strftime('%Y%m%d')}.log"
        perf_handler = logging.handlers.RotatingFileHandler(
            perf_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=2,
            encoding='utf-8'
        )
        perf_handler.setLevel(logging.INFO)

        perf_formatter = logging.Formatter(
            fmt='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        perf_handler.setFormatter(perf_formatter)
        perf_logger.addHandler(perf_handler)
        perf_logger.propagate = False  # Don't propagate to root logger

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger with the specified name.

        Args:
            name: Logger name

        Returns:
            Logger instance
        """
        return logging.getLogger(name)

    def set_log_level(self, level: str) -> None:
        """
        Change log level at runtime.

        Args:
            level: New log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        log_level = getattr(logging, level.upper(), logging.INFO)

        # Update root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Update console handler
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                handler.setLevel(log_level)
                break

        logger = logging.getLogger(__name__)
        logger.info(f"Log level changed to: {level}")

    def cleanup_old_logs(self, days_to_keep: int = 7) -> None:
        """
        Clean up old log files.

        Args:
            days_to_keep: Number of days of logs to keep
        """
        cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)

        cleaned_count = 0
        for log_file in self.log_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_date:
                try:
                    log_file.unlink()
                    cleaned_count += 1
                except Exception as e:
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to delete old log file {log_file}: {e}")

        if cleaned_count > 0:
            logger = logging.getLogger(__name__)
            logger.info(f"Cleaned up {cleaned_count} old log files")


class PerformanceLogger:
    """Logger for performance metrics and timing"""

    def __init__(self):
        self.logger = logging.getLogger('performance')

    def log_processing_time(self, operation: str, duration: float,
                          video_path: Optional[str] = None, **kwargs) -> None:
        """
        Log processing time for an operation.

        Args:
            operation: Name of the operation
            duration: Duration in seconds
            video_path: Path to video being processed (optional)
            **kwargs: Additional metadata
        """
        metadata = {
            'operation': operation,
            'duration_seconds': round(duration, 3),
            'video_path': video_path,
            **kwargs
        }

        # Format as key=value pairs for easy parsing
        metadata_str = ' '.join(f"{k}={v}" for k, v in metadata.items() if v is not None)
        self.logger.info(f"PERFORMANCE: {metadata_str}")

    def log_memory_usage(self, operation: str, memory_mb: float, **kwargs) -> None:
        """
        Log memory usage for an operation.

        Args:
            operation: Name of the operation
            memory_mb: Memory usage in MB
            **kwargs: Additional metadata
        """
        metadata = {
            'operation': operation,
            'memory_mb': round(memory_mb, 2),
            **kwargs
        }

        metadata_str = ' '.join(f"{k}={v}" for k, v in metadata.items())
        self.logger.info(f"MEMORY: {metadata_str}")

    def log_queue_stats(self, queue_size: int, processing_count: int,
                       completed_count: int, failed_count: int) -> None:
        """
        Log queue statistics.

        Args:
            queue_size: Current queue size
            processing_count: Number of items being processed
            completed_count: Number of completed items
            failed_count: Number of failed items
        """
        self.logger.info(
            f"QUEUE: size={queue_size} processing={processing_count} "
            f"completed={completed_count} failed={failed_count}"
        )


# Global instances
_logging_config: Optional[LoggingConfig] = None
_performance_logger: Optional[PerformanceLogger] = None


def setup_logging(config: AppConfig) -> None:
    """
    Setup application logging.

    Args:
        config: Application configuration
    """
    global _logging_config
    _logging_config = LoggingConfig(config)
    _logging_config.setup_logging()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    if _logging_config:
        return _logging_config.get_logger(name)
    return logging.getLogger(name)


def get_performance_logger() -> PerformanceLogger:
    """Get performance logger instance"""
    global _performance_logger
    if _performance_logger is None:
        _performance_logger = PerformanceLogger()
    return _performance_logger


def set_log_level(level: str) -> None:
    """
    Change log level at runtime.

    Args:
        level: New log level
    """
    if _logging_config:
        _logging_config.set_log_level(level)


def cleanup_old_logs(days_to_keep: int = 7) -> None:
    """
    Clean up old log files.

    Args:
        days_to_keep: Number of days of logs to keep
    """
    if _logging_config:
        _logging_config.cleanup_old_logs(days_to_keep)
