"""
Cache Service Interface

Defines the contract for caching operations.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta


class CacheEntry:
    """Represents a cache entry with metadata"""

    def __init__(self, key: str, value: Any, created_at: datetime,
                 expires_at: Optional[datetime] = None):
        self.key = key
        self.value = value
        self.created_at = created_at
        self.expires_at = expires_at

    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at

    def get_age(self) -> timedelta:
        """Get age of cache entry"""
        return datetime.now() - self.created_at


class ICacheService(ABC):
    """Interface for caching operations"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
    @abstractmethod
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
    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if value was deleted, False if key not found
        """
    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists and is not expired, False otherwise
        """
    @abstractmethod
    def clear(self) -> bool:
        """
        Clear all cache entries.

        Returns:
            True if cache was cleared successfully, False otherwise
        """
    @abstractmethod
    def get_keys(self, pattern: Optional[str] = None) -> List[str]:
        """
        Get all cache keys, optionally matching a pattern.

        Args:
            pattern: Optional pattern to match keys (glob-style)

        Returns:
            List of matching cache keys
        """
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics (hits, misses, size, etc.)
        """
    @abstractmethod
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
    @abstractmethod
    def get_entry(self, key: str) -> Optional[CacheEntry]:
        """
        Get cache entry with metadata.

        Args:
            key: Cache key

        Returns:
            CacheEntry or None if not found
        """
    @abstractmethod
    def set_multiple(self, items: Dict[str, Any], ttl: Optional[timedelta] = None) -> int:
        """
        Set multiple values in cache.

        Args:
            items: Dictionary of key-value pairs
            ttl: Time to live for all items (optional)

        Returns:
            Number of items successfully cached
        """
    @abstractmethod
    def get_multiple(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values from cache.

        Args:
            keys: List of cache keys

        Returns:
            Dictionary of found key-value pairs
        """
        pass
