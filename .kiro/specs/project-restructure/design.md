# Design Document

## Overview

This document outlines the design for restructuring the TikTok Video Processing Tool into a clean, maintainable architecture following SOLID principles, dependency injection, and clean architecture patterns. The restructure will transform the current monolithic structure into a modular, testable, and extensible system.

## Architecture

### Clean Architecture Layers

The application will be restructured into the following layers:

```
src/
├── domain/           # Business logic and entities
├── application/      # Use cases and application services
├── infrastructure/   # External dependencies (FFmpeg, file system)
├── presentation/     # UI components (GUI, CLI)
└── shared/          # Common utilities and interfaces
```

### Dependency Flow

- **Presentation Layer** → **Application Layer** → **Domain Layer**
- **Infrastructure Layer** → **Application Layer** (through interfaces)
- No layer depends on layers above it
- Dependencies point inward toward the domain

## Components and Interfaces

### Domain Layer

#### Core Entities

```python
# src/domain/entities/video.py
@dataclass
class Video:
    path: Path
    duration: float
    dimensions: Tuple[int, int]
    metadata: Dict[str, Any]

# src/domain/entities/effect.py
@dataclass
class Effect:
    type: EffectType
    duration: float
    parameters: Dict[str, Any]

# src/domain/entities/processing_job.py
@dataclass
class ProcessingJob:
    id: str
    main_video: Video
    background_video: Video
    effects: List[Effect]
    output_path: Path
    status: JobStatus
```

#### Domain Services

```python
# src/domain/services/video_processor_interface.py
class IVideoProcessor(ABC):
    @abstractmethod
    def process_video(self, job: ProcessingJob) -> ProcessingResult

    @abstractmethod
    def apply_effect(self, video: Video, effect: Effect) -> Video

# src/domain/services/effect_processor_interface.py
class IEffectProcessor(ABC):
    @abstractmethod
    def can_handle(self, effect_type: EffectType) -> bool

    @abstractmethod
    def apply(self, video: Video, effect: Effect) -> Video
```

### Application Layer

#### Use Cases

```python
# src/application/use_cases/process_video_use_case.py
class ProcessVideoUseCase:
    def __init__(self,
                 video_processor: IVideoProcessor,
                 file_repository: IFileRepository,
                 config_service: IConfigService):
        self._video_processor = video_processor
        self._file_repository = file_repository
        self._config_service = config_service

    def execute(self, request: ProcessVideoRequest) -> ProcessVideoResponse:
        # Business logic implementation
```

#### Application Services

```python
# src/application/services/video_service.py
class VideoService:
    def __init__(self,
                 video_repository: IVideoRepository,
                 effect_processors: List[IEffectProcessor]):
        self._video_repository = video_repository
        self._effect_processors = effect_processors

    def get_videos(self, directory: Path) -> List[Video]:
        # Implementation

    def create_processing_job(self, request: CreateJobRequest) -> ProcessingJob:
        # Implementation
```

### Infrastructure Layer

#### Repositories

```python
# src/infrastructure/repositories/file_repository.py
class FileRepository(IFileRepository):
    def __init__(self, config: FileConfig):
        self._config = config

    def get_videos(self, pattern: str) -> List[Path]:
        # File system implementation

    def save_video(self, video: Video, path: Path) -> bool:
        # File system implementation

# src/infrastructure/repositories/video_repository.py
class VideoRepository(IVideoRepository):
    def __init__(self,
                 file_repository: IFileRepository,
                 cache_service: ICacheService):
        self._file_repository = file_repository
        self._cache_service = cache_service

    def get_by_path(self, path: Path) -> Optional[Video]:
        # Implementation with caching
```

#### External Services

```python
# src/infrastructure/services/ffmpeg_service.py
class FFmpegService(IVideoProcessor):
    def __init__(self, config: FFmpegConfig):
        self._config = config

    def process_video(self, job: ProcessingJob) -> ProcessingResult:
        # FFmpeg implementation

    def get_video_info(self, path: Path) -> VideoInfo:
        # FFprobe implementation

# src/infrastructure/services/cache_service.py
class CacheService(ICacheService):
    def __init__(self, cache_file: Path):
        self._cache_file = cache_file
        self._cache = {}

    def get(self, key: str) -> Optional[Any]:
        # Implementation

    def set(self, key: str, value: Any) -> None:
        # Implementation
```

#### Effect Processors

```python
# src/infrastructure/processors/slide_effect_processor.py
class SlideEffectProcessor(IEffectProcessor):
    def can_handle(self, effect_type: EffectType) -> bool:
        return effect_type in [EffectType.SLIDE_LEFT_TO_RIGHT, ...]

    def apply(self, video: Video, effect: Effect) -> Video:
        # FFmpeg slide effect implementation

# src/infrastructure/processors/circle_effect_processor.py
class CircleEffectProcessor(IEffectProcessor):
    def can_handle(self, effect_type: EffectType) -> bool:
        return effect_type in [EffectType.CIRCLE_EXPAND, ...]

    def apply(self, video: Video, effect: Effect) -> Video:
        # Circle effect implementation
```

### Presentation Layer

#### GUI Components

```python
# src/presentation/gui/main_window.py
class MainWindow:
    def __init__(self,
                 video_service: VideoService,
                 processing_service: ProcessingService):
        self._video_service = video_service
        self._processing_service = processing_service

    def setup_ui(self):
        # UI setup without business logic

# src/presentation/gui/components/video_list_widget.py
class VideoListWidget:
    def __init__(self, video_service: VideoService):
        self._video_service = video_service

    def load_videos(self):
        # Delegate to service
```

