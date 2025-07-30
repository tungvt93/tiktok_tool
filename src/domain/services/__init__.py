"""
Domain Services

Interfaces and abstract classes that define contracts for domain operations.
"""

from .video_processor_interface import IVideoProcessor, ProcessingResult, VideoInfo
from .effect_processor_interface import IEffectProcessor, EffectResult
from .file_repository_interface import IFileRepository, FileSearchCriteria
from .video_repository_interface import IVideoRepository, VideoSearchCriteria
from .cache_service_interface import ICacheService, CacheEntry

__all__ = [
    # Interfaces
    'IVideoProcessor',
    'IEffectProcessor',
    'IFileRepository',
    'IVideoRepository',
    'ICacheService',
    # Result Objects
    'ProcessingResult',
    'VideoInfo',
    'EffectResult',
    # Criteria Objects
    'FileSearchCriteria',
    'VideoSearchCriteria',
    'CacheEntry'
]
