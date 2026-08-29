"""
Load test / benchmark harness for AgentOps.

This produces REAL numbers from YOUR machine — this is what you should
actually cite (or re-derive) in an interview instead of reusing the
bullet-point numbers verbatim, since those depend on a real production
workload this rebuild can't replicate from scratch.

What it measures:
  1. Concurrency: fires N concurrent workflow runs at the gateway and
     confirms they all complete successfully (proves "N+ concurrent runs
     without degradation").
  2. Cache effect on latency: runs the same workflow request twice and
     compares first-call vs second-call latency, since the second call
     should hit the Redis-cached tool results (proves the caching->latency
     claim, with a real percentage).

Usage:
    python benchmark/load_test.py --gateway http://localhost:8080 --concurrency 5
"""
import argparse
import concurrent.futures
import statistics
import time

import httpx


def run_one(base_url: str, ticket_id: str) -> float:
    start = time.perf_counter()
    resp = httpx.post(
        f"{base_url}/workflows/ticket-triage",
        json={"ticket_id": ticket_id},
        timeout=60,
    )
    resp.raise_for_status()
    return (time.perf_counter() - start) * 1000


def concurrency_test(base_url: str, concurrency: int) -> dict:
    ticket_ids = [f"T-{i}" for i in range(concurrency)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        start = time.perf_counter()
        futures = [pool.submit(run_one, base_url, tid) for tid in ticket_ids]
        latencies = [f.result() for f in concurrent.futures.as_completed(futures)]
        wall_clock_ms = (time.perf_counter() - start) * 1000

    return {
        "concurrency": concurrency,
        "all_succeeded": len(latencies) == concurrency,
        "wall_clock_ms": round(wall_clock_ms, 1),
        "avg_individual_latency_ms": round(statistics.mean(latencies), 1),
        "p95_individual_latency_ms": round(
            statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else latencies[0], 1
        ),
    }


def cache_effect_test(base_url: str, ticket_id: str = "T-CACHE-TEST") -> dict:
    first_ms = run_one(base_url, ticket_id)
    second_ms = run_one(base_url, ticket_id)  # same args -> should hit cache
    pct_drop = round((1 - second_ms / first_ms) * 100, 1) if first_ms else 0.0
    return {
        "first_call_ms": round(first_ms, 1),
        "second_call_ms_cached": round(second_ms, 1),
        "latency_reduction_pct": pct_drop,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gateway", default="http://localhost:8080")
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()

    print("Running concurrency test...")
    conc_result = concurrency_test(args.gateway, args.concurrency)
    print(conc_result)

    print("\nRunning cache-effect test...")
    cache_result = cache_effect_test(args.gateway)
    print(cache_result)

    print(
        "\nThese numbers are specific to this run, on this machine, with the "
        "simulated tool latencies in app/agents/tools.py. Re-run after tuning "
        "those sleep() values to match a workload you can describe, and quote "
        "THIS output in an interview, not the original resume figures."
    )
