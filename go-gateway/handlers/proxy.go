package handlers

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"io"
	"log"
	"net/http"
	"time"

	"github.com/redis/go-redis/v9"
)

// Proxy forwards workflow requests to the Python agent service. Before
// doing so, it checks Redis directly for a cached final result keyed on
// the request body's hash, so identical concurrent requests (a common
// pattern when multiple operational triggers fire for the same entity)
// can be served without even hitting the Python process.
type Proxy struct {
	pythonServiceURL string
	redis            *redis.Client
	httpClient       *http.Client
}

func NewProxy(pythonServiceURL, redisAddr string) *Proxy {
	return &Proxy{
		pythonServiceURL: pythonServiceURL,
		redis:            redis.NewClient(&redis.Options{Addr: redisAddr}),
		httpClient:       &http.Client{Timeout: 30 * time.Second},
	}
}

func (p *Proxy) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "failed to read body", http.StatusBadRequest)
		return
	}

	cacheKey := "gateway:result:" + r.URL.Path + ":" + hashBody(body)
	ctx := context.Background()

	if cached, err := p.redis.Get(ctx, cacheKey).Result(); err == nil {
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("X-Cache", "HIT")
		w.Write([]byte(cached))
		return
	}

	req, err := http.NewRequest(r.Method, p.pythonServiceURL+r.URL.Path, bytes.NewReader(body))
	if err != nil {
		http.Error(w, "failed to build upstream request", http.StatusInternalServerError)
		return
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := p.httpClient.Do(req)
	if err != nil {
		log.Printf("upstream error: %v", err)
		http.Error(w, "upstream request failed", http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		http.Error(w, "failed to read upstream response", http.StatusInternalServerError)
		return
	}

	if resp.StatusCode == http.StatusOK {
		// Short TTL: this is a request-level cache, distinct from the
		// tool-level cache the Python service maintains internally.
		p.redis.Set(ctx, cacheKey, respBody, 30*time.Second)
	}

	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("X-Cache", "MISS")
	w.WriteHeader(resp.StatusCode)
	w.Write(respBody)
}

func hashBody(body []byte) string {
	sum := sha256.Sum256(body)
	return hex.EncodeToString(sum[:])[:16]
}
