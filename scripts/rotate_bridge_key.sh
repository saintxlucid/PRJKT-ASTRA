#!/usr/bin/env bash
# ASTRA Bridge Key Rotation Script
# Rotates API keys and updates Kubernetes secret + reloads bridge

set -euo pipefail

NAMESPACE=${NAMESPACE:-astra}
ADMIN_KEY=${ADMIN_KEY:-}
BRIDGE_URL=${BRIDGE_URL:-https://bridge.example.com}

echo "========================================"
echo "ASTRA Bridge Key Rotation"
echo "========================================"
echo "Namespace: $NAMESPACE"
echo "Bridge URL: $BRIDGE_URL"
echo ""

if [ -z "$ADMIN_KEY" ]; then
    echo "[ERROR] ADMIN_KEY environment variable not set"
    echo "Usage: ADMIN_KEY=xxx ./rotate_bridge_key.sh"
    exit 1
fi

# Generate new keys
echo "[1/5] Generating new keys..."
NEW_ADMIN_KEY=$(openssl rand -hex 32)
NEW_AGENT_KEY=$(openssl rand -hex 32)

echo "  New Admin Key: ${NEW_ADMIN_KEY:0:16}..."
echo "  New Agent Key: ${NEW_AGENT_KEY:0:16}..."

# Create new keys JSON
echo ""
echo "[2/5] Creating keys file..."
cat > bridge_keys_new.json <<EOF
{
  "${NEW_ADMIN_KEY}": {
    "name": "Admin Key (rotated $(date +%Y-%m-%d))",
    "scopes": ["bridge:admin", "bridge:call", "docs:ingest", "docs:search"],
    "rpm": 120,
    "daily": 10000
  },
  "${NEW_AGENT_KEY}": {
    "name": "Agent Key (rotated $(date +%Y-%m-%d))",
    "scopes": ["bridge:call", "docs:search"],
    "rpm": 60,
    "daily": 5000
  }
}
EOF

echo "  Keys file created: bridge_keys_new.json"

# Backup old keys
echo ""
echo "[3/5] Backing up old keys..."
kubectl -n "$NAMESPACE" get secret bridge-keys -o jsonpath='{.data.bridge_keys}' | base64 -d > bridge_keys_backup.json 2>/dev/null || echo "  No existing keys to backup"

# Update K8s secret
echo ""
echo "[4/5] Updating Kubernetes secret..."
kubectl -n "$NAMESPACE" create secret generic bridge-keys \
  --from-file=bridge_keys=bridge_keys_new.json \
  --dry-run=client -o yaml | kubectl apply -f -

echo "  Secret updated successfully"

# Trigger reload on bridge admin endpoint
echo ""
echo "[5/5] Triggering key reload on bridge..."
RELOAD_RESPONSE=$(curl -sS -X POST -H "x-api-key: ${ADMIN_KEY}" "${BRIDGE_URL}/admin/reload-keys" -w "\nHTTP_CODE:%{http_code}" || echo "FAILED")

HTTP_CODE=$(echo "$RELOAD_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)

if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ Keys reloaded successfully"
else
    echo "  ⚠️  Reload failed or not available (HTTP $HTTP_CODE)"
    echo "  Bridge pods will pick up new keys on next restart"
    echo "  Consider: kubectl -n $NAMESPACE rollout restart deployment/bridge"
fi

echo ""
echo "========================================"
echo "✅ Key Rotation Complete"
echo "========================================"
echo ""
echo "📋 NEW CREDENTIALS:"
echo "-------------------"
echo "Admin Key: $NEW_ADMIN_KEY"
echo "Agent Key: $NEW_AGENT_KEY"
echo ""
echo "🔐 BACKUP:"
echo "----------"
echo "Old keys backed up to: bridge_keys_backup.json"
echo "New keys saved to: bridge_keys_new.json"
echo ""
echo "⚠️  IMPORTANT:"
echo "-------------"
echo "1. Update your environment variables:"
echo "   export ADMIN_KEY=\"$NEW_ADMIN_KEY\""
echo "   export AGENT_KEY=\"$NEW_AGENT_KEY\""
echo ""
echo "2. Distribute new AGENT_KEY to clients securely"
echo ""
echo "3. Keep old keys active for 24h grace period, then remove from keys file"
echo ""
echo "4. Store these keys in your password manager!"
echo ""
