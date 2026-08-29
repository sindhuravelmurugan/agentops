"""
Tests for the tool layer and caching behavior. These don't require a real
OpenAI key — they test the parts of the framework that are deterministic
and don't call the LLM (the graph/LLM-dependent parts are exercised via
the benchmark script against a live service instead, since mocking an
LLM's tool-calling behavior meaningfully requires a real model).
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agents.tools import lookup_ticket, classify_priority
from app.agents.cache import get_cached_result, set_cached_result, _make_key


def test_lookup_ticket_returns_expected_fields():
    result = lookup_ticket.invoke({"ticket_id": "T-1"})
    assert result["ticket_id"] == "T-1"
    assert "priority" in result
    assert "status" in result


def test_classify_priority_scores_enterprise_higher():
    free_result = classify_priority.invoke(
        {"subject": "question about billing", "customer_tier": "free"}
    )
    ent_result = classify_priority.invoke(
        {"subject": "question about billing", "customer_tier": "enterprise"}
    )
    assert ent_result["priority_score"] > free_result["priority_score"]


def test_cache_roundtrip():
    set_cached_result("unit_test_tool", {"a": 1}, {"value": 42})
    cached = get_cached_result("unit_test_tool", {"a": 1})
    assert cached == {"value": 42}


def test_cache_key_is_deterministic():
    key1 = _make_key("tool", {"a": 1, "b": 2})
    key2 = _make_key("tool", {"b": 2, "a": 1})  # order shouldn't matter
    assert key1 == key2


if __name__ == "__main__":
    test_lookup_ticket_returns_expected_fields()
    test_classify_priority_scores_enterprise_higher()
    try:
        test_cache_roundtrip()
        test_cache_key_is_deterministic()
        print("All tests passed (including Redis-dependent ones).")
    except Exception as e:
        print(f"Non-Redis tests passed. Redis-dependent tests skipped/failed: {e}")
