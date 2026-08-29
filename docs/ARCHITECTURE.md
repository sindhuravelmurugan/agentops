# Architecture Notes

## Why a Go gateway in front of a Python service?

Python's GIL makes it a poor fit for handling a lot of concurrent
lightweight I/O-bound routing/caching decisions at once, while Go's
goroutines are cheap and well-suited to exactly that. So the split is:

- **Go** handles connection fan-out, per-request latency tracking, and a
  fast Redis existence check before a request is even forwarded.
- **Python/FastAPI** hosts the actual agent logic, because LangGraph,
  LangChain, and the OpenAI SDK are Python-native — rewriting the agent
  loop in Go would mean losing the LangGraph ecosystem for no real
  benefit, since the agent step itself (an LLM call) dominates latency
  far more than the routing layer does.

This mirrors a common real-world pattern: a thin, fast gateway in a
systems language in front of a slower, ecosystem-rich application
language, rather than one monolith doing both jobs.

## Two layers of caching — why both?

- **Tool-result cache (Python/Redis, keyed on tool name + args)**: avoids
  redoing expensive/slow tool calls (a ticket lookup, a metrics fetch)
  when the same call is made again, whether by the same workflow run or a
  different one running concurrently.
- **Request-result cache (Go/Redis, keyed on endpoint + full request
  body)**: a coarser, shorter-TTL cache that avoids re-running an entire
  workflow (multiple LLM calls + multiple tool calls) if the exact same
  request comes in again within a short window — e.g. a retry, or two
  triggers firing for the same event.

They operate at different granularities and TTLs on purpose: the tool
cache is cheap to hit and safe to keep longer; the whole-request cache is
coarser and kept short so it doesn't serve stale results for something
that's meant to be re-evaluated.

## Why MCP instead of hardcoded tool functions on the agent?

Registering tools on an MCP server (`app/agents/mcp_server.py`) means the
same tools are callable by any MCP-compatible client — not just this
repo's LangGraph agents. In a real deployment this is what lets, say, a
separate internal chat tool or another team's agent reuse the same
ticket-lookup/notification tools without duplicating the implementation.

## Honest limitations of this rebuild

- The tools in `tools.py` simulate I/O with `time.sleep()` rather than
  calling real systems (a real ticketing API, a real Slack webhook, a
  real warehouse). This keeps the framework runnable and testable without
  needing real credentials — but it also means the concurrency/latency
  numbers you'll measure are bounded by these simulated latencies, not a
  production workload's real latencies. Swap in real API calls before
  citing production-scale numbers.
- The "hours saved per week" and "% drop in manual handoffs" claims are
  fundamentally about *comparing this system's output to a human doing
  the same steps manually* — that's not something a load test can prove
  on its own.
