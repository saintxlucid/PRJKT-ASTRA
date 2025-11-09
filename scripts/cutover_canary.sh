#!/usr/bin/env bash
# ASTRA Blue/Green Canary Cutover Script
# Safely switches traffic from blue to green with automated health checks

set -euo pipefail

# Configuration
NS="${NS:-astra}"
DEP_BLUE="${DEP_BLUE:-bridge}"
DEP_GREEN="${DEP_GREEN:-bridge-green}"
SVC="${SVC:-bridge}"
HEALTH_PATH="${HEALTH_PATH:-/health}"
PORT="${PORT:-8888}"             # containerPort on pods
SVC_PORT="${SVC_PORT:-80}"       # service port
PROM_URL="${PROM_URL:-}"         # optional: http(s)://prometheus:9090
ERROR_THRESH="${ERROR_THRESH:-0.01}" # 1% error rate threshold
LATENCY_THRESH="${LATENCY_THRESH:-1}" # 1s P95 latency threshold
CANARY_DURATION="${CANARY_DURATION:-60}" # seconds to monitor post-switch

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

die() {
    echo -e "${RED}❌ ERROR: $*${NC}" >&2
    exit 1
}

log() {
    echo -e "${CYAN}▶ $*${NC}"
}

success() {
    echo -e "${GREEN}✅ $*${NC}"
}

warn() {
    echo -e "${YELLOW}⚠️  $*${NC}"
}

# Banner
echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   ASTRA Blue/Green Canary Cutover                     ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
log "Configuration:"
echo "  Namespace:        $NS"
echo "  Blue Deployment:  $DEP_BLUE"
echo "  Green Deployment: $DEP_GREEN"
echo "  Service:          $SVC"
echo "  Health Path:      $HEALTH_PATH"
echo "  Pod Port:         $PORT"
echo "  Prometheus URL:   ${PROM_URL:-[not configured]}"
echo ""

# 0) Prechecks
log "Step 0: Pre-flight checks"

kubectl get ns "$NS" >/dev/null || die "Namespace $NS not found"
success "Namespace $NS exists"

kubectl -n "$NS" get deploy "$DEP_BLUE" >/dev/null || die "Blue deployment $DEP_BLUE not found"
success "Blue deployment $DEP_BLUE found"

kubectl -n "$NS" get deploy "$DEP_GREEN" >/dev/null || die "Green deployment $DEP_GREEN not found"
success "Green deployment $DEP_GREEN found"

kubectl -n "$NS" get svc "$SVC" >/dev/null || die "Service $SVC not found"
success "Service $SVC found"

log "Checking green deployment readiness..."
if ! kubectl -n "$NS" rollout status deploy/"$DEP_GREEN" --timeout=60s; then
    die "Green deployment $DEP_GREEN not ready"
fi
success "Green deployment is ready"

# Get current service selector
CURRENT_SELECTOR=$(kubectl -n "$NS" get svc "$SVC" -o jsonpath='{.spec.selector.app}')
log "Current service selector: app=$CURRENT_SELECTOR"

if [ "$CURRENT_SELECTOR" = "$DEP_GREEN" ]; then
    warn "Service already points to green! Nothing to do."
    exit 0
fi

# 1) Health check green (port-forward first pod)
log "Step 1: Health check green deployment"

POD=$(kubectl -n "$NS" get pod -l app="$DEP_GREEN" -o jsonpath='{.items[0].metadata.name}')
[ -n "$POD" ] || die "No green pods found"
log "Green pod: $POD"

log "Setting up port-forward to green pod..."
kubectl -n "$NS" port-forward "pod/$POD" 0:$PORT >/tmp/pf.$$.log 2>&1 &
PF_PID=$!
trap 'kill $PF_PID 2>/dev/null || true; rm -f /tmp/pf.$$.log' EXIT

sleep 2

FWD_PORT=$(sed -n 's/.*127\.0\.0\.1:\([0-9]*\).*/\1/p' /tmp/pf.$$.log | tail -1)
[ -n "${FWD_PORT:-}" ] || die "Port-forward failed (check /tmp/pf.$$.log)"
log "Port-forwarded to localhost:$FWD_PORT"

log "Testing green health endpoint: http://127.0.0.1:$FWD_PORT$HEALTH_PATH"
if curl -fsS "http://127.0.0.1:$FWD_PORT$HEALTH_PATH" | jq . >/dev/null; then
    success "Green health check PASSED"
else
    die "Green health check FAILED"
fi

# 2) Optional: error-rate guard (production traffic on blue)
if [ -n "$PROM_URL" ]; then
    log "Step 2: Checking current blue error rate via Prometheus"
    
    Q='sum(rate(bridge_calls_total{status="error"}[5m])) / clamp_min(sum(rate(bridge_calls_total[5m])),1)'
    ER=$(curl -sG --data-urlencode "query=$Q" "$PROM_URL/api/v1/query" 2>/dev/null | jq -r '.data.result[0].value[1] // "0"' || echo "0")
    
    log "Current blue error rate: $(printf '%.4f' "$ER") ($(awk "BEGIN{print $ER * 100}")%)"
    
    if awk "BEGIN{exit !($ER < $ERROR_THRESH)}"; then
        success "Blue error rate is acceptable (< $ERROR_THRESH)"
    else
        die "Blue error rate too high ($ER >= $ERROR_THRESH), aborting cutover"
    fi
    
    # Check latency too
    Q_LAT='histogram_quantile(0.95, sum by (le) (rate(bridge_call_duration_seconds_bucket[5m])))'
    LAT=$(curl -sG --data-urlencode "query=$Q_LAT" "$PROM_URL/api/v1/query" 2>/dev/null | jq -r '.data.result[0].value[1] // "0"' || echo "0")
    
    log "Current blue P95 latency: ${LAT}s"
    
    if awk "BEGIN{exit !($LAT < $LATENCY_THRESH)}"; then
        success "Blue P95 latency is acceptable (< ${LATENCY_THRESH}s)"
    else
        warn "Blue P95 latency is high (${LAT}s), proceeding with caution"
    fi
