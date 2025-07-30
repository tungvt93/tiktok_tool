"""
File Repository Implementation

Concrete implementation of file system operations.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional
import glob
import logging

from ...domain.services.file_repository_interface import IFileRepository, FileSearchCriteria
from ...shared.exceptions import VideoProcessingException
from ...shared.config import PathConfig

logger = logging.getLogger(__name__)


class FileRepository(IFileRepository):
    """File system repository implementation"""

    def __init__(self, config: PathConfig):
        """
        Initialize file repository.

        Args:
            config: Path configuration
        """
        self.config = config

    def find_video_files(self, criteria: FileSearchCriteria) -> List[Path]:
        """
        Find video files matching the given criteria.

        Args:
            criteria: Search criteria for finding files

        Returns:
            List of paths to matching video files
        """
        try:
            if not criteria.directory.exists():
                logger.warning(f"Search directory does not exist: {criteria.directory}")
                return []

            if not criteria.directory.is_dir():
                logger.warning(f"Search path is not a directory: {criteria.directory}")
                return []

            # Build search pattern
            if criteria.recursive:
                pattern = str(criteria.directory / "**" / criteria.pattern)
                files = glob.glob(pattern, recursive=True)
            else:
                pattern = str(criteria.directory / criteria.pattern)
                files = glob.glob(pattern)

            # Convert to Path objects and filter
            video_files = []
            for file_path in files:
                path = Path(file_path)
                if path.is_file() and self._is_video_file(path):
                    video_files.append(path)

            # Sort files for consistent ordering
            video_files.sort()

            # Apply max results limit
            if criteria.max_results and len(video_files) > criteria.max_results:
                video_files = video_files[:criteria.max_results]
                logger.info(f"Limited results to {criteria.max_results} files")

            logger.debug(f"Found {len(video_files)} video files in {criteria.directory}")
            return video_files

        except Exception as e:
            logger.error(f"Error finding video files: {e}")
            raise VideoProcessingException(f"Failed to find video files: {e}")

    def file_exists(self, path: Path) -> bool:
        """
        Check if a file exists.

        Args:
            path: Path to check

        Returns:
            True if file exists, False otherwise
        """
        try:
            return path.exists() and path.is_file()
        except Exception as e:
            logger.warning(f"Error checking file existence {path}: {e}")
            return False

    def get_file_size(self, path: Path) -> Optional[int]:
        """
        Get file size in bytes.

        Args:
            path: Path to the file

        Returns:
            File size in bytes or None if file doesn't exist
        """
        try:
            if not self.file_exists(path):
                return None
            return path.stat().st_size
        except Exception as e:
            logger.warning(f"Error getting file size {path}: {e}")
            return None

    def create_directory(self, path: Path) -> bool:
        """
        Create directory and any necessary parent directories.

        Args:
            path: Directory path to create

        Returns:
            True if directory was created or already exists, False on error
        """
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {path}")
            return True
        except Exception as e:
            logger.error(f"Error creating directory {path}: {e}")
            return False

    def delete_file(self, path: Path) -> bool:
        """
        Delete a file.

        Args:
            path: Path to the file to delete

        Returns:
            True if file was deleted, False on error
        """
        try:
            if not self.file_exists(path):
                logger.warning(f"Cannot delete non-existent file: {path}")
                return False

            path.unlink()
            logger.debug(f"Deleted file: {path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file {path}: {e}")
            return False

    def copy_file(self, source: Path, destination: Path) -> bool:
        """
        Copy a file from source to destination.

        Args:
            source: Source file path
            destination: Destination file path

        Returns:
            True if file was copied successfully, False on error
        """
        try:
            if not self.file_exists(source):
                logger.error(f"Source file does not exist: {source}")
                return False

            # Create destination directory if needed
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(source, destination)
            logger.debug(f"Copied file: {source} -> {destination}")
            return True
        except Exception as e:
            logger.error(f"Error copying file {source} -> {destination}: {e}")
            return False

    def move_file(self, source: Path, destination: Path) -> bool:
        """
        Move a file from source to destination.

        Args:
            source: Source file path
            destination: Destination file path

        Returns:
            True if file was moved successfully, False on error
        """
        try:
            if not self.file_exists(source):
                logger.error(f"Source file does not exist: {source}")
                return False

            # Create destination directory if needed
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Move file
            shutil.move(str(source), str(destination))
            logger.debug(f"Moved file: {source} -> {destination}")
            return True
        except Exception as e:
            logger.error(f"Error moving file {source} -> {destination}: {e}")
            return False

    def get_available_space(self, path: Path) -> Optional[int]:
        """
        Get available disk space at the given path.

        Args:
            path: Path to check (file or directory)

        Returns:
            Available space in bytes or None on error
        """
        try:
            # Get the directory containing the path
            if path.is_file():
                check_path = path.parent
            else:
                check_path = path

            # Get disk usage statistics
            stat = shutil.disk_usage(check_path)
            return stat.free
        except Exception as e:
            logger.warning(f"Error getting available space for {path}: {e}")
            return None

    def is_writable(self, path: Path) -> bool:
        """
        Check if a path is writable.

        Args:
            path: Path to check

        Returns:
            True if path is writable, False otherwise
        """
        try:
            if path.exists():
                # Check existing path
                return os.access(path, os.W_OK)
            else:
                # Check parent directory for new files
                parent = path.parent
                return parent.exists() and os.access(parent, os.W_OK)
        except Exception as e:
            logger.warning(f"Error checking write access for {path}: {e}")
            return False

    def _is_video_file(self, path: Path) -> bool:
        """
        Check if file is a video file based on extension.

        Args:
            path: File path to check

        Returns:
            True if file appears to be a video file
        """
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        return path.suffix.lower() in video_extensions

    def cleanup_temp_files(self, temp_dir: Optional[Path] = None) -> int:
        """
        Clean up temporary files.

        Args:
            temp_dir: Temporary directory to clean (optional, uses config default)

        Returns:
            Number of files cleaned up
        """
        if temp_dir is None:
            temp_dir = self.config.temp_dir

        if not temp_dir.exists():
            return 0

        cleaned_count = 0
        try:
            # Clean up common temp file patterns
            temp_patterns = [
                "temp_*.mp4",
                "temp_*.avi",
                "*.tmp",
                "ffmpeg_*.log",
                "processing_*.temp"
            ]

            for pattern in temp_patterns:
                for temp_file in temp_dir.glob(pattern):
                    try:
                        if temp_file.is_file():
                            temp_file.unlink()
                            cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to delete temp file {temp_file}: {e}")

            logger.info(f"Cleaned up {cleaned_count} temporary files")
            return cleaned_count

        except Exception as e:
            logger.error(f"Error during temp file cleanup: {e}")
            return cleaned_count

    def get_directory_size(self, directory: Path) -> Optional[int]:
        """
        Get total size of directory and all its contents.

        Args:
            directory: Directory to measure

        Returns:
            Total size in bytes or None on error
        """
        try:
            if not directory.exists() or not directory.is_dir():
                return None

            total_size = 0
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    try:
                        total_size += file_path.stat().st_size
                    except Exception:
                        # Skip files we can't read
                        continue

            return total_size
        except Exception as e:
            logger.warning(f"Error calculating directory size {directory}: {e}")
            return None
