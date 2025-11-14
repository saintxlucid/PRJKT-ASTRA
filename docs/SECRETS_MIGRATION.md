# Vault Migration Plan (Draft)

## Goal
Migrate all plaintext / env-based secrets to HashiCorp Vault and update deployment manifests to use Vault Agent or CSI driver.

## Current State
- Secrets currently stored in: `.env` files, environment variables, Kubernetes secrets YAML
- Risk: Plaintext secrets in git history, accidental exposure in logs
- Target: All secrets in Vault with automatic rotation

## Phase 1 Sprint 3 Plan (Week 3)

### Step 1: Inventory Current Secrets (1 hour)

**Command to find secrets:**
```bash
git grep -i "SECRET\|_KEY\|PASSWORD\|TOKEN\|API_KEY" | grep -v node_modules | grep -v ".git" | head -50
```

**Expected findings:**
- Database connection strings
- API keys (OpenAI, external services)
- JWT signing keys
- OAuth credentials
- Encryption keys

**Output file:** `docs/secrets-inventory.txt` (to be created in secure location, NOT committed to git)

### Step 2: Set Up Vault Infrastructure (4 hours)

**Prerequisites:**
- HashiCorp Vault 1.15+ running (Docker or native)
- `vault` CLI installed locally
- Network access to Vault server

**Commands:**
```bash
# Start Vault (Docker example)
docker run -d \
  -p 8200:8200 \
  -e VAULT_DEV_ROOT_TOKEN_ID="myroot" \
  vault:latest server -dev

# Authenticate
export VAULT_ADDR="http://localhost:8200"
export VAULT_TOKEN="myroot"
vault status

# Create KV v2 secret engine
vault secrets enable -version=2 -path=secret kv

# Create app-specific policy
vault policy write astra-policy - <<EOF
path "secret/data/astra/*" {
  capabilities = ["read", "list"]
}
path "secret/metadata/astra/*" {
  capabilities = ["list"]
}
EOF

# Create app role for CI/CD
vault auth enable approle
vault write auth/approle/role/astra \
  token_ttl=1h \
  token_max_ttl=4h \
  policies="astra-policy"
```

### Step 3: Migrate Secrets to Vault (6 hours)

**Create secrets:**
```bash
# Database credentials
vault kv put secret/astra/database \
  host="postgres.default.svc.cluster.local" \
  port="5432" \
  username="astra_user" \
  password="$(openssl rand -base64 32)" \
  database="astra_prod"

# API keys
vault kv put secret/astra/api-keys \
  openai_key="sk-..." \
  anthropic_key="sk-ant-..." \
  huggingface_token="hf_..."

# Encryption keys
vault kv put secret/astra/encryption \
  jwt_secret="$(openssl rand -hex 32)" \
  db_cipher_key="$(openssl rand -hex 32)"
```

**Verify:**
```bash
vault kv list secret/astra
vault kv get secret/astra/database
```

### Step 4: Integrate with Kubernetes (5 hours)

**Option A: Vault Agent Sidecar (Recommended for this phase)**

Example Kubernetes deployment manifest update:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: astra
spec:
  template:
    metadata:
      annotations:
        vault.hashicorp.com/agent-inject: "true"
        vault.hashicorp.com/role: "astra"
        vault.hashicorp.com/agent-inject-secret-db: "secret/data/astra/database"
        vault.hashicorp.com/agent-inject-template-db: |
          {{- with secret "secret/data/astra/database" -}}
          export DB_HOST="{{ .data.data.host }}"
          export DB_PORT="{{ .data.data.port }}"
          export DB_USER="{{ .data.data.username }}"
          export DB_PASSWORD="{{ .data.data.password }}"
          export DB_NAME="{{ .data.data.database }}"
          {{- end }}
    spec:
      serviceAccountName: astra
      containers:
      - name: astra-container
        image: astra:latest
        command: ["/bin/sh"]
        args: ["-c", "source /vault/secrets/db && exec python -m uvicorn main:app --host 0.0.0.0"]
        ports:
        - containerPort: 8000
```

**Install Vault Agent Injector:**
```bash
helm repo add hashicorp https://helm.releases.hashicorp.com
helm install vault hashicorp/vault \
  --set injector.enabled=true \
  --set server.enabled=false
```

**Option B: CSI Driver (Kubernetes 1.16+)**

```bash
helm install vault-csi hashicorp/vault-csi-provider
```

### Step 5: Testing & Validation (2 hours)

**Test on staging:**
```bash
# Deploy updated manifests to staging
kubectl apply -f k8s/deployment-vault.yaml -n staging

# Verify pod came up
kubectl get pods -n staging
kubectl logs -n staging -l app=astra | grep -i vault

# Verify secrets are NOT in environment (in plain text)
kubectl exec -it deployment/astra -n staging -- sh
# Inside pod: env | grep DB_ (should show secrets from Vault, not plain env vars)
# Inside pod: env | grep -c VAULT (should see vault paths being used)
```

### Step 6: Documentation & Runbooks (2 hours)

**Create runbooks:**
- `docs/VAULT_OPERATIONS.md` — Daily ops, secret rotation, emergency access
- `docs/VAULT_DISASTER_RECOVERY.md` — Vault failure scenarios, recovery procedures
- `docs/VAULT_TROUBLESHOOTING.md` — Common issues and solutions

**Key runbook sections:**
1. How to add a new secret (for on-call)
2. How to rotate API keys
3. How to recover if Vault is down
4. Audit log review procedures

## Acceptance Criteria

- ✅ All secrets stored in Vault paths (`secret/astra/*`)
- ✅ No plaintext secrets in `.env` files, YAML manifests, or git history
- ✅ Kubernetes deployment uses Vault Agent Sidecar (or CSI)
- ✅ All pods successfully inject secrets at startup
- ✅ Bandit/security scan shows no exposed API keys
- ✅ Rollback procedure documented and tested
- ✅ On-call runbooks created and tested
- ✅ CI/CD pipeline authenticated via AppRole

## Rollback Plan

If issues occur:
1. Revert Kubernetes manifests to use ConfigMaps/Secrets
2. Halt new secret reads from Vault
3. Investigate logs: `vault audit list` and `kubectl logs vault-*`
4. Document incident and root cause
5. Reschedule migration with fixes applied

## Timeline

**Sprint 3 (Week 3):** 15 hours total
- Step 1: Inventory (1h)
- Step 2: Vault setup (4h)
- Step 3: Migrate secrets (6h)
- Step 4: K8s integration (5h) — **runs in parallel with 2-3**
- Step 5: Testing (2h)
- Step 6: Docs & runbooks (2h)

## Success Metrics

| Metric | Target | Validation |
|--------|--------|-----------|
| Secrets in Vault | 100% | `vault kv list secret/astra \| wc -l` |
| Plaintext secrets in git | 0 | `git grep -i SECRET \| wc -l` = 0 |
| Pod startup time | <5s | `kubectl logs astra-* \| grep "Vault agent ready"` |
| Rotation window | 90-day key rotation | Cron job for `vault kv put` updates |
| Audit logging | 100% reads logged | `vault audit list` enabled |

## Contacts & Escalation

- **Vault Admin:** @security-eng
- **Kubernetes Admin:** @devops-eng
- **On-Call Rotation:** Check PagerDuty for escalations
- **Emergency Access:** See VAULT_DISASTER_RECOVERY.md

---

**Next:** After this migration is complete, Phase 1 Sprint 4 will validate all security improvements.
