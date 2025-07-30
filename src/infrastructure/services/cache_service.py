"""
Cache Service Implementation

JSON-based caching service for video metadata and other data.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import threading
import fnmatch

from ...domain.services.cache_service_interface import ICacheService, CacheEntry
from ...shared.exceptions import CacheException
from ...shared.config import PerformanceConfig

logger = logging.getLogger(__name__)


class CacheService(ICacheService):
    """JSON-based cache service implementation"""

    def __init__(self, config: PerformanceConfig):
        """
        Initialize cache service.

        Args:
            config: Performance configuration
        """
        self.config = config
        self.cache_path = config.cache_path
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'clears': 0
        }

        if config.cache_enabled:
            self._load_cache()

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        if not self.config.cache_enabled:
            return None

        with self._lock:
            try:
                if key not in self._cache:
                    self._stats['misses'] += 1
                    return None

                entry_data = self._cache[key]
                entry = self._dict_to_cache_entry(key, entry_data)

                if entry.is_expired():
                    # Remove expired entry
                    del self._cache[key]
                    self._stats['misses'] += 1
                    logger.debug(f"Cache entry expired: {key}")
                    return None

                self._stats['hits'] += 1
                logger.debug(f"Cache hit: {key}")
                return entry.value

            except Exception as e:
                logger.warning(f"Error getting cache entry {key}: {e}")
                self._stats['misses'] += 1
                return None

    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live (optional)

        Returns:
            True if value was cached successfully, False otherwise
        """
        if not self.config.cache_enabled:
            return False

        with self._lock:
            try:
                now = datetime.now()
                expires_at = now + ttl if ttl else None

                entry_data = {
                    'value': value,
                    'created_at': now.isoformat(),
                    'expires_at': expires_at.isoformat() if expires_at else None
                }

                self._cache[key] = entry_data
                self._stats['sets'] += 1

                logger.debug(f"Cache set: {key} (TTL: {ttl})")

                # Periodically save to disk
                if self._stats['sets'] % 10 == 0:
                    self._save_cache()

                return True

            except Exception as e:
                logger.error(f"Error setting cache entry {key}: {e}")
                return False

    def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if value was deleted, False if key not found
        """
        if not self.config.cache_enabled:
            return False

        with self._lock:
            try:
                if key in self._cache:
                    del self._cache[key]
                    self._stats['deletes'] += 1
                    logger.debug(f"Cache delete: {key}")
                    return True
                return False

            except Exception as e:
                logger.warning(f"Error deleting cache entry {key}: {e}")
                return False

    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists and is not expired, False otherwise
        """
        return self.get(key) is not None

    def clear(self) -> bool:
        """
        Clear all cache entries.

        Returns:
            True if cache was cleared successfully, False otherwise
        """
        if not self.config.cache_enabled:
            return False

        with self._lock:
            try:
                self._cache.clear()
                self._stats['clears'] += 1
                self._save_cache()
                logger.info("Cache cleared")
                return True

            except Exception as e:
                logger.error(f"Error clearing cache: {e}")
                return False

    def get_keys(self, pattern: Optional[str] = None) -> List[str]:
        """
        Get all cache keys, optionally matching a pattern.

        Args:
            pattern: Optional pattern to match keys (glob-style)

        Returns:
            List of matching cache keys
        """
        if not self.config.cache_enabled:
            return []

        with self._lock:
            try:
                keys = list(self._cache.keys())

                if pattern:
                    keys = [key for key in keys if fnmatch.fnmatch(key, pattern)]

                return keys

            except Exception as e:
                logger.warning(f"Error getting cache keys: {e}")
                return []

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0

            return {
                'enabled': self.config.cache_enabled,
                'cache_file': str(self.cache_path),
                'total_entries': len(self._cache),
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate_percent': round(hit_rate, 2),
                'sets': self._stats['sets'],
                'deletes': self._stats['deletes'],
                'clears': self._stats['clears'],
                'memory_usage_kb': self._estimate_memory_usage()
            }

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        if not self.config.cache_enabled:
            return 0

        with self._lock:
            try:
                expired_keys = []

                for key, entry_data in self._cache.items():
                    entry = self._dict_to_cache_entry(key, entry_data)
                    if entry.is_expired():
                        expired_keys.append(key)

                for key in expired_keys:
                    del self._cache[key]

                if expired_keys:
                    logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
                    self._save_cache()

                return len(expired_keys)

            except Exception as e:
                logger.error(f"Error cleaning up expired entries: {e}")
                return 0

    def get_entry(self, key: str) -> Optional[CacheEntry]:
        """
        Get cache entry with metadata.

        Args:
            key: Cache key

        Returns:
            CacheEntry or None if not found
        """
        if not self.config.cache_enabled:
            return None

        with self._lock:
            try:
                if key not in self._cache:
                    return None

                entry_data = self._cache[key]
                return self._dict_to_cache_entry(key, entry_data)

            except Exception as e:
                logger.warning(f"Error getting cache entry {key}: {e}")
                return None

    def set_multiple(self, items: Dict[str, Any], ttl: Optional[timedelta] = None) -> int:
        """
        Set multiple values in cache.

        Args:
            items: Dictionary of key-value pairs
            ttl: Time to live for all items (optional)

        Returns:
            Number of items successfully cached
        """
        if not self.config.cache_enabled:
            return 0

        success_count = 0
        for key, value in items.items():
            if self.set(key, value, ttl):
                success_count += 1

        return success_count

    def get_multiple(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values from cache.

        Args:
            keys: List of cache keys

        Returns:
            Dictionary of found key-value pairs
        """
        if not self.config.cache_enabled:
            return {}

        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value

        return result

    def _load_cache(self) -> None:
        """Load cache from disk"""
        try:
            if not self.cache_path.exists():
                logger.debug("Cache file does not exist, starting with empty cache")
                return

            with open(self.cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._cache = data.get('entries', {})

                # Load stats if available
                if 'stats' in data:
                    saved_stats = data['stats']
                    for key in self._stats:
                        if key in saved_stats:
                            self._stats[key] = saved_stats[key]

            logger.info(f"Loaded cache with {len(self._cache)} entries from {self.cache_path}")

        except Exception as e:
            logger.warning(f"Failed to load cache from {self.cache_path}: {e}")
            self._cache = {}

    def _save_cache(self) -> None:
        """Save cache to disk"""
        try:
            # Create directory if needed
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)

            # Prepare data to save
            data = {
                'version': '1.0',
                'saved_at': datetime.now().isoformat(),
                'entries': self._cache,
                'stats': self._stats
            }

            # Write to temporary file first, then rename for atomicity
            temp_path = self.cache_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_path.replace(self.cache_path)

            logger.debug(f"Saved cache with {len(self._cache)} entries to {self.cache_path}")

        except Exception as e:
            logger.error(f"Failed to save cache to {self.cache_path}: {e}")
            raise CacheException("save", message=f"Failed to save cache: {e}")

    def _dict_to_cache_entry(self, key: str, entry_data: Dict[str, Any]) -> CacheEntry:
        """Convert dictionary to CacheEntry object"""
        created_at = datetime.fromisoformat(entry_data['created_at'])
        expires_at = None
        if entry_data.get('expires_at'):
            expires_at = datetime.fromisoformat(entry_data['expires_at'])

        return CacheEntry(
            key=key,
            value=entry_data['value'],
            created_at=created_at,
            expires_at=expires_at
        )

    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage in KB"""
        try:
            # Rough estimation based on JSON serialization
            cache_str = json.dumps(self._cache)
            return len(cache_str.encode('utf-8')) // 1024
        except Exception:
            return 0

    def force_save(self) -> bool:
        """Force save cache to disk"""
        try:
            with self._lock:
                self._save_cache()
            return True
        except Exception as e:
            logger.error(f"Failed to force save cache: {e}")
            return False

    def get_cache_file_info(self) -> Dict[str, Any]:
        """Get information about cache file"""
        try:
            if not self.cache_path.exists():
                return {
                    'exists': False,
                    'path': str(self.cache_path)
                }

            stat = self.cache_path.stat()
            return {
                'exists': True,
                'path': str(self.cache_path),
                'size_bytes': stat.st_size,
                'size_kb': stat.st_size // 1024,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'readable': self.cache_path.is_file() and os.access(self.cache_path, os.R_OK),
                'writable': os.access(self.cache_path.parent, os.W_OK)
            }
        except Exception as e:
            return {
                'exists': False,
                'path': str(self.cache_path),
                'error': str(e)
            }
