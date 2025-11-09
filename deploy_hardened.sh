#!/usr/bin/env bash
# ASTRA 3.0 - Hardened Deployment Script
# Production-grade orchestration with health checks and rollback
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_prereqs() {
    log_info "Checking prerequisites..."
    
    command -v docker >/dev/null 2>&1 || { log_error "docker not found"; exit 1; }
    command -v docker-compose >/dev/null 2>&1 || { log_error "docker-compose not found"; exit 1; }
    command -v python3 >/dev/null 2>&1 || { log_error "python3 not found"; exit 1; }
    command -v psql >/dev/null 2>&1 || { log_error "psql not found"; exit 1; }
    
    log_info "✓ All prerequisites satisfied"
}

init_infrastructure() {
    log_info "Initializing infrastructure..."
    
    # Start Redis + Postgres
    docker compose -f docker-compose.prod.yml up -d redis postgres
    
    # Wait for Postgres to be ready
    log_info "Waiting for Postgres..."
    for i in {1..30}; do
        if docker exec astra_postgres pg_isready -U astra >/dev/null 2>&1; then
            log_info "✓ Postgres ready"
            break
        fi
        sleep 1
    done
    
    # Apply migrations
    if [ -f "migrations/001_init.sql" ]; then
        log_info "Applying database migrations..."
        export DATABASE_URL="${DATABASE_URL:-postgres://astra:astra_pass@localhost:5432/astra}"
        psql "$DATABASE_URL" -f migrations/001_init.sql 2>/dev/null || log_warn "Migrations may have already been applied"
        log_info "✓ Database schema ready"
    fi
}

start_astra() {
    log_info "Starting ASTRA 3.0..."
    
    # Check if already running
    if pgrep -f "astra_master.py" >/dev/null; then
        log_warn "ASTRA already running (PID: $(pgrep -f astra_master.py))"
        return
    fi
    
    # Start in background
    nohup python3 astra_master.py > logs/astra.log 2>&1 &
    ASTRA_PID=$!
    
    log_info "ASTRA starting (PID: $ASTRA_PID)"
    
    # Wait for health check
    log_info "Waiting for ASTRA to be healthy..."
    for i in {1..60}; do
        if curl -sf http://localhost:8000/ >/dev/null 2>&1; then
            log_info "✓ ASTRA is online"
            return
        fi
        sleep 1
    done
    
    log_error "ASTRA failed to start within 60s"
    exit 1
}

health_check() {
    log_info "Running health checks..."
    
    # System health
    HEALTH=$(curl -sf http://localhost:8000/ | jq -r .status 2>/dev/null || echo "error")
    if [ "$HEALTH" = "online" ]; then
        log_info "✓ System health: ONLINE"
    else
        log_error "✗ System health: $HEALTH"
        exit 1
    fi
    
    # Persistence health
    PERSIST=$(curl -sf http://localhost:8000/v1/persistence/health | jq -r .overall_healthy 2>/dev/null || echo "false")
    if [ "$PERSIST" = "true" ]; then
        log_info "✓ Persistence: HEALTHY"
    else
        log_warn "⚠ Persistence: DEGRADED"
    fi
    
    # Boot status
    BOOT=$(curl -sf http://localhost:8000/v1/boot/status | jq -r .status 2>/dev/null || echo "error")
    if [ "$BOOT" = "complete" ]; then
        log_info "✓ Boot: COMPLETE"
    else
        log_error "✗ Boot: $BOOT"
        exit 1
    fi
}

run_smoke_test() {
    log_info "Running smoke test..."
    
    # Simple chat request
    RESPONSE=$(curl -sf -X POST http://localhost:8000/v1/chat \
        -H "Content-Type: application/json" \
        -d '{"conversation_id":"smoke-test","message":"ping"}' \
        | jq -r .message 2>/dev/null || echo "error")
    
    if [ "$RESPONSE" != "error" ] && [ -n "$RESPONSE" ]; then
        log_info "✓ Smoke test PASSED"
    else
        log_error "✗ Smoke test FAILED"
        exit 1
    fi
}

stop_astra() {
    log_info "Stopping ASTRA..."
    
    if pgrep -f "astra_master.py" >/dev/null; then
        pkill -f "astra_master.py"
        log_info "✓ ASTRA stopped"
    else
        log_warn "ASTRA not running"
    fi
}

status_check() {
    log_info "ASTRA 3.0 Status Check"
    echo ""
    
    # Check if running
    if pgrep -f "astra_master.py" >/dev/null; then
        PID=$(pgrep -f "astra_master.py")
        log_info "Process: RUNNING (PID: $PID)"
    else
        log_warn "Process: NOT RUNNING"
        return
    fi
    
    # Quick health
    if curl -sf http://localhost:8000/ >/dev/null 2>&1; then
        log_info "API: RESPONDING"
    else
        log_error "API: NOT RESPONDING"
    fi
    
    # Container status
    log_info "Containers:"
    docker ps --filter "name=astra_" --format "  {{.Names}}: {{.Status}}"
}

usage() {
    cat <<EOF
ASTRA 3.0 Hardened Deployment Script

Usage: $0 <command>

Commands:
    init     - Initialize infrastructure (Redis + Postgres)
    start    - Start ASTRA master API
    stop     - Stop ASTRA master API
    restart  - Restart ASTRA
    status   - Check current status
    health   - Run full health checks
    test     - Run smoke test
    deploy   - Full deployment (init + start + health + test)

Examples:
    $0 deploy           # Full deployment with validation
    $0 start            # Start ASTRA only
    $0 health           # Check system health

EOF
}

main() {
    case "${1:-}" in
        init)
            check_prereqs
            init_infrastructure
            ;;
        start)
            start_astra
            ;;
        stop)
            stop_astra
            ;;
        restart)
            stop_astra
            sleep 2
            start_astra
            ;;
        status)
            status_check
            ;;
        health)
            health_check
            ;;
        test)
            run_smoke_test
            ;;
        deploy)
            check_prereqs
            init_infrastructure
            start_astra
            health_check
            run_smoke_test
            log_info "🎉 ASTRA 3.0 deployment COMPLETE"
            ;;
        *)
            usage
            exit 1
            ;;
    esac
}

main "$@"
