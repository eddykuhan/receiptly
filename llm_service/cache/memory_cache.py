from typing import Optional, Dict

# Simple in-memory cache
_cache: Dict[str, str] = {}

def get_cached(raw_name: str) -> Optional[str]:
    return _cache.get(raw_name)

def set_cached(raw_name: str, canonical_name: str):
    _cache[raw_name] = canonical_name

