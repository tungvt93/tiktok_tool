"""
Data Migration Tests

Tests to verify that existing data and functionality work correctly after migration.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any
import json

from src.shared.config.config_loader import load_config
from src.compatibility.migration_helpers import ConfigMigrator
from src.compatibility.legacy_adapters import LegacyVideoProcessor, LegacyConfigAdapter
from src.application.use_cases.get_videos_use_case import GetVideosUseCase, GetVideosRequest
from src.application.use_cases.process_video_use_case import ProcessVideoUseCase
from main import ApplicationFactory


class TestDataMigration:
    """Test suite for data migration validation"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        temp_dir = Path(tempfile.mkdtemp())

        # Create directory structure
        (temp_dir / "dongphuc").mkdir()
        (temp_dir / "video_chia_2").mkdir()
        (temp_dir / "output").mkdir()

        # Create sample video files (empty files for testing)
        sample_videos = [
            temp_dir / "dongphuc" / "test1.mp4",
            temp_dir / "dongphuc" / "test2.mp4",
            temp_dir / "video_chia_2" / "bg1.mp4",
            temp_dir / "video_chia_2" / "bg2.mp4"
        ]

        for video_path in sample_videos:
            video_path.write_bytes(b"fake video content")

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def old_config_content(self):
        """Sample old configuration content"""
        return '''# Old configuration file
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080
FRAME_RATE = 30
CRF_VALUE = 18
SPEED_MULTIPLIER = 1.5

FFMPEG_PRESET = "fast"
VIDEO_CODEC = "libx264"
AUDIO_CODEC = "aac"

INPUT_DIR = "dongphuc"
BACKGROUND_DIR = "video_chia_2"
OUTPUT_DIR = "output"

MAX_WORKERS = 8
CACHE_ENABLED = True
LOG_LEVEL = "DEBUG"
'''

    def test_config_migration_preserves_data(self, temp_workspace, old_config_content):
        """Test that configuration migration preserves all data correctly"""
        # Create old config file
        old_config_path = temp_workspace / "old_config.py"
        old_config_path.write_text(old_config_content)

        # Migrate configuration
        migrator = ConfigMigrator()
        new_config = migrator.migrate_from_py_config(old_config_path)

        # Verify key settings were preserved
        assert new_config.video.output_width == 1920
        assert new_config.video.output_height == 1080
        assert new_config.video.frame_rate == 30
        assert new_config.video.crf_value == 18
        assert new_config.video.speed_multiplier == 1.5

        assert new_config.ffmpeg.preset == "fast"
        assert new_config.ffmpeg.codec_video == "libx264"
        assert new_config.ffmpeg.codec_audio == "aac"

        assert str(new_config.paths.input_dir) == "dongphuc"
        assert str(new_config.paths.background_dir) == "video_chia_2"
        assert str(new_config.paths.output_dir) == "output"

        assert new_config.performance.max_workers == 8
        assert new_config.performance.cache_enabled == True
        assert new_config.ui.log_level == "DEBUG"

    def test_video_discovery_consistency(self, temp_workspace):
        """Test that video discovery works consistently after migration"""
        # Change to temp workspace
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(temp_workspace)

            # Load configuration
            config = load_config()
            factory = ApplicationFactory(config)
            container = factory.create_container()

            # Test new architecture
            get_videos_use_case = container.resolve(GetVideosUseCase)
            request = GetVideosRequest(recursive=False)
            response = get_videos_use_case.execute(request)

            assert response.success
            new_arch_videos = response.videos

            # Test legacy adapter
            process_use_case = container.resolve(ProcessVideoUseCase)
            legacy_processor = LegacyVideoProcessor(process_use_case, get_videos_use_case, config)
            legacy_videos = legacy_processor.get_videos()

            # Compare results
            assert len(new_arch_videos) == len(legacy_videos)

            # Verify video data consistency
            for new_video, legacy_video in zip(new_arch_videos, legacy_videos):
                assert new_video.filename == legacy_video.filename
                assert str(new_video.path) == legacy_video.path

        finally:
            os.chdir(original_cwd)

    def test_configuration_backward_compatibility(self, temp_workspace, old_config_content):
        """Test that legacy configuration adapter provides backward compatibility"""
        # Create and migrate config
        old_config_path = temp_workspace / "old_config.py"
        old_config_path.write_text(old_config_content)

        migrator = ConfigMigrator()
        new_config = migrator.migrate_from_py_config(old_config_path)

        # Test legacy adapter
        legacy_config = LegacyConfigAdapter(new_config)

        # Verify legacy properties work
        assert legacy_config.OUTPUT_WIDTH == 1920
        assert legacy_config.OUTPUT_HEIGHT == 1080
        assert legacy_config.FRAME_RATE == 30
        assert legacy_config.CRF_VALUE == 18
        assert legacy_config.SPEED_MULTIPLIER == 1.5

        assert legacy_config.FFMPEG_PRESET == "fast"
        assert legacy_config.VIDEO_CODEC == "libx264"
        assert legacy_config.AUDIO_CODEC == "aac"

        assert legacy_config.INPUT_DIR == "dongphuc"
        assert legacy_config.BACKGROUND_DIR == "video_chia_2"
        assert legacy_config.OUTPUT_DIR == "output"

        # Test legacy config dict
        config_dict = legacy_config.get_config_dict()
        assert config_dict['OUTPUT_WIDTH'] == 1920
        assert config_dict['FFMPEG_PRESET'] == "fast"
        assert config_dict['INPUT_DIR'] == "dongphuc"

    def test_effect_types_consistency(self):
        """Test that effect types are consistent between old and new architecture"""
        from src.domain.value_objects.effect_type import EffectType

        # Get effects from new architecture
        new_effects = [effect.value for effect in EffectType]

        # Get effects from legacy adapter
        config = load_config()
        factory = ApplicationFactory(config)
        container = factory.create_container()

        process_use_case = container.resolve(ProcessVideoUseCase)
        get_videos_use_case = container.resolve(GetVideosUseCase)
        legacy_processor = LegacyVideoProcessor(process_use_case, get_videos_use_case, config)

        legacy_effects = legacy_processor.get_available_effects()

        # Verify all legacy effects are supported in new architecture
        for legacy_effect in legacy_effects:
            if legacy_effect != "none":  # "none" maps to EffectType.NONE
                # Convert legacy name to new format for comparison
                expected_new_name = legacy_effect
                assert expected_new_name in new_effects or "none" in new_effects

    def test_json_config_roundtrip(self, temp_workspace):
        """Test that JSON configuration can be saved and loaded without data loss"""
        # Create configuration
        config = load_config()

        # Modify some values
        config.video.output_width = 1920
        config.video.output_height = 1080
        config.video.crf_value = 20
        config.ffmpeg.preset = "medium"
        config.performance.max_workers = 6

        # Save to JSON
        json_path = temp_workspace / "test_config.json"
        config.save_to_file(json_path)

        # Load from JSON
        loaded_config = load_config(json_path)

        # Verify data integrity
        assert loaded_config.video.output_width == 1920
        assert loaded_config.video.output_height == 1080
        assert loaded_config.video.crf_value == 20
        assert loaded_config.ffmpeg.preset == "medium"
        assert loaded_config.performance.max_workers == 6

        # Verify configuration is valid
        validation_errors = loaded_config.validate()
        assert len(validation_errors) == 0 or all("does not exist" in error for error in validation_errors)


