#!/usr/bin/env bash
# ASTRA Live Status Snapshot
# Queries Prometheus for current health metrics

set -euo pipefail

PROM_URL="${PROM_URL:-http://prometheus.monitoring:9090}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Helper to query Prometheus
q() {
    local query="$1"
    curl -sG --data-urlencode "query=$query" "$PROM_URL/api/v1/query" 2>/dev/null | \
        jq -r '.data.result[0].value[1] // "N/A"'
}

# Helper for colored output
print_metric() {
    local label="$1"
    local value="$2"
    local unit="$3"
    local threshold="$4"
    local operator="$5"  # "lt" or "gt"
    
    # Color based on threshold
    local color="$NC"
    if [ "$value" != "N/A" ] && [ -n "$threshold" ]; then
        if [ "$operator" = "lt" ]; then
            # Good if less than threshold
            if awk "BEGIN{exit !($value < $threshold)}"; then
                color="$GREEN"
            else
                color="$RED"
            fi
        else
            # Good if greater than threshold
            if awk "BEGIN{exit !($value > $threshold)}"; then
                color="$GREEN"
            else
                color="$RED"
            fi
        fi
    fi
    
    printf "%-30s ${color}%8.4f${NC} %s\n" "$label:" "$value" "$unit"
}

# Banner
echo ""
echo -e "${BOLD}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   ASTRA Live Status Snapshot                          ║${NC}"
echo -e "${BOLD}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Prometheus: $PROM_URL${NC}"
echo -e "${CYAN}Timestamp:  $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo ""

# Bridge Metrics
echo -e "${BOLD}━━━ BRIDGE SERVICE ━━━${NC}"

ERR_RATE=$(q 'sum(rate(bridge_calls_total{status="error"}[5m])) / clamp_min(sum(rate(bridge_calls_total[5m])),1) * 100')
P95=$(q 'histogram_quantile(0.95, sum by (le) (rate(bridge_call_duration_seconds_bucket[5m])))')
P99=$(q 'histogram_quantile(0.99, sum by (le) (rate(bridge_call_duration_seconds_bucket[5m])))')
CALLS=$(q 'sum(rate(bridge_calls_total[1m]))')
SUCCESS_RATE=$(q 'sum(rate(bridge_calls_total{status="success"}[5m])) / clamp_min(sum(rate(bridge_calls_total[5m])),1) * 100')

print_metric "Error Rate" "$ERR_RATE" "%" "1" "lt"
print_metric "Success Rate" "$SUCCESS_RATE" "%" "99" "gt"
print_metric "P95 Latency" "$P95" "s" "1" "lt"
print_metric "P99 Latency" "$P99" "s" "2" "lt"
print_metric "Request Rate" "$CALLS" "req/s" "" ""

# Docs Metrics
echo ""
echo -e "${BOLD}━━━ DOCS SERVICE ━━━${NC}"

INGEST=$(q 'sum(rate(docs_ingest_total[1m]))')
SEARCH_RPM=$(q 'sum(rate(docs_search_total[1m])) * 60')
SEARCH_P95=$(q 'histogram_quantile(0.95, sum by (le) (rate(docs_search_duration_seconds_bucket[5m])))')
INGEST_FAIL=$(q 'sum(rate(docs_ingest_total{status="error"}[5m])) / clamp_min(sum(rate(docs_ingest_total[5m])),1) * 100')

print_metric "Ingest Rate" "$INGEST" "doc/s" "" ""
print_metric "Ingest Failure Rate" "$INGEST_FAIL" "%" "5" "lt"
print_metric "Search Rate" "$SEARCH_RPM" "search/min" "" ""
print_metric "Search P95 Latency" "$SEARCH_P95" "s" "2" "lt"

# Qdrant Metrics
echo ""
echo -e "${BOLD}━━━ QDRANT ━━━${NC}"

QDRANT_UP=$(q 'up{job="qdrant"}')
QDRANT_MEM=$(q 'qdrant_memory_used_bytes / qdrant_memory_total_bytes * 100')

if [ "$QDRANT_UP" = "1" ]; then
    printf "%-30s ${GREEN}%8s${NC}\n" "Status:" "UP"
else
    printf "%-30s ${RED}%8s${NC}\n" "Status:" "DOWN"
fi

if [ "$QDRANT_MEM" != "N/A" ]; then
    print_metric "Memory Usage" "$QDRANT_MEM" "%" "85" "lt"
fi

# Pod Health
echo ""
echo -e "${BOLD}━━━ POD HEALTH ━━━${NC}"

