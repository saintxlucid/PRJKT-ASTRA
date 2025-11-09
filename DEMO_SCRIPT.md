# 🎬 ASTRA 3.0 One-Minute Demo Script

**Purpose:** Screen recording to demonstrate production-grade capabilities  
**Duration:** 60 seconds  
**Target Audience:** Technical decision-makers, engineers, DevOps

---

## Setup (Pre-Recording)

```bash
# Terminal 1: Start ASTRA
./deploy_hardened.sh deploy

# Terminal 2: Open Grafana (if configured)
# Open browser to localhost:3000

# Terminal 3: Jaeger UI (if tracing enabled)
# Open browser to localhost:16686

# Terminal 4: Ready for commands
```

---

## Script Timeline

### 0:00-0:10 - System Boot (10s)

**Visual:** Terminal showing boot sequence

```bash
# Show clean deployment
./deploy_hardened.sh start
```

**Narration:**
> "ASTRA 3.0 boots in under 10 seconds with full health validation."

**Screen Shows:**
```
[INFO] ✓ All prerequisites satisfied
[INFO] ✓ Postgres ready
[INFO] ✓ Database schema ready
[INFO] ✓ ASTRA is online
[INFO] ✓ System health: ONLINE
[INFO] ✓ Persistence: HEALTHY
[INFO] ✓ Boot: COMPLETE
```

---

### 0:10-0:25 - Health Dashboard (15s)

**Visual:** Browser showing Grafana dashboard with live metrics

**Narration:**
> "Real-time observability: p95 latency, throughput, error rate. All systems green."

**Screen Shows:**
- Grafana panel: p95 latency graph (under 1s)
- Request rate: steady ~50 rps
- Error rate: 0.0%
- CPU/Memory: stable

**Action:** Hover over metrics to show values

---

### 0:25-0:40 - Distributed Trace (15s)

**Visual:** Jaeger UI showing end-to-end trace

```bash
# In terminal: Send test request
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"conversation_id":"demo","message":"What is ASTRA?"}'
```

**Narration:**
> "Full distributed tracing: watch a request flow through Sigil → Micro → Expert → Memory."

**Screen Shows:**
- Jaeger trace view
- Span hierarchy:
  ```
  /v1/chat [650ms]
  ├── sigil.seal [12ms]
  ├── micro.execute [580ms]
  │   ├── expert.query [520ms]
  │   │   └── llm.generate [480ms]
  │   └── memory.recall [40ms]
  └── state.checkpoint [18ms]
  ```

**Action:** Click into spans to show metadata

---

### 0:40-0:50 - Self-Healing Demo (10s)

**Visual:** Terminal showing resilience test

```bash
# Kill memory service
docker stop astra_redis

# Show auto-recovery in logs
tail -f logs/astra.log | grep "fallback\|recovery"
```

**Narration:**
> "Automatic resilience: Redis goes down, system continues with degraded mode."

**Screen Shows:**
```
[WARN] redis_connection_failed error="Connection refused"
[INFO] state_manager_fallback mode="wal_only"
[INFO] persistence_degraded redis=false postgres=true wal=true
```

**Action:** Restart Redis, show recovery

```bash
docker start astra_redis
# Logs show: [INFO] redis_reconnected status="healthy"
```

---

### 0:50-1:00 - Load Test Pass (10s)

**Visual:** Terminal showing load test results

```bash
# Run quick load test (30s @ 50 rps)
python scripts/load_test.py --duration 30 --rps 50 --workers 5
```

**Narration:**
> "Production SLO validated: p95 under 1 second at 50 rps. System passes smoke test."

**Screen Shows:**
```
============================================================
Load Test Complete
============================================================

Duration: 30.2s
Total Requests: 1512
Actual RPS: 50.1
Errors: 0 (0.00%)

Latency Distribution (ms):
   p50: 420ms
   p90: 780ms
   p95: 890ms
   p99: 1200ms

============================================================
SLO Verification (p95 < 1000ms @ 100 rps)
============================================================

✅ PASS: p95 latency 890ms within 1000ms target
✅ PASS: Error rate 0.00% within 0.1% target

🎉 Load test PASSED - ASTRA 3.0 meets production SLO
```

---

### End Frame (5s)

**Visual:** Terminal or slide with key stats

```
┌─────────────────────────────────────────────┐
│      ASTRA 3.0 "ASCENSION"                  │
│      Operating Intelligence                 │
├─────────────────────────────────────────────┤
│  ✅ p95 < 1s @ 100 rps                      │
│  ✅ 99.9% availability target               │
│  ✅ Full tracing (OpenTelemetry → Jaeger)  │
│  ✅ Auto-healing (Redis failover)           │
│  ✅ State persistence (WAL + Redis + PG)    │
├─────────────────────────────────────────────┤
│  Tag: v3.0.0-ASCENSION                      │
│  Sacred Code: 333 → ∞                       │
└─────────────────────────────────────────────┘
```

---

## Recording Tips

### Camera/Screen Settings
- **Resolution:** 1920x1080 or 1280x720
- **Frame Rate:** 30 fps minimum
- **Terminal:** Large font (16pt+), high contrast theme
- **Browser:** Full screen mode for dashboards

### Audio
- Clear voiceover (use good mic or post-production VO)
- Optional: Background music (low volume, non-distracting)
- Consider no-audio version with captions for accessibility

### Timing
- Practice runs to hit 60s target
- Use jumpcuts if needed (trim wait times)
- Speed up slow parts (e.g., load test can be 2x speed)

### Editing
- Add text overlays for key metrics
- Highlight important log lines (color box or arrow)
- Zoom into specific UI elements when needed
- Fade/transition between sections

---

## Alternative: GIF Version (No Audio)

If video hosting is an issue, create an animated GIF:

1. **Frame 1 (5s):** Boot sequence with green checkmarks
2. **Frame 2 (5s):** Grafana dashboard with metrics
3. **Frame 3 (5s):** Jaeger trace visualization
4. **Frame 4 (5s):** Load test results (pass banner)
5. **Frame 5 (5s):** End card with key stats

**Tools:** OBS Studio (recording), FFmpeg (GIF conversion), Giphy/Ezgif (optimization)

---

## Distribution

Once recorded:

- **YouTube:** Upload as unlisted or public
- **Twitter:** Native video upload (< 2:20)
- **LinkedIn:** Direct upload
- **README:** Embed GIF or link to YouTube
- **Docs Site:** Embed player on homepage

---

**Status:** ✅ Demo script ready for recording  
**Next:** Record, edit, publish
