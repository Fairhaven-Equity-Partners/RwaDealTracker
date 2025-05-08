import functools
import time
import pickle
import os
from typing import Callable, Any, Dict, Optional, Tuple
import hashlib
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create cache directory if it doesn't exist
CACHE_DIR = ".cache"
os.makedirs(CACHE_DIR, exist_ok=True)

class MemoryCache:
    """
    In-memory cache with TTL (Time-To-Live) expiration.
    """
    _cache: Dict[str, Tuple[Any, float]] = {}
    
    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        """Get a value from the cache if it exists and is not expired"""
        if key in cls._cache:
            value, expiry = cls._cache[key]
            if expiry > time.time():
                logger.debug(f"Memory cache hit for key: {key}")
                return value
            else:
                # Remove expired entry
                logger.debug(f"Memory cache expired for key: {key}")
                del cls._cache[key]
        return None
    
    @classmethod
    def set(cls, key: str, value: Any, ttl: int = 3600) -> None:
        """Set a value in the cache with a TTL in seconds"""
        expiry = time.time() + ttl
        cls._cache[key] = (value, expiry)
        logger.debug(f"Set value in memory cache for key: {key}, expires in {ttl} seconds")
    
    @classmethod
    def clear(cls) -> None:
        """Clear all cache entries"""
        cls._cache.clear()
        logger.debug("Memory cache cleared")

class DiskCache:
    """
    Disk-based persistent cache with TTL (Time-To-Live) expiration.
    """
    @staticmethod
    def _get_cache_path(key: str) -> str:
        """Get the file path for a cache key"""
        hashed_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(CACHE_DIR, f"{hashed_key}.cache")
    
    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        """Get a value from the disk cache if it exists and is not expired"""
        cache_path = cls._get_cache_path(key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    value, expiry = pickle.load(f)
                    if expiry > time.time():
                        logger.debug(f"Disk cache hit for key: {key}")
                        return value
                    else:
                        # Remove expired file
                        logger.debug(f"Disk cache expired for key: {key}")
                        os.remove(cache_path)
            except (pickle.PickleError, IOError) as e:
                logger.error(f"Error loading from disk cache: {e}")
        return None
    
    @classmethod
    def set(cls, key: str, value: Any, ttl: int = 86400) -> None:
        """Set a value in the disk cache with a TTL in seconds"""
        cache_path = cls._get_cache_path(key)
        expiry = time.time() + ttl
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump((value, expiry), f)
            logger.debug(f"Set value in disk cache for key: {key}, expires in {ttl} seconds")
        except (pickle.PickleError, IOError) as e:
            logger.error(f"Error saving to disk cache: {e}")
    
    @classmethod
    def clear(cls) -> None:
        """Clear all disk cache entries"""
        for filename in os.listdir(CACHE_DIR):
            if filename.endswith(".cache"):
                os.remove(os.path.join(CACHE_DIR, filename))
        logger.debug("Disk cache cleared")

def cache(ttl: int = 3600, use_disk: bool = False):
    """
    Cache decorator that can use either memory or disk cache.
    
    Args:
        ttl: Time-to-live in seconds (default: 1 hour)
        use_disk: Whether to use disk cache (default: False, use memory cache)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from the function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)
            
            # Try to get value from cache
            cache_handler = DiskCache if use_disk else MemoryCache
            cached_value = cache_handler.get(cache_key)
            
            if cached_value is not None:
                return cached_value
            
            # If not in cache, call the function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache_handler.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator
