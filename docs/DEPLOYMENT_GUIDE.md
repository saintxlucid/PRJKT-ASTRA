# ASTRA Ingestion Service Deployment Guide

## Overview

This guide details the deployment process for the ASTRA Ingestion Service in a distributed environment. The service is containerized and designed to run on Kubernetes, with PostgreSQL for persistent storage and Redis for caching.

## Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl CLI tool
- Docker (v20.10+)
- Helm v3

## Local Development Setup

1. Install Docker and Docker Compose:

   ```bash
   # Windows (PowerShell)
   winget install Docker.DockerDesktop
   ```

2. Clone the repository and navigate to the project directory:

   ```bash
   git clone <repository-url>
   cd astra-core
   ```

3. Start the development environment:

   ```bash
   docker-compose up -d
   ```

4. Verify services are running:

   ```bash
   docker-compose ps
   ```

## Kubernetes Deployment

### 1. Create Namespace

```bash
kubectl create namespace astra
kubectl config set-context --current --namespace=astra
```

### 2. Deploy PostgreSQL

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install astra-postgres bitnami/postgresql \
  --set auth.database=astra \
  --set auth.username=astra \
  --set auth.password=<your-password>
```

### 3. Deploy Redis

```bash
helm install astra-redis bitnami/redis \
  --set auth.enabled=false \
  --set architecture=standalone
```

### 4. Create Secrets

```bash
kubectl create secret generic astra-secrets \
  --from-literal=postgres-user=astra \
  --from-literal=postgres-password=<your-password>
```

### 5. Deploy Ingestion Service

```bash
kubectl apply -f k8s/ingestion-service.yaml
```

### 6. Verify Deployment

```bash
kubectl get pods
kubectl get services
kubectl get hpa
```

## Monitoring Setup

1. Install Prometheus and Grafana:
   ```bash
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm install prometheus prometheus-community/kube-prometheus-stack
   ```

2. Access Grafana dashboard:
   ```bash
   kubectl port-forward svc/prometheus-grafana 3000:80
   ```

3. Import the provided Grafana dashboard (ID: TBD)

## Scaling Configuration

The service is configured to scale automatically based on CPU utilization:

- Minimum replicas: 3
- Maximum replicas: 10
- Target CPU utilization: 70%

To modify scaling parameters:

```bash
kubectl edit hpa ingestion-service-hpa
```

## Maintenance Tasks

### Backup PostgreSQL Data

```bash
kubectl exec -it astra-postgres-0 -- pg_dump -U astra > backup.sql
```

### Monitor Logs

```bash
kubectl logs -f -l app=ingestion-service
```

### Update Configuration

1. Edit the ConfigMap:
   ```bash
   kubectl edit configmap astra-config
   ```

2. Restart the pods:
   ```bash
   kubectl rollout restart deployment ingestion-service
   ```

## Troubleshooting

### Common Issues

1. Pod Startup Failures
   ```bash
   kubectl describe pod <pod-name>
   kubectl logs <pod-name>
   ```

2. Database Connection Issues
   ```bash
   kubectl exec -it <pod-name> -- python -c "from astra.service.database import db_manager; import asyncio; asyncio.run(db_manager.initialize())"
   ```

3. File Processing Issues
   ```bash
   kubectl exec -it <pod-name> -- ls -la /data/ingest/failed
   ```

### Health Checks

```bash
kubectl get events --sort-by=.metadata.creationTimestamp
kubectl describe deployment ingestion-service
```

## Security Considerations

1. Network Policies

   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: ingestion-service-policy
   spec:
     podSelector:
       matchLabels:
         app: ingestion-service
     ingress:
     - from:
       - podSelector:
           matchLabels:
             app: api-gateway
     egress:
     - to:
       - podSelector:
           matchLabels:
             app: postgres
     - to:
       - podSelector:
           matchLabels:
             app: redis
   ```

2. Pod Security Context

   ```yaml
   securityContext:
     runAsUser: 1000
     runAsGroup: 1000
     fsGroup: 1000
   ```

## Production Checklist

- [ ] Set resource limits and requests
- [ ] Configure persistent storage
- [ ] Set up monitoring and alerting
- [ ] Configure backup strategy
- [ ] Implement network policies
- [ ] Set up logging aggregation
- [ ] Configure horizontal pod autoscaling
- [ ] Set up SSL/TLS
- [ ] Configure health checks
- [ ] Set up CI/CD pipeline