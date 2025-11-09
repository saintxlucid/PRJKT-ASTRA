# ASTRA Bridge - Production Runbook

This runbook covers deployment, health checks, monitoring, rollback, backups, and alerts for ASTRA Bridge in production.

## Quick Reference

- Namespace: `astra`
- Service: `bridge`
- Ingress: `bridge.example.com` (replace)
- Container image: `REGISTRY/your-org/astra-bridge:latest` (replace)

## Deploy

1) Build and push image (local):

```powershell
docker build -t REGISTRY/your-org/astra-bridge:prod -f services/bridge/Dockerfile .
docker push REGISTRY/your-org/astra-bridge:prod
```

2) Apply manifests:

```powershell
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secret-bridge.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/bridge-deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
```

## Health Checks

- Readiness: `GET /health`
- Metrics: `GET /metrics` (Prometheus)

```powershell
kubectl -n astra get pods -l app=bridge
kubectl -n astra describe pod <pod>
```

## Logs

```powershell
kubectl -n astra logs -l app=bridge -f --tail=200
```

## Rollout and Rollback

```powershell
kubectl -n astra rollout status deployment/bridge
kubectl -n astra rollout undo deployment/bridge
```

## Scaling

```powershell
kubectl -n astra scale deployment bridge --replicas=0
kubectl -n astra scale deployment bridge --replicas=2
```

## Backups / Data Management

- Bridge audit log: `/data/bridge_audit.log` → ship to ELK/CloudWatch
- Qdrant snapshots: `/qdrant/storage` → offsite snapshots
- Models: store source in S3/GCS; mount only in-use models

## Monitoring & Alerts

- Prometheus: scrape `/metrics` from bridge service
- Grafana dashboards:
  - bridge_calls_total by tool and status
  - bridge_call_duration_seconds histogram and quantiles (P95)
  - CPU/Memory, restarts, PV usage

Alert examples (Prometheus rules):

```yaml
groups:
- name: bridge.rules
  rules:
  - alert: BridgeHighErrorRate
    expr: rate(bridge_calls_total{status="error"}[5m]) / rate(bridge_calls_total[5m]) > 0.05
    for: 5m
    labels:
      severity: page
    annotations:
      summary: "Bridge error rate >5% ({{ $value }})"
```

## Security

- Use K8s secrets or Vault for `BRIDGE_API_KEY` and internal endpoints
- Enable `BRIDGE_ENFORCE_PER_TOOL_SCOPE=true` for per-tool scopes
- Rate limiting and quotas configured per API key
- TLS via Ingress + cert-manager (Let’s Encrypt)
- Remove shell adapter for production if possible

## Incident Response

1. Confirm impact (error rate, latency, user reports)
2. Check logs and recent deploy
3. Rollback if necessary
4. Escalate to on-call SRE/Ops

Common commands:

```powershell
kubectl -n astra get events --sort-by=.lastTimestamp
kubectl -n astra describe deployment bridge
kubectl -n astra get ingress bridge-ingress -o yaml
```

## Change Management

- Changes land via PRs; CI/CD runs tests and deploys to prod on main
- Use semantic version tags for images if preferred
- Keep a deployment log for audit compliance
