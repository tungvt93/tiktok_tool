# Developer Guide

This guide provides detailed information for developers who want to extend or modify the TikTok Video Processing Tool.

## Architecture Overview

The application follows Clean Architecture principles with clear separation of concerns:

### Layer Dependencies

```
Presentation Layer → Application Layer → Domain Layer
Infrastructure Layer → Application Layer
```

**Key Rules:**

- Dependencies point inward toward the domain
- Domain layer has no external dependencies
- Infrastructure implements interfaces defined in domain
- Application orchestrates business logic

### Directory Structure

```
src/
├── domain/                 # Core business logic (no external dependencies)
│   ├── entities/          # Business entities (Video, Effect, ProcessingJob)
│   ├── services/          # Domain service interfaces
│   └── value_objects/     # Immutable value objects (EffectType, Dimensions)
├── application/           # Use cases and application services
│   ├── models/           # Data transfer objects
│   ├── services/         # Application services (orchestration)
│   └── use_cases/        # Business use cases
├── infrastructure/       # External dependencies and implementations
│   ├── processors/       # Effect processors (FFmpeg implementations)
│   ├── repositories/     # Data access implementations
│   └── services/         # External service implementations
├── presentation/         # User interfaces
│   ├── cli/             # Command-line interface
│   ├── gui/             # Graphical user interface
│   └── common/          # Shared UI components
└── shared/              # Cross-cutting concerns
    ├── config/          # Configuration management
    ├── exceptions/      # Exception hierarchy
    └── utils/           # Utilities and helpers
```

## Adding New Effects

### Step 1: Define Effect Type

Add your effect to the `EffectType` enum:

```python
# src/domain/value_objects/effect_type.py
class EffectType(Enum):
    # ... existing effects
    MY_CUSTOM_EFFECT = "my_custom_effect"

    @classmethod
    def get_custom_effects(cls) -> list['EffectType']:
        """Get all custom effects"""
        return [cls.MY_CUSTOM_EFFECT]
```

### Step 2: Create Effect Processor

Implement the `IEffectProcessor` interface:

```python
# src/infrastructure/processors/my_custom_effect_processor.py
from typing import Dict, Any
from pathlib import Path

from ...domain.entities.video import Video
from ...domain.entities.effect import Effect
from ...domain.services.effect_processor_interface import IEffectProcessor
from ...domain.value_objects.effect_type import EffectType
from ...shared.config.video_config import FFmpegConfig
from ...shared.utils import get_logger

logger = get_logger(__name__)

class MyCustomEffectProcessor(IEffectProcessor):
    """Processor for custom effects"""

    def __init__(self, ffmpeg_config: FFmpegConfig):
        """
        Initialize processor.

        Args:
            ffmpeg_config: FFmpeg configuration
        """
        self.ffmpeg_config = ffmpeg_config

    def can_handle(self, effect_type: EffectType) -> bool:
        """Check if this processor can handle the effect type"""
        return effect_type == EffectType.MY_CUSTOM_EFFECT

    def apply(self, video: Video, effect: Effect) -> Video:
        """
        Apply the custom effect to video.

        Args:
            video: Input video
            effect: Effect configuration

        Returns:
            Processed video
        """
        logger.info(f"Applying custom effect to {video.filename}")

        # Build FFmpeg command
        command = self._build_ffmpeg_command(video, effect)

        # Execute command
        result = self._execute_ffmpeg(command)

        if not result.success:
            raise EffectProcessingException(f"Custom effect failed: {result.error}")

        return result.output_video

    def _build_ffmpeg_command(self, video: Video, effect: Effect) -> List[str]:
        """Build FFmpeg command for custom effect"""
        duration = effect.duration

        # Example: Custom filter implementation
        filter_complex = f"[0:v]custom_filter=duration={duration}[v]"

        command = [
            'ffmpeg',
            '-i', str(video.path),
            '-filter_complex', filter_complex,
            '-map', '[v]',
            '-c:v', self.ffmpeg_config.codec_video,
            '-preset', self.ffmpeg_config.preset,
            '-y',  # Overwrite output
            str(video.output_path)
        ]

        return command

    def _execute_ffmpeg(self, command: List[str]) -> ProcessingResult:
        """Execute FFmpeg command"""
        # Implementation similar to other processors
        pass
```

### Step 3: Register Processor

Add the processor to the application factory:

```python
# main.py - in ApplicationFactory._register_infrastructure_services()
from src.infrastructure.processors.my_custom_effect_processor import MyCustomEffectProcessor

# Register effect processors
effect_processors = [
    SlideEffectProcessor(self.config.ffmpeg),
    CircleEffectProcessor(self.config.ffmpeg),
    FadeEffectProcessor(self.config.ffmpeg),
    GIFProcessor(self.config.paths),
    MyCustomEffectProcessor(self.config.ffmpeg),  # Add your processor
]
```

### Step 4: Add Tests

Create comprehensive tests:

```python
# tests/unit/infrastructure/processors/test_my_custom_effect_processor.py
import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from src.infrastructure.processors.my_custom_effect_processor import MyCustomEffectProcessor
from src.domain.entities.video import Video
from src.domain.entities.effect import Effect
from src.domain.value_objects.effect_type import EffectType
from src.shared.config.video_config import FFmpegConfig

class TestMyCustomEffectProcessor:

    @pytest.fixture
    def processor(self):
        config = FFmpegConfig()
        return MyCustomEffectProcessor(config)

    @pytest.fixture
    def sample_video(self):
        return Video(
            path=Path("test.mp4"),
            filename="test.mp4",
            duration=10.0,
            dimensions=Dimensions(1920, 1080)
        )

    @pytest.fixture
    def sample_effect(self):
        return Effect(
            type=EffectType.MY_CUSTOM_EFFECT,
            duration=2.0,
            parameters={}
        )

    def test_can_handle_custom_effect(self, processor):
        assert processor.can_handle(EffectType.MY_CUSTOM_EFFECT)
        assert not processor.can_handle(EffectType.FADE_IN)

    def test_apply_effect_success(self, processor, sample_video, sample_effect):
        with patch.object(processor, '_execute_ffmpeg') as mock_execute:
            mock_execute.return_value = Mock(success=True, output_video=sample_video)

            result = processor.apply(sample_video, sample_effect)

            assert result == sample_video
            mock_execute.assert_called_once()

    def test_build_ffmpeg_command(self, processor, sample_video, sample_effect):
        command = processor._build_ffmpeg_command(sample_video, sample_effect)

        assert 'ffmpeg' in command
        assert '-i' in command
        assert str(sample_video.path) in command
        assert 'custom_filter=duration=2.0' in ' '.join(command)
```

## Adding New Use Cases

### Step 1: Define Request/Response Models

```python
# src/application/models/my_models.py
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

@dataclass
class MyUseCaseRequest:
    """Request for my use case"""
    parameter1: str
    parameter2: Optional[int] = None

@dataclass
class MyUseCaseResponse:
    """Response from my use case"""
    success: bool
    result_data: List[str]
    error_message: Optional[str] = None
```

### Step 2: Implement Use Case

```python
# src/application/use_cases/my_use_case.py
from typing import List
from ...domain.services.my_repository_interface import IMyRepository
from ...shared.config import AppConfig
from ...shared.utils import get_logger
from ..models.my_models import MyUseCaseRequest, MyUseCaseResponse

logger = get_logger(__name__)

class MyUseCase:
    """Use case for my business logic"""

    def __init__(self, my_repository: IMyRepository, config: AppConfig):
        """
        Initialize use case.

        Args:
            my_repository: Repository for data access
            config: Application configuration
        """
        self.my_repository = my_repository
        self.config = config

    def execute(self, request: MyUseCaseRequest) -> MyUseCaseResponse:
        """
        Execute the use case.

        Args:
            request: Use case request

        Returns:
            Use case response
        """
        try:
            logger.info(f"Executing my use case with parameter: {request.parameter1}")

            # Business logic implementation
            result = self._perform_business_logic(request)

            return MyUseCaseResponse(
                success=True,
                result_data=result
            )

        except Exception as e:
            logger.error(f"Use case failed: {e}")
            return MyUseCaseResponse(
                success=False,
                result_data=[],
                error_message=str(e)
            )

    def _perform_business_logic(self, request: MyUseCaseRequest) -> List[str]:
        """Perform the core business logic"""
        # Implementation here
        pass
```

### Step 3: Register Use Case

Add to dependency injection:

```python
# main.py - in ApplicationFactory._register_use_cases()
def create_my_use_case():
    my_repo = self.container.resolve(IMyRepository)
    return MyUseCase(my_repo, self.config)

self.container.register_factory(MyUseCase, create_my_use_case)
```

## Configuration Management

### Adding New Configuration Sections

1. **Define Configuration Class:**

```python
# src/shared/config/my_config.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class MyConfig:
    """Configuration for my feature"""
    setting1: str = "default_value"
    setting2: int = 42
    setting3: Optional[str] = None

    def validate(self) -> List[str]:
        """Validate configuration"""
        errors = []
        if self.setting2 < 0:
            errors.append("setting2 must be positive")
        return errors
```

2. **Add to Main Configuration:**

```python
# src/shared/config/app_config.py
from .my_config import MyConfig

@dataclass
class AppConfig:
    # ... existing fields
    my_feature: MyConfig = None

    def __post_init__(self):
        # ... existing initialization
        if self.my_feature is None:
            self.my_feature = MyConfig()
```

3. **Update Configuration Loading:**

```python
# In AppConfig.from_dict() and to_dict() methods
config_dict['my_feature'] = asdict(self.my_feature)

# In from_dict:
my_config = MyConfig(**data.get('my_feature', {}))
```

## Testing Guidelines

