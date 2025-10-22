# Switching to Qdrant

This guide covers the process of switching ASTRA's dense retrieval backend from local to Qdrant.

## Prerequisites

- Qdrant server running (local or containerized)
- ASTRA core system operational
- `config/rag.yaml` configured

## Configuration

Update `config/rag.yaml` to use Qdrant:

```yaml
dense_index:
  type: "qdrant"
  config:
    url: "http://localhost:6333"
    collection_name: "astra_documents"
    distance: "Cosine"
    batch_size: 100
    cache_dir: "data/cache/qdrant"
```

## Verification Steps

1. Check Qdrant Connection:
```powershell
curl http://localhost:6333/collections/astra_documents
```

2. Monitor Ingestion:
- Watch logs in `data/logs/ingestion.jsonl`
- Verify `ingestion.complete` events
- Check document count in metrics

3. Verify Cache Behavior:
- First query: Cache miss, metrics show Qdrant hit
- Repeat query: Cache hit, faster response
- Cache entries in `data/cache/qdrant`

## Troubleshooting

### Common Issues

1. Connection Failures
- Check Qdrant process/container status
- Verify firewall rules
- Test connection with curl

2. Cache Issues
- Clear cache: Delete contents of `data/cache/qdrant`
- Verify cache hit metrics
- Check cache entry TTLs

3. Performance Issues
- Monitor `data/logs/telemetry.jsonl`
- Check Qdrant resource usage
- Verify index optimization

### Recovery Procedures

1. Circuit Breaker Activation:
- Check logs for failure patterns
- Wait for reset timeout
- Verify health status recovery

2. Cache Corruption:
- Stop ASTRA service
- Clear cache directory
- Restart service
- Monitor rewarming

## Health Checks

1. Qdrant Status:
```powershell
Get-Service qdrant
curl http://localhost:6333/health
```

2. Collection Status:
```powershell
curl http://localhost:6333/collections/astra_documents
```

3. ASTRA Integration:
- Run test queries
- Check telemetry
- Verify cache behavior

## Maintenance

1. Regular Tasks:
- Monitor disk usage
- Check collection optimization
- Verify backup integrity

2. Optimization:
- Run VACUUM periodically
- Clear stale cache entries
- Update vector indexes

3. Backup/Restore:
- Snapshot collection data
- Backup configuration
- Test restore procedures