#### CLI Interface

```python
# src/presentation/cli/cli_app.py
class CLIApp:
    def __init__(self,
                 process_video_use_case: ProcessVideoUseCase):
        self._process_video_use_case = process_video_use_case

    def run(self, args: List[str]):
        # CLI implementation
```

### Shared Layer

#### Configuration

```python
# src/shared/config/app_config.py
@dataclass
class AppConfig:
    video: VideoConfig
    ffmpeg: FFmpegConfig
    ui: UIConfig

    @classmethod
    def from_file(cls, path: Path) -> 'AppConfig':
        # Load from JSON/YAML

# src/shared/config/dependency_injection.py
class DIContainer:
    def __init__(self, config: AppConfig):
        self._config = config
        self._services = {}

    def register_singleton(self, interface: Type, implementation: Type):
        # Registration logic

    def resolve(self, interface: Type) -> Any:
        # Resolution logic
```

#### Common Utilities

```python
# src/shared/utils/logging_config.py
def setup_logging(config: LoggingConfig):
    # Centralized logging setup

# src/shared/utils/validation.py
class Validator:
    @staticmethod
    def validate_video_file(path: Path) -> bool:
        # Validation logic

    @staticmethod
    def validate_config(config: AppConfig) -> List[str]:
        # Config validation
```

## Data Models

### Core Data Structures

```python
# Video metadata with caching
class VideoMetadata:
    path: Path
    duration: float
    dimensions: Tuple[int, int]
    codec: str
    bitrate: int
    created_at: datetime
    cached_at: datetime

# Processing job with status tracking
class ProcessingJob:
    id: UUID
    main_video: Video
    background_video: Video
    effects: List[Effect]
    output_path: Path
    status: JobStatus
    progress: float
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]

# Effect configuration
class EffectConfig:
    type: EffectType
    duration: float
    parameters: Dict[str, Any]

    def validate(self) -> List[str]:
        # Validation logic
```

### Configuration Models

```python
# Hierarchical configuration
class VideoProcessingConfig:
    output_dimensions: Tuple[int, int]
    frame_rate: int
    quality_settings: QualityConfig
    performance_settings: PerformanceConfig

class QualityConfig:
    crf_value: int
    preset: str
    codec: str

class PerformanceConfig:
    max_workers: int
    cache_enabled: bool
    temp_directory: Path
```

## Error Handling

### Exception Hierarchy

```python
# src/shared/exceptions/base_exceptions.py
class VideoProcessingException(Exception):
    """Base exception for video processing errors"""
    pass

class VideoNotFoundException(VideoProcessingException):
    """Raised when video file is not found"""
    pass

class FFmpegException(VideoProcessingException):
    """Raised when FFmpeg command fails"""
    def __init__(self, command: str, error_output: str):
        self.command = command
        self.error_output = error_output
        super().__init__(f"FFmpeg failed: {command}")

class EffectProcessingException(VideoProcessingException):
    """Raised when effect processing fails"""
    pass
```

### Error Handling Strategy

```python
# src/shared/utils/error_handler.py
class ErrorHandler:
    def __init__(self, logger: Logger):
        self._logger = logger

    def handle_exception(self, exc: Exception, context: str) -> ErrorResult:
        # Centralized error handling with logging

    def create_user_friendly_message(self, exc: Exception) -> str:
        # Convert technical errors to user-friendly messages
```

## Testing Strategy

### Test Structure

```
tests/
├── unit/
│   ├── domain/
│   ├── application/
│   └── infrastructure/
├── integration/
│   ├── repositories/
│   └── services/
├── e2e/
│   ├── gui/
│   └── cli/
└── fixtures/
    ├── videos/
    └── configs/
```

### Testing Patterns

```python
# Unit test example
class TestVideoService:
    def setup_method(self):
        self.mock_repository = Mock(spec=IVideoRepository)
        self.service = VideoService(self.mock_repository)

    def test_get_videos_returns_cached_results(self):
        # Test implementation

# Integration test example
class TestFFmpegService:
    def setup_method(self):
        self.config = FFmpegConfig()
        self.service = FFmpegService(self.config)
        self.test_video = Path("tests/fixtures/test_video.mp4")

    def test_process_video_creates_output(self):
        # Test with real FFmpeg
```

### Mocking Strategy

- Mock external dependencies (file system, FFmpeg) in unit tests
- Use real implementations in integration tests
- Create test doubles for complex scenarios
- Use dependency injection to make testing easier

## Migration Strategy

### Phase 1: Extract Domain Models

- Create domain entities and value objects
- Extract business logic from existing classes
- Maintain backward compatibility

### Phase 2: Implement Application Layer

- Create use cases and application services
- Implement dependency injection container
- Refactor existing code to use new services

### Phase 3: Restructure Infrastructure

- Extract FFmpeg operations to infrastructure layer
- Implement repository pattern for file operations
- Add proper error handling and logging

### Phase 4: Refactor Presentation Layer

- Separate UI logic from business logic
- Implement proper MVP/MVVM patterns
- Add comprehensive testing

### Phase 5: Optimization and Cleanup

- Remove deprecated code
- Optimize performance
- Add monitoring and metrics