### Unit Tests

- Test each component in isolation
- Mock external dependencies
- Focus on business logic
- Achieve high code coverage

```python
# Example unit test structure
class TestMyComponent:

    @pytest.fixture
    def component(self):
        # Setup component with mocked dependencies
        pass

    def test_happy_path(self, component):
        # Test successful execution
        pass

    def test_error_handling(self, component):
        # Test error scenarios
        pass

    def test_edge_cases(self, component):
        # Test boundary conditions
        pass
```

### Integration Tests

- Test component interactions
- Use real implementations where possible
- Test configuration loading
- Test file system operations

```python
# Example integration test
class TestVideoProcessingIntegration:

    def test_end_to_end_processing(self, temp_dir):
        # Test complete video processing workflow
        pass
```

### Test Fixtures

Use pytest fixtures for common test data:

```python
# tests/conftest.py
@pytest.fixture
def sample_config():
    return AppConfig(
        video=VideoProcessingConfig(output_width=1080),
        # ... other settings
    )

@pytest.fixture
def temp_video_file(tmp_path):
    video_path = tmp_path / "test.mp4"
    # Create test video file
    return video_path
```

## Error Handling

### Exception Hierarchy

Follow the established exception hierarchy:

```python
# src/shared/exceptions/my_exceptions.py
from .base_exceptions import VideoProcessingException

class MyFeatureException(VideoProcessingException):
    """Base exception for my feature"""
    pass

class MySpecificException(MyFeatureException):
    """Specific exception for my feature"""

    def __init__(self, message: str, context: dict = None):
        super().__init__(message)
        self.context = context or {}
```

### Error Handling Patterns

```python
# In use cases and services
try:
    result = risky_operation()
except SpecificException as e:
    logger.error(f"Specific error: {e}")
    # Handle specific error
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Handle general error
```

## Logging

### Logging Best Practices

```python
# Get logger for your module
logger = get_logger(__name__)

# Log levels
logger.debug("Detailed debugging information")
logger.info("General information")
logger.warning("Warning about potential issues")
logger.error("Error that doesn't stop execution")
logger.critical("Critical error that stops execution")

# Structured logging
logger.info("Processing video", extra={
    'video_path': str(video.path),
    'duration': video.duration,
    'effect_type': effect.type.value
})
```

### Performance Logging

```python
# Use performance logger for timing
perf_logger = get_performance_logger(__name__)

start_time = time.time()
# ... operation
processing_time = time.time() - start_time

perf_logger.info("Video processing completed", extra={
    'processing_time': processing_time,
    'video_size': video.file_size,
    'effect_count': len(effects)
})
```

## Deployment

### Building Distribution

1. **Create setup.py:**

```python
from setuptools import setup, find_packages

setup(
    name="tiktok-video-processor",
    version="2.0.0",
    packages=find_packages(),
    install_requires=[
        # List dependencies
    ],
    entry_points={
        'console_scripts': [
            'tiktok-processor=main:main',
        ],
    },
)
```

2. **Build Package:**

```bash
python setup.py sdist bdist_wheel
```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Copy application
COPY . /app
WORKDIR /app

# Install dependencies
RUN pip install -r requirements.txt

# Run application
CMD ["python", "main.py"]
```

## Performance Optimization

### Profiling

Use the built-in profiling:

```bash
python main.py --profile --cli process input.mp4 bg.mp4
```

### Memory Management

- Use generators for large datasets
- Clear caches periodically
- Monitor memory usage in long-running processes

### Parallel Processing

- Configure `max_workers` based on system capabilities
- Use async/await for I/O operations
- Implement proper resource cleanup

## Contributing Guidelines

1. **Code Style:**

   - Follow PEP 8
   - Use type hints
   - Add comprehensive docstrings
   - Keep functions focused and small

2. **Testing:**

   - Write tests for new features
   - Maintain high test coverage
   - Test error scenarios

3. **Documentation:**

   - Update README for user-facing changes
   - Update this guide for developer changes
   - Add inline code comments

4. **Pull Requests:**
   - Create feature branches
   - Write clear commit messages
   - Include tests and documentation
   - Request code review

## Troubleshooting Development Issues

### Common Development Problems

1. **Import Errors:**

   - Check PYTHONPATH
   - Verify package structure
   - Use relative imports correctly

2. **Dependency Injection Issues:**

   - Verify service registration
   - Check interface implementations
   - Debug container resolution

3. **Configuration Problems:**

   - Validate configuration schema
   - Check file permissions
   - Verify environment variables

4. **Test Failures:**
   - Check test isolation
   - Verify mock configurations
   - Update test data

### Debug Tools

- Use `--debug` flag for detailed logging
- Enable profiling with `--profile`
- Use IDE debugger for step-through debugging
- Add temporary logging statements

---

This guide should help you understand and extend the TikTok Video Processing Tool effectively. For specific questions, refer to the code documentation or create an issue.
