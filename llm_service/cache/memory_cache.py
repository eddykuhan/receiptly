from typing import Optional, Dict, Tuple, Any
import time

# In-memory cache with TTL (Time To Live)
# Format: {key: (value, timestamp)}
_cache: Dict[str, Tuple[Any, float]] = {}

# Cache TTL in seconds (1 hour)
CACHE_TTL = 3600

def get_cached(raw_name: str) -> Optional[Any]:
    """Get cached value if it exists and hasn't expired."""
    if raw_name in _cache:
        value, timestamp = _cache[raw_name]
        # Check if cache entry has expired
        if time.time() - timestamp < CACHE_TTL:
            return value
        else:
            # Cache expired, remove it
            del _cache[raw_name]
    return None

def set_cached(raw_name: str, canonical_data: Any):
    """Store value in cache with current timestamp."""
    _cache[raw_name] = (canonical_data, time.time())

def clear_cache():
    """Clear all cached entries."""
    _cache.clear()

def get_cache_stats() -> dict:
    """Get cache statistics."""
    current_time = time.time()
    total_entries = len(_cache)
    expired_entries = sum(1 for _, (_, ts) in _cache.items() if current_time - ts >= CACHE_TTL)
    
    return {
        "total_entries": total_entries,
        "active_entries": total_entries - expired_entries,
        "expired_entries": expired_entries,
        "ttl_seconds": CACHE_TTL
    }

