"""
Exception Hierarchy

Custom exceptions for the video processing application.
"""

from .base_exceptions import (
    VideoProcessingException, VideoNotFoundException, VideoCorruptedException,
    FFmpegException, EffectProcessingException, ConfigurationException,
    ProcessingJobException, DependencyException, ResourceException,
    CacheException, ValidationException, UserCancelledException
)

__all__ = [
    'VideoProcessingException',
    'VideoNotFoundException',
    'VideoCorruptedException',
    'FFmpegException',
    'EffectProcessingException',
    'ConfigurationException',
    'ProcessingJobException',
    'DependencyException',
    'ResourceException',
    'CacheException',
    'ValidationException',
    'UserCancelledException'
]