else
    warn "Prometheus URL not set, skipping error rate check"
fi

# 3) Switch service selector to green
log "Step 3: Switching service selector to green"

echo ""
warn "About to switch traffic from $DEP_BLUE to $DEP_GREEN"
echo "Press Ctrl+C within 5 seconds to abort..."
sleep 5

log "Patching Service/$SVC to app=$DEP_GREEN"
kubectl -n "$NS" patch svc "$SVC" -p "{\"spec\":{\"selector\":{\"app\":\"$DEP_GREEN\"}}}" || die "Failed to patch service"

success "Service switched to green"

# Wait for endpoints to update
log "Waiting for service endpoints to update..."
sleep 3

# 4) Post-switch smoke (service endpoint via ClusterIP)
log "Step 4: Post-switch health check via service"

SVC_IP=$(kubectl -n "$NS" get svc "$SVC" -o jsonpath='{.spec.clusterIP}')
SVC_PORT_NUM=$(kubectl -n "$NS" get svc "$SVC" -o jsonpath='{.spec.ports[0].port}')
log "Service ClusterIP: $SVC_IP:$SVC_PORT_NUM"

# Use kubectl run to test from inside cluster
log "Testing service health from inside cluster..."
if kubectl run -n "$NS" health-check-$$ --rm -i --restart=Never --image=curlimages/curl:latest -- \
    curl -fsS "http://$SVC_IP:$SVC_PORT_NUM$HEALTH_PATH" 2>/dev/null | grep -q status; then
    success "Post-switch health check PASSED"
else
    log "❌ Post-switch health check FAILED - ROLLING BACK"
    kubectl -n "$NS" patch svc "$SVC" -p "{\"spec\":{\"selector\":{\"app\":\"$DEP_BLUE\"}}}"
    die "Rolled back to blue due to health check failure"
fi

# 5) Canary monitoring period
if [ -n "$PROM_URL" ]; then
    log "Step 5: Canary monitoring for ${CANARY_DURATION}s"
    
    START=$(date +%s)
    FAIL_COUNT=0
    
    while [ $(($(date +%s) - START)) -lt "$CANARY_DURATION" ]; do
        sleep 5
        
        # Check error rate
        Q='sum(rate(bridge_calls_total{status="error"}[1m])) / clamp_min(sum(rate(bridge_calls_total[1m])),1)'
        ER=$(curl -sG --data-urlencode "query=$Q" "$PROM_URL/api/v1/query" 2>/dev/null | jq -r '.data.result[0].value[1] // "0"' || echo "0")
        
        ELAPSED=$(($(date +%s) - START))
        REMAINING=$((CANARY_DURATION - ELAPSED))
        
        if awk "BEGIN{exit !($ER > $ERROR_THRESH)}"; then
            FAIL_COUNT=$((FAIL_COUNT + 1))
            warn "Error rate spike detected: $(awk "BEGIN{print $ER * 100}")% (threshold: $(awk "BEGIN{print $ERROR_THRESH * 100}")%)"
            
            if [ $FAIL_COUNT -ge 3 ]; then
                log "❌ Error rate consistently high - ROLLING BACK"
                kubectl -n "$NS" patch svc "$SVC" -p "{\"spec\":{\"selector\":{\"app\":\"$DEP_BLUE\"}}}"
                die "Rolled back to blue due to high error rate"
            fi
        else
            FAIL_COUNT=0
            log "Monitoring: ${ELAPSED}s elapsed, ${REMAINING}s remaining (error rate: $(awk "BEGIN{printf \"%.4f\", $ER}"))"
        fi
    done
    
    success "Canary monitoring complete - metrics stable"
else
    warn "Prometheus URL not set, skipping canary monitoring"
fi

# 6) Success
echo ""
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   ✅ CUTOVER COMPLETE                                  ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""
success "Traffic switched from $DEP_BLUE to $DEP_GREEN"
log "Next steps:"
echo "  1. Monitor Grafana dashboard for 30+ minutes"
echo "  2. Run smoke tests: ./scripts/smoke_tests_production.ps1"
echo "  3. Scale down blue deployment: kubectl -n $NS scale deploy/$DEP_BLUE --replicas=0"
echo "  4. After 1 hour, delete blue: kubectl -n $NS delete deploy/$DEP_BLUE"
echo ""
log "Rollback command (if needed):"
echo "  kubectl -n $NS patch svc $SVC -p '{\"spec\":{\"selector\":{\"app\":\"$DEP_BLUE\"}}}'"
echo ""
