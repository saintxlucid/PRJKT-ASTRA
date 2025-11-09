# Go-Live Validation Report — ASTRA Core

**Commit:** <SHA>  
**Date:** <YYYY-MM-DD> **Env:** <dev/stage>  
**Verdict:** ✅ PASS | ❌ FAIL

## Summary
- Health: live ✓ ready ✓ full: ok|degraded(reason)
- SLOs: p95 /answer = <ms>, first token stream = <ms>, error% = <x%>
- Backpressure: triggered at depth <N>, shed % <x%>, no 5xx spikes

## Checks
- Endpoints: /live ✓ /ready ✓ /health/full ✓ /answer ✓ /stream ✓
- Citations present ✓  Budget utilization: <used>/<limit> (max <x%>)
- Circuit breakers: memory ✓ inference ✓ fallbacks ✓
- Graceful drain: <seconds> (target ≤10s)

## Load Test (Locust)
- Users: <U>, Hatch: <R/s>, Time: <T>
- p50/p95 /answer: <ms>/<ms>  | Error%: <x%>
- stream first token p95: <ms>

## Recommendations
- …