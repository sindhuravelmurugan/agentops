# AgentOps — Multi-Agent LLM Framework

A multi-agent framework that automates multi-step operational workflows
(ticket triage, status reporting, data sync + notification) by chaining
LangGraph tool-calling agents behind an MCP tool registry, with a Go
gateway in front for concurrent request handling and Redis for caching
intermediate tool results.

## Architecture

```
                 ┌─────────────┐        ┌──────────────────────┐
  client ──────▶ │  Go Gateway │ ─────▶ │ Python Agent Service │
                 │  (:8080)    │        │  (FastAPI, :8000)    │
                 └──────┬──────┘        └──────────┬───────────┘
                        │                            │
                        │        ┌───────────────────┼───────────────────┐
                        │        │            LangGraph tool-calling loop │
                        │        │   ┌────────────┐  ┌─────────────────┐ │
                        │        │   │ Ticket      │  │ Status Report   │ │
                        │        │   │ Triage agent│  │ agent           │ │
                        │        │   └─────┬──────┘  └────────┬────────┘ │
                        │        │         │   ┌──────────────┘          │
                        │        │         ▼   ▼                         │
                        │        │   MCP-registered tools                │
                        │        └─────────┬──────────────────────────────┘
                        │                  │
                        ▼                  ▼
                   ┌─────────────────────────────┐
                   │            Redis             │
                   │  - gateway request cache      │
                   │  - agent tool-result cache    │
                   └───────────────────────────────┘
```

- **`python-agent-service/`** — FastAPI app. `app/agents/graph.py` defines
  the shared LangGraph tool-calling loop; `app/agents/workflows/` has the
  three concrete workflows; `app/agents/tools.py` defines the tools, each
  wrapped with a Redis cache; `app/agents/mcp_server.py` exposes those
  same tools over MCP.
- **`go-gateway/`** — Go service that proxies to the Python service,
  tracks per-request and concurrent-inflight latency, and short-circuits
  fully-cached requests before they hit Python.
- **`benchmark/load_test.py`** — drives concurrent load through the
  gateway and reports real numbers (see below).

## Running it locally

```bash
cp .env.example .env   # add your free GROQ_API_KEY from console.groq.com/keys
docker compose up --build
```

Then:

```bash
# via the Go gateway
curl -X POST http://localhost:8080/workflows/ticket-triage \
  -H "Content-Type: application/json" -d '{"ticket_id": "T-4521"}'

curl -X POST http://localhost:8080/workflows/status-report \
  -H "Content-Type: application/json" \
  -d '{"service_names": ["auth-service", "billing-service"]}'

curl -X POST http://localhost:8080/workflows/data-sync-notify \
  -H "Content-Type: application/json" \
  -d '{"source": "crm", "target": "warehouse"}'
```

Without Docker: run `redis-server`, then in `python-agent-service/`,
`pip install -r requirements.txt && uvicorn app.main:app --reload`, and in
`go-gateway/`, `go run main.go`.

## Generating your own real numbers

```bash
pip install httpx
python benchmark/load_test.py --gateway http://localhost:8080 --concurrency 5
```

This prints actual measured concurrency and cache-latency numbers from
your machine.

## Tests

```bash
cd python-agent-service && python -m pytest tests/ -v
```

## Project structure

```
agentops/
├── python-agent-service/
│   ├── app/
│   │   ├── main.py                 # FastAPI endpoints
│   │   ├── config.py
│   │   └── agents/
│   │       ├── graph.py            # shared LangGraph tool-calling loop
│   │       ├── tools.py            # tools + Redis cache wrapper
│   │       ├── cache.py            # Redis client + cache stats
│   │       ├── mcp_server.py       # MCP registration
│   │       └── workflows/
│   │           ├── ticket_triage.py
│   │           ├── status_report.py
│   │           └── data_sync_notify.py
│   └── tests/
├── go-gateway/
│   ├── main.go
│   ├── handlers/proxy.go           # proxy + request-level cache
│   └── metrics/latency.go          # latency + concurrency tracking
├── benchmark/load_test.py          # generates real perf numbers
├── docs/
│   └── ARCHITECTURE.md
└── docker-compose.yml
```
