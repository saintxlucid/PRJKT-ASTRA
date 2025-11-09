# Capacity Planning Policy (Quarterly Review)

**Review Cycle**: Quarterly + ad-hoc triggers  
**Window**: Rolling 30 days  
**Owner**: SRE + Infrastructure Team

## Triggers (Act within 7 days)

### Compute
- **CPU > 60% avg for 3 consecutive days** → +2 replicas (HPA floor increase)
- **Memory > 70% avg for 3 consecutive days** → Increase pod memory limits by 20%
- **Pod count at HPA max for > 4 hours/day** → Raise HPA max by 50%

### Storage
- **PVC > 70% full** → Scale PVC storage class or add shards
- **Backup size growth > 20% WoW** → Review retention policy + compression

### Database
- **Connection pool saturation > 80% for > 1 hour** → Increase pool size
- **Query p95 degradation > 10% WoW** → Index optimization or read replicas

### Vector Database
- **Recall@k degradation > 2% WoW** → Reindex or tune ANN parameters
- **Query latency p95 > target for 3 consecutive days** → Add shards/replicas

### Token Throughput (LLM)
- **Growth > 25% MoM** → Add model nodes + autoscaler tuning
- **Queue depth > 20 for > 30 min** → Increase concurrency limits

## Actions

### Immediate (Within 7 days)
1. Scale resources (HPA min/max, node pool size, DB replicas)
2. File infrastructure tickets for next-tier capacity
3. Update cost guardrails vs SLO compliance

### Quarterly Review
1. Analyze 90-day trends (CPU, memory, storage, throughput)
2. Forecast 6-month capacity needs
3. Budget approval for infra upgrades
4. Update capacity model in `audit/capacity_model.xlsx`

## Cost Optimization
- Right-size underutilized resources (CPU/memory requests)
- Evaluate spot instances for non-critical workloads
- Review data retention policies (logs, backups, metrics)

---
**Last Review**: 2025-11-01  
**Next Review**: 2026-02-01
