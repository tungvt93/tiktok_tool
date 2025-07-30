"""
Configuration Management

Configuration classes and dependency injection container.
"""

from .app_config import AppConfig
from .video_config import VideoProcessingConfig, FFmpegConfig, PathConfig, PerformanceConfig, UIConfig
from .config_loader import ConfigLoader, load_config, save_config, get_config_loader
from .dependency_injection import DIContainer, ServiceRegistry, create_container, register_services, singleton, transient, implements

__all__ = [
    # Main config
    'AppConfig',
    # Config sections
    'VideoProcessingConfig',
    'FFmpegConfig',
    'PathConfig',
    'PerformanceConfig',
    'UIConfig',
    # Loader utilities
    'ConfigLoader',
    'load_config',
    'save_config',
    'get_config_loader',
    # Dependency injection
    'DIContainer',
    'ServiceRegistry',
    'create_container',
    'register_services',
    'singleton',
    'transient',
    'implements'
]
