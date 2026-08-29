package metrics

import (
	"encoding/json"
	"net/http"
	"sync"
	"time"
)

// LatencyTracker records real per-request latency so gateway performance
// claims are measured, not asserted. Thread-safe for concurrent requests.
type LatencyTracker struct {
	mu       sync.Mutex
	samples  []float64
	inflight int
	maxSeen  int
}

func NewLatencyTracker() *LatencyTracker {
	return &LatencyTracker{}
}

func (t *LatencyTracker) record(ms float64) {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.samples = append(t.samples, ms)
}

func (t *LatencyTracker) enter() {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.inflight++
	if t.inflight > t.maxSeen {
		t.maxSeen = t.inflight
	}
}

func (t *LatencyTracker) exit() {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.inflight--
}

func (t *LatencyTracker) Handler(w http.ResponseWriter, r *http.Request) {
	t.mu.Lock()
	defer t.mu.Unlock()

	var sum float64
	for _, s := range t.samples {
		sum += s
	}
	avg := 0.0
	if len(t.samples) > 0 {
		avg = sum / float64(len(t.samples))
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"request_count":         len(t.samples),
		"avg_latency_ms":        avg,
		"max_concurrent_inflight": t.maxSeen,
	})
}

// Wrap records request latency and concurrent in-flight count around any
// handler. This is how the "5+ concurrent runs without degradation" claim
// gets a real number attached to it.
func Wrap(t *LatencyTracker, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.enter()
		defer t.exit()

		start := time.Now()
		next.ServeHTTP(w, r)
		t.record(float64(time.Since(start).Microseconds()) / 1000.0)
	})
}