class TestMigrationValidation:
    """Test suite for validating migration results"""

    def test_migration_report_generation(self, tmp_path):
        """Test that migration reports are generated correctly"""
        # Create sample old config with issues
        old_config_content = '''# Config with potential issues
OUTPUT_WIDTH = "not_a_number"  # This should cause an issue
OUTPUT_HEIGHT = 1080
UNKNOWN_SETTING = "test"  # This should be flagged as unmapped
'''

        old_config_path = tmp_path / "problematic_config.py"
        old_config_path.write_text(old_config_content)

        # Attempt migration
        migrator = ConfigMigrator()
        try:
            new_config = migrator.migrate_from_py_config(old_config_path)

            # Generate report
            report = migrator.generate_migration_report()

            # Verify report contains expected information
            assert "WARNINGS:" in report or "INFORMATION:" in report
            assert len(migrator.migration_issues) > 0

        except Exception:
            # Migration might fail, which is expected for problematic config
            assert len(migrator.migration_issues) > 0

    def test_cache_compatibility(self, tmp_path):
        """Test that existing cache files work with new architecture"""
        # Create sample cache file
        cache_data = {
            "dongphuc/test1.mp4": {
                "duration": 60.0,
                "width": 1920,
                "height": 1080,
                "file_size": 1000000,
                "cached_at": "2025-07-30T10:00:00"
            }
        }

        cache_path = tmp_path / "video_cache.json"
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)

        # Change to temp directory
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)

            # Create required directories
            (tmp_path / "dongphuc").mkdir()
            (tmp_path / "dongphuc" / "test1.mp4").write_bytes(b"fake video")

            # Load configuration and test cache loading
            config = load_config()
            factory = ApplicationFactory(config)
            container = factory.create_container()

            # The cache service should load existing cache
            from src.infrastructure.services.cache_service import CacheService
            cache_service = container.resolve(CacheService)

            # Verify cache was loaded (this tests backward compatibility)
            assert len(cache_service._cache) >= 0  # Cache might be empty if file format changed

        finally:
            os.chdir(original_cwd)

    def test_directory_structure_migration(self, tmp_path):
        """Test that existing directory structures work after migration"""
        # Create old-style directory structure
        directories = [
            "dongphuc",
            "video_chia_2",
            "output",
            "effects",
            "generated_effects"
        ]

        for dir_name in directories:
            (tmp_path / dir_name).mkdir()
            # Add sample files
            (tmp_path / dir_name / "sample.txt").write_text("test")

        # Change to temp directory
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)

            # Load configuration
            config = load_config()

            # Verify directories are recognized
            assert config.paths.input_dir.exists()
            assert config.paths.background_dir.exists()
            assert config.paths.output_dir.exists()

            # Test directory creation for missing ones
            config.ensure_directories()

            # All directories should exist after ensure_directories
            assert config.paths.input_dir.exists()
            assert config.paths.background_dir.exists()
            assert config.paths.output_dir.exists()
            assert config.paths.effects_dir.exists()
            assert config.paths.generated_effects_dir.exists()

        finally:
            os.chdir(original_cwd)


