"""
Configuration Loader

Utilities for loading and managing application configuration.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
import os
import json
import logging

from .app_config import AppConfig


logger = logging.getLogger(__name__)


class ConfigLoader:
    """Configuration loader with multiple sources support"""

    DEFAULT_CONFIG_PATHS = [
        Path("config.json"),
        Path("config/app.json"),
        Path.home() / ".tiktok_processor" / "config.json",
        Path("/etc/tiktok_processor/config.json")
    ]

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration loader.

        Args:
            config_path: Specific config file path (optional)
        """
        self.config_path = config_path
        self._config_cache: Optional[AppConfig] = None

    def load_config(self, force_reload: bool = False) -> AppConfig:
        """
        Load configuration from various sources.

        Args:
            force_reload: Force reload even if cached

        Returns:
            AppConfig instance
        """
        if self._config_cache and not force_reload:
            return self._config_cache

        config = self._load_from_sources()
        self._config_cache = config
        return config

    def _load_from_sources(self) -> AppConfig:
        """Load configuration from multiple sources in priority order"""
        # 1. Try specific config path if provided
        if self.config_path:
            if self.config_path.exists():
                logger.info(f"Loading config from specified path: {self.config_path}")
                return AppConfig.from_file(self.config_path)
            else:
                logger.warning(f"Specified config path does not exist: {self.config_path}")

        # 2. Try default config paths
        for config_path in self.DEFAULT_CONFIG_PATHS:
            if config_path.exists():
                logger.info(f"Loading config from: {config_path}")
                try:
                    return AppConfig.from_file(config_path)
                except Exception as e:
                    logger.warning(f"Failed to load config from {config_path}: {e}")
                    continue

        # 3. Try environment variables
        logger.info("Loading config from environment variables")
        config = AppConfig.from_environment()

        # 4. Validate and ensure directories
        validation_errors = config.validate()
        if validation_errors:
            logger.warning(f"Configuration validation warnings: {validation_errors}")

        config.ensure_directories()
        return config

    def save_config(self, config: AppConfig, config_path: Optional[Path] = None) -> None:
        """
        Save configuration to file.

        Args:
            config: Configuration to save
            config_path: Path to save to (optional, uses default if not provided)
        """
        save_path = config_path or self.config_path or self.DEFAULT_CONFIG_PATHS[0]

        logger.info(f"Saving config to: {save_path}")
        config.save_to_file(save_path)

        # Update cache
        self._config_cache = config

    def create_default_config_file(self, config_path: Optional[Path] = None) -> Path:
        """
        Create a default configuration file.

        Args:
            config_path: Path to create config file (optional)

        Returns:
            Path to created config file
        """
        save_path = config_path or self.DEFAULT_CONFIG_PATHS[0]

        if save_path.exists():
            logger.warning(f"Config file already exists: {save_path}")
            return save_path

        # Create default config
        config = AppConfig()
        config.save_to_file(save_path)

        logger.info(f"Created default config file: {save_path}")
        return save_path

    def get_config_info(self) -> Dict[str, Any]:
        """Get information about current configuration"""
        config = self.load_config()

        return {
            'config_version': config.config_version,
            'created_at': config.created_at.isoformat() if config.created_at else None,
            'updated_at': config.updated_at.isoformat() if config.updated_at else None,
            'validation_errors': config.validate(),
            'is_valid': config.is_valid(),
            'config_sources': self._get_available_config_sources()
        }

    def _get_available_config_sources(self) -> List[Dict[str, Any]]:
        """Get information about available configuration sources"""
        sources = []

        # Check specific path
        if self.config_path:
            sources.append({
                'type': 'specific',
                'path': str(self.config_path),
                'exists': self.config_path.exists(),
                'readable': self.config_path.exists() and os.access(self.config_path, os.R_OK)
            })

        # Check default paths
        for path in self.DEFAULT_CONFIG_PATHS:
            sources.append({
                'type': 'default',
                'path': str(path),
                'exists': path.exists(),
                'readable': path.exists() and os.access(path, os.R_OK)
            })

        # Environment variables
        env_vars = [
            'VIDEO_OUTPUT_WIDTH', 'VIDEO_OUTPUT_HEIGHT', 'VIDEO_CRF_VALUE',
            'FFMPEG_PRESET', 'INPUT_DIR', 'OUTPUT_DIR', 'MAX_WORKERS',
            'UI_THEME', 'LOG_LEVEL'
        ]

        env_config = {var: os.getenv(var) for var in env_vars if os.getenv(var)}
        sources.append({
            'type': 'environment',
            'variables': env_config,
            'count': len(env_config)
        })

        return sources

    def migrate_old_config(self, old_config_path: Path) -> AppConfig:
        """
        Migrate configuration from old format.

        Args:
            old_config_path: Path to old configuration file

        Returns:
            Migrated AppConfig
        """
        if not old_config_path.exists():
            raise FileNotFoundError(f"Old config file not found: {old_config_path}")

        logger.info(f"Migrating config from: {old_config_path}")

        # This would contain logic to migrate from the old config.py format
        # For now, create a new config with some sensible defaults
        config = AppConfig()

        # Save migrated config
        new_config_path = old_config_path.parent / "config_migrated.json"
        config.save_to_file(new_config_path)

        logger.info(f"Migrated config saved to: {new_config_path}")
        return config


# Global configuration loader instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader(config_path: Optional[Path] = None) -> ConfigLoader:
    """Get global configuration loader instance"""
    global _config_loader
    if _config_loader is None or config_path:
        _config_loader = ConfigLoader(config_path)
    return _config_loader


def load_config(config_path: Optional[Path] = None, force_reload: bool = False) -> AppConfig:
    """
    Convenience function to load configuration.

    Args:
        config_path: Specific config file path (optional)
        force_reload: Force reload even if cached

    Returns:
        AppConfig instance
    """
    loader = get_config_loader(config_path)
    return loader.load_config(force_reload)


def save_config(config: AppConfig, config_path: Optional[Path] = None) -> None:
    """
    Convenience function to save configuration.

    Args:
        config: Configuration to save
        config_path: Path to save to (optional)
    """
    loader = get_config_loader()
    loader.save_config(config, config_path)
