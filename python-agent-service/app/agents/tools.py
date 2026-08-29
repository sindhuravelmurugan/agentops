"""
Tools shared across all workflow agents.

Each tool is:
  1. Decorated with @tool (LangChain) so LangGraph agents can call it.
  2. Registered on an MCP server (see mcp_server.py) so it's also reachable
     as a standard MCP tool by any MCP-compatible client, not just our
     own agents.
  3. Wrapped with a Redis cache check so repeated calls with the same
     arguments are served from cache instead of re-executed.

In this rebuilt version, the tools simulate the kind of calls a real
deployment would make (ticketing system, notification service, internal
docs) so the framework is runnable and testable without real credentials.
Swap the body of each function for a real API call when you plug this
into an actual ticketing/notification system.
"""
import time
import random
from functools import wraps
from typing import Callable

from langchain_core.tools import tool

from app.agents.cache import get_cached_result, set_cached_result


def cached_tool(fn: Callable) -> Callable:
    """Wraps a tool function with the Redis intermediate-result cache."""

    @wraps(fn)
    def wrapper(**kwargs):
        cached = get_cached_result(fn.__name__, kwargs)
        if cached is not None:
            return cached
        result = fn(**kwargs)
        set_cached_result(fn.__name__, kwargs, result)
        return result

    return wrapper


@tool
@cached_tool
def lookup_ticket(ticket_id: str) -> dict:
    """Look up a support ticket by ID and return its details."""
    # Simulated I/O latency of a real ticketing API call.
    time.sleep(0.15)
    return {
        "ticket_id": ticket_id,
        "subject": "Login failures after SSO rollout",
        "priority": random.choice(["low", "medium", "high"]),
        "status": "open",
        "customer_tier": random.choice(["free", "pro", "enterprise"]),
    }


@tool
@cached_tool
def classify_priority(subject: str, customer_tier: str) -> dict:
    """Classify a ticket's priority given its subject and customer tier."""
    time.sleep(0.1)
    score = 3 if customer_tier == "enterprise" else 1
    score += 2 if "down" in subject.lower() or "fail" in subject.lower() else 0
    return {"priority_score": score, "recommended_sla_hours": max(1, 24 - score * 4)}


@tool
@cached_tool
def draft_response(ticket_id: str, subject: str) -> dict:
    """Draft a first-touch customer response for a given ticket."""
    time.sleep(0.2)
    return {
        "ticket_id": ticket_id,
        "draft": f"Hi, thanks for reporting '{subject}'. We're investigating now "
        f"and will update you shortly.",
    }


@tool
@cached_tool
def fetch_service_metrics(service_name: str) -> dict:
    """Fetch current operational metrics for a service (uptime, error rate, latency)."""
    time.sleep(0.15)
    return {
        "service": service_name,
        "uptime_pct": round(random.uniform(98.5, 99.99), 2),
        "error_rate_pct": round(random.uniform(0.01, 1.5), 2),
        "p95_latency_ms": random.randint(80, 400),
    }


@tool
@cached_tool
def summarize_status(service_name: str, metrics: dict) -> dict:
    """Summarize a service's health into a short status-report paragraph."""
    time.sleep(0.1)
    health = "healthy" if metrics.get("error_rate_pct", 0) < 1 else "degraded"
    return {
        "service": service_name,
        "summary": f"{service_name} is currently {health}. "
        f"Uptime {metrics.get('uptime_pct')}%, "
        f"p95 latency {metrics.get('p95_latency_ms')}ms.",
    }


@tool
@cached_tool
def sync_records(source: str, target: str) -> dict:
    """Simulate syncing records between two systems and report a diff count."""
    time.sleep(0.2)
    return {"source": source, "target": target, "records_synced": random.randint(5, 80)}


@tool
@cached_tool
def send_notification(channel: str, message: str) -> dict:
    """Send a notification to a channel (e.g. Slack, email) and confirm delivery."""
    time.sleep(0.1)
    return {"channel": channel, "delivered": True, "message": message}


ALL_TOOLS = [
    lookup_ticket,
    classify_priority,
    draft_response,
    fetch_service_metrics,
    summarize_status,
    sync_records,
    send_notification,
]
