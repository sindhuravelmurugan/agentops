"""
Redis-backed cache for intermediate tool results.

Why this exists: in a multi-agent workflow, the same tool is often called
with the same arguments multiple times across concurrent workflow runs
(e.g. "look up ticket #4521" gets called by both the triage agent and the
status-report agent). Caching the tool's output keyed on (tool_name, args)
avoids redoing that work, which is what drives the latency win when
multiple workflows run concurrently.
"""
import hashlib
import json
import logging
from typing import Any, Optional

import redis

from app.config import settings

logger = logging.getLogger("agentops.cache")

_client: Optional[redis.Redis] = None


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )
    return _client


def _make_key(tool_name: str, args: dict) -> str:
    payload = json.dumps(args, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return f"agentops:tool:{tool_name}:{digest}"


def get_cached_result(tool_name: str, args: dict) -> Optional[Any]:
    key = _make_key(tool_name, args)
    try:
        raw = get_client().get(key)
    except redis.RedisError as e:
        logger.warning("Redis unavailable, skipping cache read: %s", e)
        return None
    if raw is None:
        return None
    logger.info("cache HIT for %s", key)
    return json.loads(raw)


def set_cached_result(tool_name: str, args: dict, result: Any) -> None:
    key = _make_key(tool_name, args)
    try:
        get_client().setex(key, settings.CACHE_TTL_SECONDS, json.dumps(result, default=str))
    except redis.RedisError as e:
        logger.warning("Redis unavailable, skipping cache write: %s", e)


def cache_stats() -> dict:
    """Used by the benchmark script to report real hit-rate numbers."""
    try:
        info = get_client().info(section="stats")
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        return {
            "hits": hits,
            "misses": misses,
            "hit_rate": round(hits / total, 4) if total else 0.0,
        }
    except redis.RedisError:
        return {"hits": 0, "misses": 0, "hit_rate": 0.0}
