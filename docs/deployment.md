# Deployment Guide

This guide covers the deployment and operation of the RAG system in production.

## Prerequisites

- Python 3.9+
- Docker
- Kubernetes
- Prometheus/Grafana
- Redis
- Qdrant

## System Requirements

### Minimum Requirements

- CPU: 8 cores
- RAM: 32GB
- Storage: 100GB SSD
- Network: 1Gbps

### Recommended

- CPU: 16+ cores
- RAM: 64GB
- Storage: 500GB NVMe
- Network: 10Gbps

## Installation

1. Clone Repository:

   ```bash
   git clone https://github.com/your-org/rag-system.git
   cd rag-system
   ```

2. Configure Environment:

   ```bash
   # Create .env file
   cp .env.example .env
   
   # Edit configuration
   vim .env
   ```

3. Build Containers:

   ```bash
   docker-compose build
   ```

## Kubernetes Deployment

1. Apply Manifests:

   ```bash
   # Create namespace
   kubectl create namespace rag-system
   
   # Apply configurations
   kubectl apply -f k8s/
   ```

2. Verify Deployment:

   ```bash
   kubectl get pods -n rag-system
   kubectl get services -n rag-system
   ```

## Configuration

### Environment Variables

```bash
# Core Settings
RAG_ENV=production
RAG_LOG_LEVEL=INFO
RAG_API_KEY=your-api-key

# Service Endpoints
QDRANT_HOST=qdrant-service
QDRANT_PORT=6333
REDIS_URL=redis://redis-service:6379

# Performance Tuning
RAG_BATCH_SIZE=32
RAG_MAX_CONCURRENT=100
RAG_CACHE_TTL=3600
```

### Kubernetes Config

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-system
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: rag-api
          image: rag-system:latest
          resources:
            requests:
              cpu: "2"
              memory: "4Gi"
            limits:
              cpu: "4"
              memory: "8Gi"
```

## Monitoring Setup

1. Prometheus Configuration:

   ```yaml
   # prometheus.yml
   scrape_configs:
     - job_name: 'rag-system'
       static_configs:
         - targets: ['rag-service:9090']
   ```

2. Grafana Dashboard:

   ```bash
   # Import dashboard
   curl -X POST http://grafana:3000/api/dashboards/import \
     -H "Content-Type: application/json" \
     -d @dashboards/rag-overview.json
   ```

## Scaling

### Horizontal Scaling

1. API Servers:
   - Scale replicas based on CPU/memory
   - Monitor request latency
   - Adjust resource limits

2. Vector Store:
   - Add read replicas
   - Shard data
   - Optimize caching

### Vertical Scaling

1. Resource Allocation:
   - Increase CPU/memory
   - Optimize batch sizes
   - Tune concurrent requests

2. Performance Tuning:
   - Adjust HNSW parameters
   - Optimize cache sizes
   - Fine-tune timeouts

## Backup & Recovery

1. Regular Backups:

   ```bash
   # Backup vector store
   kubectl exec qdrant-0 -- qdrant-backup \
     --output /backups/qdrant-backup.tar.gz
   
   # Backup configurations
   kubectl get configmap -n rag-system -o yaml > configs-backup.yaml
   ```

2. Recovery Process:

   ```bash
   # Restore vector store
   kubectl cp qdrant-backup.tar.gz qdrant-0:/backups/
   kubectl exec qdrant-0 -- qdrant-restore \
     --input /backups/qdrant-backup.tar.gz
   ```

## Security

### Network Security

1. Enable TLS:

   ```bash
   # Generate certificates
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout tls.key -out tls.crt
   
   # Create secret
   kubectl create secret tls rag-tls \
     --key tls.key --cert tls.crt
   ```

2. Configure Ingress:

   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: rag-ingress
   spec:
     tls:
       - secretName: rag-tls
     rules:
       - host: rag.example.com
         http:
           paths:
             - path: /
               pathType: Prefix
               backend:
                 service:
                   name: rag-service
                   port:
                     number: 80
   ```

### Access Control

1. API Authentication:
   - JWT validation
   - Rate limiting
   - IP whitelisting

2. Service Authentication:
   - Service accounts
   - Network policies
   - RBAC configuration

## Maintenance

### Regular Tasks

1. System Updates:

   ```bash
   # Update containers
   kubectl set image deployment/rag-system \
     rag-api=rag-system:latest
   
   # Rolling restart
   kubectl rollout restart deployment rag-system
   ```

2. Health Checks:

   ```bash
   # Check system status
   kubectl get pods -n rag-system
   kubectl logs -f deployment/rag-system
   ```

### Troubleshooting

1. Check Logs:

   ```bash
   # View service logs
   kubectl logs -f deployment/rag-system
   
   # Check events
   kubectl get events -n rag-system
   ```

2. Debug Issues:

   ```bash
   # Shell into container
   kubectl exec -it deployment/rag-system -- /bin/bash
   
   # Check metrics
   curl localhost:9090/metrics
   ```

## Performance Tuning

### Vector Store

1. HNSW Settings:
   ```yaml
   store:
     hnsw:
       m: 32
       ef_construct: 128
       ef_search: 100
   ```

2. Cache Configuration:
   ```yaml
   cache:
     size: 10000
     ttl: 3600
     shards: 3
   ```

### Query Processing

1. Batch Settings:
   ```yaml
   processing:
     batch_size: 32
     max_concurrent: 100
     timeout: 30
   ```

2. Resource Limits:
   ```yaml
   resources:
     cpu_limit: 4
     memory_limit: 8Gi
     max_connections: 1000
   ```

## Monitoring & Alerts

### Key Metrics

1. Performance:
   - Query latency
   - Cache hit rate
   - Error rate

2. Resources:
   - CPU usage
   - Memory usage
   - Network I/O

### Alert Rules

```yaml
groups:
  - name: rag-alerts
    rules:
      - alert: HighLatency
        expr: rag_query_latency_seconds > 0.5
        for: 5m
        
      - alert: HighErrorRate
        expr: rate(rag_error_total[5m]) > 0.01
        for: 5m
```

## Disaster Recovery

### Backup Strategy

1. Regular Backups:
   - Vector store data
   - Configurations
   - Logs and metrics

2. Recovery Testing:
   - Periodic drills
   - Validation checks
   - Documentation updates

### Recovery Procedures

1. System Restore:
   - Load backups
   - Verify data
   - Test functionality

2. Validation Steps:
   - Check metrics
   - Run test queries
   - Verify integrations