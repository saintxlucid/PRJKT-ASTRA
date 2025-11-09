# Incident Report — ASTRA Core

**SEV:** SEV1 | SEV2 | SEV3  
**Start:** YYYY-MM-DD HH:MM (UTC+2)  
**End:** YYYY-MM-DD HH:MM (UTC+2)  
**Owner:**  
**Status:** Resolved | Mitigating | Monitoring

## Summary
One-paragraph what/impact/scope.

## Impact
- Users affected, symptoms, endpoints (e.g., /answer 5xx 12%)

## Timeline (UTC+2)
- 14:02 Alert fired (RAGLatencyP95 > 2.5s)
- 14:05 On-call acks; checks /ready, queue depth 180
- 14:08 Drain + rollback to v1.0.0-core
- 14:15 SLOs restored

## Detection
Which alert + dashboards.

## Root Cause
Technical trigger, why now.

## Mitigation
Steps taken (drain, shedder, rollback).

## Corrective Actions
- [ ] Add backpressure thresholds tighter
- [ ] Perf test at 2× current QPS
- [ ] Fix planner O(n^2) clustering

## Attachments
- Grafana snapshots, logs with req_id/err_id, PRs