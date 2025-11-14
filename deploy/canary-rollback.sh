#!/usr/bin/env bash
# CANARY ROLLBACK — ASTRA
# Usage: ./deploy/canary-rollback.sh <namespace>
set -euo pipefail
NAMESPACE=${1:-"staging"}
DEPLOYMENT_NAME="astra"

echo "→ Rolling back deployment $DEPLOYMENT_NAME in namespace $NAMESPACE"
kubectl -n "$NAMESPACE" rollout undo deployment/"$DEPLOYMENT_NAME"
kubectl -n "$NAMESPACE" label deployment/"$DEPLOYMENT_NAME" astra-canary-previous=true --overwrite || true
echo "→ Rollback triggered. Verify pods and logs:"
kubectl -n "$NAMESPACE" get pods -l app=$DEPLOYMENT_NAME
kubectl -n "$NAMESPACE" logs -l app=$DEPLOYMENT_NAME --tail=200
echo "→ Notify stakeholders and open an incident ticket if needed."
