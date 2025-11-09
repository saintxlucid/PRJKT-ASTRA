# 🔐 ASTRA Core - Backup and Security Validation

**Purpose**: Production backup procedures and security validation  
**Compliance**: SOC 2, ISO 27001, GDPR  
**Last Review**: 2025-11-01

---

## 📋 Table of Contents

1. [Backup Procedures](#backup-procedures)
2. [Security Validation](#security-validation)
3. [Disaster Recovery](#disaster-recovery)
4. [Compliance Checklist](#compliance-checklist)
5. [Security Incident Response](#security-incident-response)

---

## 💾 Backup Procedures

### **Backup Strategy**

#### **Backup Frequency**
- **Application Configuration**: Before every deployment
- **Application State**: Every 6 hours
- **Logs**: Continuous (streamed to S3/Azure Blob)
- **Metrics**: Retained in Prometheus for 30 days
- **Database**: Every 4 hours (if applicable)

#### **Retention Policy**
- **Daily Backups**: 7 days
- **Weekly Backups**: 4 weeks
- **Monthly Backups**: 12 months
- **Yearly Backups**: 7 years (compliance)

### **1. Kubernetes Configuration Backup**

```bash
# Backup all ASTRA Core Kubernetes resources
kubectl get all -n astra-production -o yaml > \
  backups/k8s/astra-core-all-$(date +%Y%m%d-%H%M%S).yaml

# Backup individual resources
kubectl get deployment astra-core -n astra-production -o yaml > \
  backups/k8s/deployment-$(date +%Y%m%d-%H%M%S).yaml

kubectl get service astra-core -n astra-production -o yaml > \
  backups/k8s/service-$(date +%Y%m%d-%H%M%S).yaml

kubectl get configmap -n astra-production -o yaml > \
  backups/k8s/configmap-$(date +%Y%m%d-%H%M%S).yaml

kubectl get secret -n astra-production -o yaml > \
  backups/k8s/secrets-$(date +%Y%m%d-%H%M%S).yaml.enc

# Encrypt secrets backup
gpg --encrypt --recipient ops@company.com \
  backups/k8s/secrets-$(date +%Y%m%d-%H%M%S).yaml

# Upload to secure storage
aws s3 cp backups/k8s/ s3://astra-backups/k8s/ --recursive
```

### **2. Application State Backup**

```bash
# Backup application data from persistent volumes
kubectl exec -n astra-production deployment/astra-core -- \
  tar czf /tmp/astra-data-$(date +%Y%m%d-%H%M%S).tar.gz /app/data

kubectl cp astra-production/astra-core-pod:/tmp/astra-data-*.tar.gz \
  backups/data/

# Upload to backup storage
aws s3 cp backups/data/ s3://astra-backups/data/ --recursive
```

### **3. Database Backup** (if applicable)

```bash
# PostgreSQL backup
pg_dump -h prod-db-host \
  -U astra_user \
  -d astra_db \
  --format=custom \
  --file=backups/db/astra-db-$(date +%Y%m%d-%H%M%S).dump

# Verify backup integrity
pg_restore --list backups/db/astra-db-*.dump

# Encrypt and upload
gpg --encrypt --recipient dba@company.com \
  backups/db/astra-db-*.dump

aws s3 cp backups/db/ s3://astra-backups/db/ --recursive
```

### **4. Metrics and Logs Backup**

```bash
# Export Prometheus metrics snapshot
curl -X POST http://prometheus:9090/api/v1/admin/tsdb/snapshot

# Copy snapshot to backup location
kubectl cp prometheus/prometheus-pod:/prometheus/snapshots/latest \
  backups/metrics/snapshot-$(date +%Y%m%d-%H%M%S)

# Backup Grafana dashboards
curl -H "Authorization: Bearer $GRAFANA_API_KEY" \
  http://grafana:3000/api/search?type=dash-db | \
  jq -r '.[] | .uid' | while read uid; do
    curl -H "Authorization: Bearer $GRAFANA_API_KEY" \
      http://grafana:3000/api/dashboards/uid/$uid > \
      backups/grafana/dashboard-$uid-$(date +%Y%m%d).json
done

# Backup logs from Loki/Elasticsearch
# (Implementation depends on log aggregation system)
```

### **5. Automated Backup Script**

```bash
#!/bin/bash
# backups/scripts/automated-backup.sh

set -e

BACKUP_DIR="/backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Starting ASTRA Core backup..."

# 1. Kubernetes resources
echo "Backing up Kubernetes resources..."
kubectl get all -n astra-production -o yaml > "$BACKUP_DIR/k8s-all.yaml"
kubectl get configmap -n astra-production -o yaml > "$BACKUP_DIR/configmaps.yaml"
kubectl get secret -n astra-production -o yaml | \
  gpg --encrypt --recipient ops@company.com > "$BACKUP_DIR/secrets.yaml.gpg"

# 2. Application data
echo "Backing up application data..."
kubectl exec -n astra-production deployment/astra-core -- \
  tar czf /tmp/app-data.tar.gz /app/data 2>/dev/null || true
kubectl cp astra-production/$(kubectl get pod -n astra-production -l app=astra-core -o name | head -1):/tmp/app-data.tar.gz \
  "$BACKUP_DIR/app-data.tar.gz" 2>/dev/null || true

# 3. Database
echo "Backing up database..."
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME \
  --format=custom --file="$BACKUP_DIR/database.dump" 2>/dev/null || true

# 4. Encrypt everything
echo "Encrypting backup..."
tar czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
gpg --encrypt --recipient ops@company.com "$BACKUP_DIR.tar.gz"

# 5. Upload to S3
echo "Uploading to S3..."
aws s3 cp "$BACKUP_DIR.tar.gz.gpg" \
  s3://astra-backups/automated/$(date +%Y/%m/%d)/

# 6. Cleanup local files
rm -rf "$BACKUP_DIR" "$BACKUP_DIR.tar.gz" "$BACKUP_DIR.tar.gz.gpg"

# 7. Verify backup
aws s3 ls s3://astra-backups/automated/$(date +%Y/%m/%d)/

echo "Backup completed successfully!"
```

### **6. Backup Verification**

```bash
# Test restore from backup
# 1. Download latest backup
aws s3 cp s3://astra-backups/automated/latest.tar.gz.gpg /tmp/

# 2. Decrypt
gpg --decrypt /tmp/latest.tar.gz.gpg > /tmp/latest.tar.gz

# 3. Extract
tar xzf /tmp/latest.tar.gz -C /tmp/restore-test/

# 4. Verify contents
ls -la /tmp/restore-test/
kubectl apply --dry-run=client -f /tmp/restore-test/k8s-all.yaml

# 5. Cleanup
rm -rf /tmp/restore-test /tmp/latest.tar.gz*
```

---

## 🔒 Security Validation

### **1. Container Image Security**

```bash
# Scan Docker image for vulnerabilities
trivy image astra-core:latest \
  --severity HIGH,CRITICAL \
  --format json \
  --output security-reports/trivy-$(date +%Y%m%d).json

# Check for secrets in image
docker history astra-core:latest --no-trunc | grep -i -E '(password|secret|key|token)'

# Verify image signature
cosign verify --key cosign.pub astra-core:latest

# Check image provenance
docker buildx imagetools inspect astra-core:latest --format "{{json .Provenance}}"
```

### **2. Kubernetes Security**

```bash
# Run kube-bench security audit
kube-bench run --targets node,policies,managedservices \
  --json > security-reports/kube-bench-$(date +%Y%m%d).json

# Check Pod Security Standards
kubectl get pods -n astra-production -o json | \
  jq '.items[] | select(.spec.securityContext.runAsNonRoot != true)'

# Verify RBAC policies
kubectl auth can-i --list --as system:serviceaccount:astra-production:astra-core

# Check NetworkPolicies
kubectl get networkpolicy -n astra-production

# Audit admission controllers
kubectl get validatingwebhookconfigurations
kubectl get mutatingwebhookconfigurations
```

### **3. Network Security**

```bash
# Verify TLS certificates
echo | openssl s_client -servername astra-core.prod -connect astra-core.prod:443 2>/dev/null | \
  openssl x509 -noout -dates

# Check for open ports
nmap -sT -O astra-core.prod

# Verify firewall rules (AWS Security Groups)
aws ec2 describe-security-groups \
  --filters Name=group-name,Values=astra-production \
  --query 'SecurityGroups[*].IpPermissions'

# Test WAF rules
curl -H "User-Agent: malicious-bot" https://astra-core.prod/
curl -X POST https://astra-core.prod/ -d "'; DROP TABLE users;--"
```

### **4. Secrets Management**

```bash
# Verify secrets are encrypted at rest
kubectl get secrets -n astra-production -o json | \
  jq '.items[].metadata.annotations["encryption.kubernetes.io"]'

# Check for hardcoded secrets in code
git grep -i -E '(password|secret|key|token)\s*=\s*["\']' -- '*.py' '*.yaml'

# Audit secret access
kubectl get events -n astra-production | grep -i secret

# Verify secrets rotation
kubectl get secret -n astra-production -o json | \
  jq '.items[] | {name: .metadata.name, created: .metadata.creationTimestamp}'
```

### **5. Authentication & Authorization**

```bash
# Verify API authentication is required
curl -X POST http://astra-core.prod/answer \
  -H "Content-Type: application/json" \
  -d '{"query":"test"}'
# Should return 401/403 if auth is required

# Check rate limiting is active
for i in {1..100}; do
  curl -X POST http://astra-core.prod/answer \
    -H "Content-Type: application/json" \
    -d '{"query":"rate limit test"}' &
done
wait
# Should see 429 responses

# Verify RBAC roles
kubectl get roles,rolebindings -n astra-production

# Check service account permissions
kubectl auth can-i --list \
  --as=system:serviceaccount:astra-production:astra-core
```

### **6. Compliance Checks**

```bash
# OWASP ZAP scan
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t https://astra-core.prod \
  -r security-reports/zap-$(date +%Y%m%d).html

# CIS Kubernetes Benchmark
docker run --rm -v $(pwd):/host aquasec/kube-bench:latest \
  --config-dir /host/cfg --config /host/cfg/config.yaml

# PCI DSS compliance check (if applicable)
lynis audit system --quick \
  --report-file security-reports/lynis-$(date +%Y%m%d).log
```

---

## 🚨 Disaster Recovery

### **Recovery Time Objective (RTO)**
- **Critical**: 1 hour
- **High**: 4 hours
- **Medium**: 24 hours
- **Low**: 72 hours

### **Recovery Point Objective (RPO)**
- **Configuration**: 0 minutes (GitOps)
- **Application State**: 6 hours
- **Database**: 4 hours
- **Logs**: Real-time (streamed)

### **Disaster Recovery Procedures**

#### **Scenario 1: Pod Failure**

```bash
# Auto-recovery via Kubernetes
# No action needed - k8s will restart pods automatically

# Verify recovery
kubectl get pods -n astra-production -w
```

#### **Scenario 2: Node Failure**

```bash
# Kubernetes will reschedule pods to healthy nodes
kubectl get nodes
kubectl get pods -n astra-production -o wide

# Force drain node if stuck
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
```

#### **Scenario 3: Cluster Failure**

```bash
# Restore from backup to new cluster
# 1. Create new cluster
eksctl create cluster -f cluster-config.yaml

# 2. Restore namespaces
kubectl create namespace astra-production

# 3. Restore secrets
aws s3 cp s3://astra-backups/k8s/latest/secrets.yaml.gpg /tmp/
gpg --decrypt /tmp/secrets.yaml.gpg | kubectl apply -f -

# 4. Restore deployments
kubectl apply -f backups/k8s/latest/

# 5. Verify
kubectl get all -n astra-production
curl http://astra-core.prod/live
```

#### **Scenario 4: Data Corruption**

```bash
# Restore from latest good backup
# 1. Identify last known good backup
aws s3 ls s3://astra-backups/data/ | grep "2025-11-01"

# 2. Download backup
aws s3 cp s3://astra-backups/data/astra-data-20251101-120000.tar.gz /tmp/

# 3. Restore to pods
kubectl cp /tmp/astra-data-20251101-120000.tar.gz \
  astra-production/astra-core-pod:/tmp/

kubectl exec -n astra-production deployment/astra-core -- \
  tar xzf /tmp/astra-data-20251101-120000.tar.gz -C /app/data

# 4. Verify data integrity
kubectl exec -n astra-production deployment/astra-core -- \
  /app/verify-data.sh
```

#### **Scenario 5: Region Outage**

```bash
# Failover to secondary region
# 1. Update DNS to point to DR cluster
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456 \
  --change-batch file://dns-failover.json

# 2. Verify DR cluster is healthy
kubectl --context=dr-cluster get pods -n astra-production

# 3. Monitor traffic shift
watch 'curl -s https://astra-core.prod/live | jq .region'

# 4. Post-incident: Sync data from DR back to primary
```

---

## ✅ Compliance Checklist

### **SOC 2 Type II**
- [ ] Access controls implemented and audited
- [ ] Encryption at rest and in transit
- [ ] Change management process documented
- [ ] Backup and recovery tested quarterly
- [ ] Security monitoring and alerting active
- [ ] Incident response plan documented
- [ ] Vendor risk assessment completed

### **ISO 27001**
- [ ] Information security policy published
- [ ] Risk assessment completed annually
- [ ] Asset inventory maintained
- [ ] Security training completed by team
- [ ] Business continuity plan tested
- [ ] Cryptographic controls implemented
- [ ] Physical security measures in place

### **GDPR**
- [ ] Data processing agreement signed
- [ ] Privacy by design implemented
- [ ] Data retention policy enforced
- [ ] Right to erasure implemented
- [ ] Data breach notification process (<72 hours)
- [ ] Data protection impact assessment completed
- [ ] DPO appointed and contact available

### **PCI DSS** (if applicable)
- [ ] Cardholder data encrypted
- [ ] Network segmentation implemented
- [ ] Access control lists maintained
- [ ] Vulnerability scans quarterly
- [ ] Penetration tests annually
- [ ] Security awareness training
- [ ] Audit logs retained for 1 year

---

## 🚨 Security Incident Response

### **Severity Levels**

| Severity | Description | Response Time |
|----------|-------------|---------------|
| **P0 - Critical** | Production outage, data breach | < 15 minutes |
| **P1 - High** | Major functionality impaired | < 1 hour |
| **P2 - Medium** | Minor functionality impaired | < 4 hours |
| **P3 - Low** | Cosmetic issue, documentation | < 24 hours |

### **Incident Response Playbook**

#### **Step 1: Detection**

```bash
# Automated detection via monitoring
# Manual detection via user report

# Gather initial information
kubectl logs -n astra-production -l app=astra-core --tail=100
python tools/check_metrics.py http://astra-core.prod
curl http://astra-core.prod/health/full
```

#### **Step 2: Containment**

```bash
# Isolate affected components
kubectl scale deployment astra-core --replicas=0 -n astra-production

# Block malicious traffic
kubectl apply -f k8s/security/network-policy-lockdown.yaml

# Enable rate limiting
kubectl patch deployment astra-core -n astra-production \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"astra-core","env":[{"name":"RATE_LIMIT","value":"10"}]}]}}}}'
```

#### **Step 3: Investigation**

```bash
# Collect forensic data
kubectl get events -n astra-production --sort-by='.lastTimestamp' > incident-events.log
kubectl logs -n astra-production -l app=astra-core --previous > incident-logs.log

# Analyze network traffic
kubectl exec -n astra-production deployment/astra-core -- tcpdump -w /tmp/capture.pcap

# Check for compromise indicators
kubectl exec -n astra-production deployment/astra-core -- \
  find /app -type f -mtime -1
```

#### **Step 4: Eradication**

```bash
# Remove malicious code/data
kubectl exec -n astra-production deployment/astra-core -- \
  rm -rf /app/compromised-files/

# Patch vulnerabilities
kubectl set image deployment/astra-core \
  astra-core=astra-core:v1.1.1-security-patch \
  -n astra-production

# Rotate compromised secrets
kubectl delete secret astra-api-key -n astra-production
kubectl create secret generic astra-api-key \
  --from-literal=key=<new-secure-key> \
  -n astra-production
```

#### **Step 5: Recovery**

```bash
# Restore from clean backup
kubectl apply -f backups/k8s/last-known-good/

# Scale back up
kubectl scale deployment astra-core --replicas=3 -n astra-production

# Verify clean state
python tools/validate_production.py
```

#### **Step 6: Post-Incident**

- [ ] Write post-mortem within 48 hours
- [ ] Identify root cause
- [ ] Document lessons learned
- [ ] Update runbooks/procedures
- [ ] Implement preventive measures
- [ ] Notify affected parties (if required)
- [ ] File regulatory reports (if required)

---

## 📊 Security Metrics

### **KPIs to Track**
- Mean Time to Detect (MTTD): < 15 minutes
- Mean Time to Respond (MTTR): < 1 hour
- Mean Time to Recover (MTTR): < 4 hours
- Vulnerability Remediation SLA: 30 days (medium), 7 days (high), 24 hours (critical)
- Backup Success Rate: > 99.9%
- Restore Test Success Rate: 100%

---

## 📚 References

- NIST Cybersecurity Framework: https://www.nist.gov/cyberframework
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- CIS Kubernetes Benchmark: https://www.cisecurity.org/benchmark/kubernetes
- Kubernetes Security Best Practices: https://kubernetes.io/docs/concepts/security/

---

**Last Updated**: 2025-11-01  
**Next Review**: 2026-02-01  
**Owner**: Security & DevOps Teams
