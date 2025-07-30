"""
Pytest Configuration

Global test configuration and fixtures.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock

from src.shared.config import AppConfig, VideoProcessingConfig, FFmpegConfig, PathConfig, PerformanceConfig, UIConfig
from src.domain.entities.video import Video
from src.domain.entities.effect import Effect
from src.domain.entities.processing_job import ProcessingJob
from src.domain.value_objects.dimensions import Dimensions
from src.domain.value_objects.effect_type import EffectType
from src.domain.value_objects.job_status import JobStatus


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_config(temp_dir):
    """Create test configuration"""
    return AppConfig(
        video=VideoProcessingConfig(
            output_width=1080,
            output_height=1080,
            speed_multiplier=1.3,
            frame_rate=10,
            crf_value=23,
            default_effect_duration=2.0
        ),
        ffmpeg=FFmpegConfig(
            preset="ultrafast",
            codec_video="libx264",
            codec_audio="aac",
            threads="0"
        ),
        paths=PathConfig(
            input_dir=temp_dir / "input",
            background_dir=temp_dir / "background",
            output_dir=temp_dir / "output",
            effects_dir=temp_dir / "effects",
            generated_effects_dir=temp_dir / "generated_effects",
            temp_dir=temp_dir / "temp"
        ),
        performance=PerformanceConfig(
            max_workers=2,
            cache_enabled=True,
            cache_file=str(temp_dir / "test_cache.json"),
            memory_limit_mb=None
        ),
        ui=UIConfig(
            theme="dark",
            window_width=1400,
            window_height=800,
            auto_refresh_interval=5,
            show_preview=True,
            log_level="DEBUG"
        )
    )


@pytest.fixture
def sample_video(temp_dir):
    """Create sample video entity"""
    video_path = temp_dir / "sample_video.mp4"
    video_path.touch()  # Create empty file

    return Video(
        path=video_path,
        duration=60.0,
        dimensions=Dimensions(1920, 1080),
        metadata={
            'codec': 'h264',
            'bitrate': 5000000,
            'file_size': 10485760  # 10MB
        }
    )


@pytest.fixture
def sample_background_video(temp_dir):
    """Create sample background video entity"""
    video_path = temp_dir / "background_video.mp4"
    video_path.touch()  # Create empty file

    return Video(
        path=video_path,
        duration=120.0,
        dimensions=Dimensions(1920, 1080),
        metadata={
            'codec': 'h264',
            'bitrate': 3000000,
            'file_size': 20971520  # 20MB
        }
    )


@pytest.fixture
def sample_effect():
    """Create sample effect entity"""
    return Effect(
        type=EffectType.FADE_IN,
        duration=2.0,
        parameters={'color': 'black', 'alpha': 1.0}
    )


@pytest.fixture
def sample_processing_job(sample_video, sample_background_video, sample_effect, temp_dir):
    """Create sample processing job"""
    output_path = temp_dir / "output" / "processed_video.mp4"

    return ProcessingJob(
        main_video=sample_video,
        background_video=sample_background_video,
        effects=[sample_effect],
        output_path=output_path,
        status=JobStatus.PENDING
    )


@pytest.fixture
def mock_video_processor():
    """Create mock video processor"""
    processor = Mock()
    processor.process_video.return_value = Mock(
        is_success=Mock(return_value=True),
        output_path=Path("output.mp4"),
        get_error=Mock(return_value=None)
    )
    processor.get_video_info.return_value = Mock(
        duration=60.0,
        dimensions=Dimensions(1920, 1080),
        codec="h264",
        bitrate=5000000,
        metadata={}
    )
    processor.validate_video_file.return_value = True
    processor.estimate_processing_time.return_value = 30.0
    processor.cancel_processing.return_value = True

    return processor


@pytest.fixture
def mock_file_repository():
    """Create mock file repository"""
    repository = Mock()
    repository.find_video_files.return_value = []
    repository.file_exists.return_value = True
    repository.get_file_size.return_value = 10485760
    repository.create_directory.return_value = True
    repository.delete_file.return_value = True
    repository.copy_file.return_value = True
    repository.move_file.return_value = True
    repository.get_available_space.return_value = 1073741824  # 1GB
    repository.is_writable.return_value = True

    return repository


@pytest.fixture
def mock_video_repository():
    """Create mock video repository"""
    repository = Mock()
    repository.get_by_path.return_value = None
    repository.get_all.return_value = []
    repository.save.return_value = True
    repository.delete.return_value = True
    repository.exists.return_value = False
    repository.get_cached_videos.return_value = []
    repository.clear_cache.return_value = True
    repository.refresh_video.return_value = None
    repository.get_videos_by_directory.return_value = []
    repository.get_total_duration.return_value = 0.0

    return repository


@pytest.fixture
def mock_cache_service():
    """Create mock cache service"""
    service = Mock()
    service.get.return_value = None
    service.set.return_value = True
    service.delete.return_value = True
    service.exists.return_value = False
    service.clear.return_value = True
    service.get_keys.return_value = []
    service.get_stats.return_value = {
        'enabled': True,
        'total_entries': 0,
        'hits': 0,
        'misses': 0,
        'hit_rate_percent': 0.0
    }
    service.cleanup_expired.return_value = 0
    service.get_entry.return_value = None
    service.set_multiple.return_value = 0
    service.get_multiple.return_value = {}

    return service


@pytest.fixture
def mock_effect_processors():
    """Create mock effect processors"""
    processors = []

    # Slide effect processor
    slide_processor = Mock()
    slide_processor.can_handle.side_effect = lambda effect_type: effect_type.is_slide_effect()
    slide_processor.get_supported_effects.return_value = EffectType.get_slide_effects()
    slide_processor.apply_effect.return_value = Mock(success=True, processing_time=5.0)
    slide_processor.validate_effect_parameters.return_value = []
    slide_processor.estimate_processing_time.return_value = 5.0
    slide_processor.get_processor_name.return_value = "Slide Effect Processor"
    processors.append(slide_processor)

    # Circle effect processor
    circle_processor = Mock()
    circle_processor.can_handle.side_effect = lambda effect_type: effect_type.is_circle_effect()
    circle_processor.get_supported_effects.return_value = EffectType.get_circle_effects()
    circle_processor.apply_effect.return_value = Mock(success=True, processing_time=8.0)
    circle_processor.validate_effect_parameters.return_value = []
    circle_processor.estimate_processing_time.return_value = 8.0
    circle_processor.get_processor_name.return_value = "Circle Effect Processor"
    processors.append(circle_processor)

    # Fade effect processor
    fade_processor = Mock()
    fade_processor.can_handle.side_effect = lambda effect_type: effect_type == EffectType.FADE_IN
    fade_processor.get_supported_effects.return_value = [EffectType.FADE_IN]
    fade_processor.apply_effect.return_value = Mock(success=True, processing_time=3.0)
    fade_processor.validate_effect_parameters.return_value = []
    fade_processor.estimate_processing_time.return_value = 3.0
    fade_processor.get_processor_name.return_value = "Fade Effect Processor"
    processors.append(fade_processor)

    return processors


@pytest.fixture(autouse=True)
def setup_test_logging():
    """Setup logging for tests"""
    import logging
    logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')


@pytest.fixture
def create_test_video_file():
    """Factory fixture for creating test video files"""
    def _create_video_file(temp_dir: Path, filename: str, duration: float = 60.0,
                          width: int = 1920, height: int = 1080) -> Video:
        video_path = temp_dir / filename
        video_path.touch()  # Create empty file

        return Video(
            path=video_path,
            duration=duration,
            dimensions=Dimensions(width, height),
            metadata={
                'codec': 'h264',
                'bitrate': 5000000,
                'file_size': video_path.stat().st_size
            }
        )

    return _create_video_file


@pytest.fixture
def create_test_effect():
    """Factory fixture for creating test effects"""
    def _create_effect(effect_type: EffectType = EffectType.FADE_IN,
                      duration: float = 2.0, **parameters) -> Effect:
        return Effect(
            type=effect_type,
            duration=duration,
            parameters=parameters
        )

    return _create_effect


# Pytest markers
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "requires_ffmpeg: Tests that require FFmpeg")


# Test data constants
TEST_VIDEO_FORMATS = ['.mp4', '.avi', '.mov', '.mkv']
TEST_EFFECT_TYPES = list(EffectType)
TEST_JOB_STATUSES = list(JobStatus)