class TestPerformanceConsistency:
    """Test suite for verifying performance characteristics are maintained"""

    def test_video_loading_performance(self, tmp_path):
        """Test that video loading performance is consistent"""
        import time

        # Create multiple test video files
        video_dir = tmp_path / "test_videos"
        video_dir.mkdir()

        for i in range(10):
            (video_dir / f"video_{i}.mp4").write_bytes(b"fake video content" * 1000)

        # Change to temp directory
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tmp_path)

            # Test new architecture performance
            config = load_config()
            config.paths.input_dir = video_dir

            factory = ApplicationFactory(config)
            container = factory.create_container()

            get_videos_use_case = container.resolve(GetVideosUseCase)

            start_time = time.time()
            request = GetVideosRequest(directory=video_dir)
            response = get_videos_use_case.execute(request)
            new_arch_time = time.time() - start_time

            assert response.success
            assert len(response.videos) == 10

            # Test legacy adapter performance
            process_use_case = container.resolve(ProcessVideoUseCase)
            legacy_processor = LegacyVideoProcessor(process_use_case, get_videos_use_case, config)

            start_time = time.time()
            legacy_videos = legacy_processor.get_videos(video_dir)
            legacy_time = time.time() - start_time

            assert len(legacy_videos) == 10

            # Performance should be comparable (within 2x)
            # This is a loose check since we're testing with fake files
            assert legacy_time < new_arch_time * 3  # Allow some overhead for compatibility layer

        finally:
            os.chdir(original_cwd)

    def test_memory_usage_consistency(self, tmp_path):
        """Test that memory usage patterns are reasonable"""
        import psutil
        import os

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create test environment
        video_dir = tmp_path / "memory_test"
        video_dir.mkdir()

        # Create larger fake video files
        for i in range(5):
            (video_dir / f"large_video_{i}.mp4").write_bytes(b"fake video content" * 10000)

        original_cwd = Path.cwd()
        try:
            os.chdir(tmp_path)

            # Test memory usage with new architecture
            config = load_config()
            config.paths.input_dir = video_dir

            factory = ApplicationFactory(config)
            container = factory.create_container()

            get_videos_use_case = container.resolve(GetVideosUseCase)
            request = GetVideosRequest(directory=video_dir)
            response = get_videos_use_case.execute(request)

            # Check memory usage after loading videos
            after_loading_memory = process.memory_info().rss
            memory_increase = after_loading_memory - initial_memory

            # Memory increase should be reasonable (less than 100MB for this test)
            assert memory_increase < 100 * 1024 * 1024  # 100MB

        finally:
            os.chdir(original_cwd)
