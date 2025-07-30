"""
Unit Tests for Video Entity

Tests for the Video domain entity.
"""

import pytest
from pathlib import Path
from datetime import datetime

from src.domain.entities.video import Video
from src.domain.value_objects.dimensions import Dimensions


class TestVideoEntity:
    """Test cases for Video entity"""

    def test_video_creation_with_valid_data(self, temp_dir):
        """Test creating video with valid data"""
        video_path = temp_dir / "test_video.mp4"
        video_path.touch()

        video = Video(
            path=video_path,
            duration=60.0,
            dimensions=Dimensions(1920, 1080),
            metadata={'codec': 'h264'}
        )

        assert video.path == video_path
        assert video.duration == 60.0
        assert video.dimensions.width == 1920
        assert video.dimensions.height == 1080
        assert video.metadata['codec'] == 'h264'
        assert isinstance(video.created_at, datetime)

    def test_video_creation_with_nonexistent_file(self, temp_dir):
        """Test creating video with nonexistent file raises error"""
        video_path = temp_dir / "nonexistent.mp4"

        with pytest.raises(ValueError, match="Video file does not exist"):
            Video(
                path=video_path,
                duration=60.0,
                dimensions=Dimensions(1920, 1080)
            )

    def test_video_creation_with_invalid_duration(self, temp_dir):
        """Test creating video with invalid duration raises error"""
        video_path = temp_dir / "test_video.mp4"
        video_path.touch()

        with pytest.raises(ValueError, match="Duration must be positive"):
            Video(
                path=video_path,
                duration=-10.0,
                dimensions=Dimensions(1920, 1080)
            )

    def test_video_creation_with_unsupported_format(self, temp_dir):
        """Test creating video with unsupported format raises error"""
        video_path = temp_dir / "test_video.txt"
        video_path.touch()

        with pytest.raises(ValueError, match="Unsupported video format"):
            Video(
                path=video_path,
                duration=60.0,
                dimensions=Dimensions(1920, 1080)
            )

    def test_video_properties(self, sample_video):
        """Test video properties"""
        assert sample_video.filename == "sample_video.mp4"
        assert sample_video.extension == ".mp4"
        assert sample_video.get_display_name() == "sample_video"
        assert sample_video.file_size > 0

    def test_video_metadata_operations(self, sample_video):
        """Test video metadata operations"""
        # Test getting metadata
        assert sample_video.get_metadata_value('codec') == 'h264'
        assert sample_video.get_metadata_value('nonexistent', 'default') == 'default'

        # Test setting metadata
        sample_video.set_metadata_value('new_key', 'new_value')
        assert sample_video.get_metadata_value('new_key') == 'new_value'

    def test_video_caching_operations(self, sample_video):
        """Test video caching operations"""
        # Initially not cached
        assert not sample_video.is_cached()
        assert sample_video.cached_at is None

        # Mark as cached
        sample_video.mark_as_cached()
        assert sample_video.is_cached()
        assert sample_video.cached_at is not None

    def test_video_equality(self, temp_dir):
        """Test video equality based on path"""
        video_path = temp_dir / "test_video.mp4"
        video_path.touch()

        video1 = Video(
            path=video_path,
            duration=60.0,
            dimensions=Dimensions(1920, 1080)
        )

        video2 = Video(
            path=video_path,
            duration=120.0,  # Different duration
            dimensions=Dimensions(1280, 720)  # Different dimensions
        )

        # Should be equal because same path
        assert video1 == video2
        assert hash(video1) == hash(video2)

    def test_video_string_representation(self, sample_video):
        """Test video string representation"""
        str_repr = str(sample_video)
        assert "sample_video.mp4" in str_repr
        assert "60.0s" in str_repr
        assert "1920x1080" in str_repr