BRIDGE_PODS=$(q 'count(kube_pod_info{namespace="astra", pod=~"bridge-.*"})')
DOCS_PODS=$(q 'count(kube_pod_info{namespace="astra", pod=~"docs-.*"})')
QDRANT_PODS=$(q 'count(kube_pod_info{namespace="astra", pod=~"qdrant-.*"})')
RESTARTS=$(q 'sum(increase(kube_pod_container_status_restarts_total{namespace="astra"}[1h]))')

printf "%-30s %8.0f\n" "Bridge Pods:" "$BRIDGE_PODS"
printf "%-30s %8.0f\n" "Docs Pods:" "$DOCS_PODS"
printf "%-30s %8.0f\n" "Qdrant Pods:" "$QDRANT_PODS"

if [ "$RESTARTS" != "N/A" ] && awk "BEGIN{exit !($RESTARTS > 0)}"; then
    printf "%-30s ${RED}%8.0f${NC} (last 1h)\n" "Pod Restarts:" "$RESTARTS"
else
    printf "%-30s ${GREEN}%8.0f${NC} (last 1h)\n" "Pod Restarts:" "${RESTARTS:-0}"
fi

# Storage
echo ""
echo -e "${BOLD}━━━ STORAGE ━━━${NC}"

DISK_USAGE=$(q '1 - (node_filesystem_avail_bytes{mountpoint="/data"} / node_filesystem_size_bytes{mountpoint="/data"})')
DISK_PERCENT=$(awk "BEGIN{print $DISK_USAGE * 100}")

if [ "$DISK_USAGE" != "N/A" ]; then
    print_metric "PV /data Usage" "$DISK_PERCENT" "%" "85" "lt"
fi

# SLO Metrics
echo ""
echo -e "${BOLD}━━━ SLO TRACKING ━━━${NC}"

AVAIL_1H=$(q 'bridge:availability:1h * 100')
AVAIL_24H=$(q 'bridge:availability:24h * 100')
BUDGET_REMAIN=$(q 'bridge:error_budget_remaining:30d * 100')

if [ "$AVAIL_1H" != "N/A" ]; then
    print_metric "Availability (1h)" "$AVAIL_1H" "%" "99.5" "gt"
fi

if [ "$AVAIL_24H" != "N/A" ]; then
    print_metric "Availability (24h)" "$AVAIL_24H" "%" "99.5" "gt"
fi

if [ "$BUDGET_REMAIN" != "N/A" ]; then
    print_metric "Error Budget Remaining" "$BUDGET_REMAIN" "%" "20" "gt"
fi

# Active Alerts
echo ""
echo -e "${BOLD}━━━ ACTIVE ALERTS ━━━${NC}"

FIRING_ALERTS=$(curl -sG "$PROM_URL/api/v1/alerts" 2>/dev/null | \
    jq -r '[.data.alerts[] | select(.state=="firing")] | length')

if [ "$FIRING_ALERTS" = "0" ]; then
    echo -e "${GREEN}✅ No active alerts${NC}"
else
    echo -e "${RED}⚠️  $FIRING_ALERTS alerts firing${NC}"
    
    # List critical alerts
    curl -sG "$PROM_URL/api/v1/alerts" 2>/dev/null | \
        jq -r '.data.alerts[] | select(.state=="firing") | "  - \(.labels.alertname): \(.annotations.summary)"' | \
        head -n 5
fi

# Summary
echo ""
echo -e "${BOLD}━━━ HEALTH SUMMARY ━━━${NC}"

HEALTH_OK=true

# Check thresholds
[ "$ERR_RATE" != "N/A" ] && awk "BEGIN{exit !($ERR_RATE > 1)}" && HEALTH_OK=false
[ "$P95" != "N/A" ] && awk "BEGIN{exit !($P95 > 1)}" && HEALTH_OK=false
[ "$QDRANT_UP" != "1" ] && HEALTH_OK=false
[ "$FIRING_ALERTS" != "0" ] && HEALTH_OK=false
[ "$RESTARTS" != "N/A" ] && awk "BEGIN{exit !($RESTARTS > 0)}" && HEALTH_OK=false

if [ "$HEALTH_OK" = true ]; then
    echo -e "${GREEN}✅ ALL SYSTEMS OPERATIONAL${NC}"
else
    echo -e "${RED}⚠️  ISSUES DETECTED - INVESTIGATE${NC}"
fi

echo ""
echo -e "${CYAN}Next check: watch -n 5 ./scripts/cutover_status.sh${NC}"
echo ""
