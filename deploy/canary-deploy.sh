#!/usr/bin/env bash
# CANARY DEPLOY SCRIPT — ASTRA (staging)
# Usage: ./deploy/canary-deploy.sh <image-tag> <namespace>
# Example: ./deploy/canary-deploy.sh astra-20251114-abc123 staging

set -euo pipefail

IMAGE_TAG=${1:-"astra:latest"}
NAMESPACE=${2:-"staging"}
DEPLOYMENT_NAME="astra"
K8S_CONTEXT=${K8S_CONTEXT:-""}   # export K8S_CONTEXT if you use multiple clusters
CANARY_PERCENT=5                 # start = 5%
WAIT_SECONDS=60                  # monitor window per stage

echo "→ Deploying ASTRA canary: $IMAGE_TAG to namespace: $NAMESPACE"

# 0. Optional: select context
if [[ -n "$K8S_CONTEXT" ]]; then
  kubectl config use-context "$K8S_CONTEXT"
fi

# 1. Create pre-deploy snapshot (DB / config) - adjust commands to your infra
echo "→ Creating DB snapshot (dry-run placeholder)"
# ./scripts/db_snapshot.sh --target $NAMESPACE || true

# 2. Patch deployment image for canary (use label to route 5% traffic via service mesh or ingress)
# If using feature flags or service mesh: set canary label
kubectl -n "$NAMESPACE" set image deployment/"$DEPLOYMENT_NAME" astra-container="$IMAGE_TAG" --record

# 3. Mark deployment as canary via label
kubectl -n "$NAMESPACE" label deployment/"$DEPLOYMENT_NAME" astra-canary=true --overwrite

echo "→ Waiting $WAIT_SECONDS seconds for initial health check..."
sleep $WAIT_SECONDS

# 4. Health checks
echo "→ Checking rollout status"
kubectl -n "$NAMESPACE" rollout status deployment/"$DEPLOYMENT_NAME" --watch=true --timeout=120s

# 5. Monitor metrics for short window (Prometheus/Grafana pre-configured)
echo "→ Monitor: Prometheus / Grafana (open dashboards). Waiting additional 60s."
sleep 60

# 6. Ramp traffic (if using feature flags or ingress routing; example: Istio VirtualService patch)
# NOTE: Replace with your mesh/ingress traffic-shift API. Here is a placeholder for a manual ramp.
for P in 5 25 50 100; do
  echo "→ Ramp to ${P}% — manual step; update feature-flag or ingress accordingly."
  # Example: kubectl apply -f k8s/virtualservice-canary-${P}.yaml
  echo "Sleeping 60s for stabilization..."
  sleep 60
done

echo "→ Canary deployment completed. Validate monitors and logs:"
echo "  - kubectl -n $NAMESPACE get pods -l app=$DEPLOYMENT_NAME"
echo "  - kubectl -n $NAMESPACE logs -l app=$DEPLOYMENT_NAME --tail=200"
echo ""
echo "If anything fails, run rollback:"
echo "  ./deploy/canary-rollback.sh $NAMESPACE"

exit 0
