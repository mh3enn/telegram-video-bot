import time
from config import CACHE_TTL

# user_id -> {"missing": list, "ts": float}
_membership_cache = {}

def get_cached_membership(user_id):
    data = _membership_cache.get(user_id)
    if not data:
        return None

    if time.time() - data["ts"] > CACHE_TTL:
        del _membership_cache[user_id]
        return None

    return data["missing"]

def set_cached_membership(user_id, missing_channels):
    _membership_cache[user_id] = {
        "missing": missing_channels,
        "ts": time.time()
    }

def clear_cached_membership(user_id):
    _membership_cache.pop(user_id, None)
