// AgentOps Go gateway.
//
// Sits in front of the Python FastAPI agent service and:
//  1. Routes workflow requests to it, running many in flight concurrently
//     via goroutines rather than a single blocking call per request.
//  2. Records per-request latency so the "cutting response latency by X%"
//     claim is something you can actually measure, not assert.
//  3. Does a fast Redis existence check before proxying, so a request that
//     is already fully cached downstream never even pays the network hop
//     to Python.
//
// This is the piece that makes "5+ concurrent agent workflow runs without
// degradation" a testable claim: see benchmark/load_test.py, which drives
// load through this gateway and reports real numbers.
package main

import (
	"log"
	"net/http"
	"os"

	"agentops-gateway/handlers"
	"agentops-gateway/metrics"
)

func main() {
	pythonServiceURL := getEnv("PYTHON_SERVICE_URL", "http://localhost:8000")
	redisAddr := getEnv("REDIS_ADDR", "localhost:6379")
	port := getEnv("GATEWAY_PORT", "8080")

	proxy := handlers.NewProxy(pythonServiceURL, redisAddr)
	tracker := metrics.NewLatencyTracker()

	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok"}`))
	})
	mux.HandleFunc("/metrics/latency", tracker.Handler)
	mux.Handle("/workflows/", metrics.Wrap(tracker, proxy))

	log.Printf("agentops-gateway listening on :%s, proxying to %s", port, pythonServiceURL)
	if err := http.ListenAndServe(":"+port, mux); err != nil {
		log.Fatal(err)
	}
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
