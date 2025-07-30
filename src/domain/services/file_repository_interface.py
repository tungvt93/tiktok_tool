"""
File Repository Interface

Defines the contract for file system operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path

from ..entities.video import Video


class FileSearchCriteria:
    """Criteria for searching files"""

    def __init__(self, directory: Path, pattern: str = "*.mp4",
                 recursive: bool = False, max_results: Optional[int] = None):
        self.directory = directory
        self.pattern = pattern
        self.recursive = recursive
        self.max_results = max_results


class IFileRepository(ABC):
    """Interface for file system operations"""

    @abstractmethod
    def find_video_files(self, criteria: FileSearchCriteria) -> List[Path]:
        """
        Find video files matching the given criteria.

        Args:
            criteria: Search criteria for finding files

        Returns:
            List of paths to matching video files
        """
    @abstractmethod
    def file_exists(self, path: Path) -> bool:
        """
        Check if a file exists.

        Args:
            path: Path to check

        Returns:
            True if file exists, False otherwise
        """
    @abstractmethod
    def get_file_size(self, path: Path) -> Optional[int]:
        """
        Get file size in bytes.

        Args:
            path: Path to the file

        Returns:
            File size in bytes or None if file doesn't exist
        """
    @abstractmethod
    def create_directory(self, path: Path) -> bool:
        """
        Create directory and any necessary parent directories.

        Args:
            path: Directory path to create

        Returns:
            True if directory was created or already exists, False on error
        """
    @abstractmethod
    def delete_file(self, path: Path) -> bool:
        """
        Delete a file.

        Args:
            path: Path to the file to delete

        Returns:
            True if file was deleted, False on error
        """
    @abstractmethod
    def copy_file(self, source: Path, destination: Path) -> bool:
        """
        Copy a file from source to destination.

        Args:
            source: Source file path
            destination: Destination file path

        Returns:
            True if file was copied successfully, False on error
        """
    @abstractmethod
    def move_file(self, source: Path, destination: Path) -> bool:
        """
        Move a file from source to destination.

        Args:
            source: Source file path
            destination: Destination file path

        Returns:
            True if file was moved successfully, False on error
        """
    @abstractmethod
    def get_available_space(self, path: Path) -> Optional[int]:
        """
        Get available disk space at the given path.

        Args:
            path: Path to check (file or directory)

        Returns:
            Available space in bytes or None on error
        """
    @abstractmethod
    def is_writable(self, path: Path) -> bool:
        """
        Check if a path is writable.

        Args:
            path: Path to check

        Returns:
            True if path is writable, False otherwise
        """
        pass
