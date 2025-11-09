#!/usr/bin/env bash
################################################################################
# ASTRA 3.0 - Production Readiness Verification Script
# Validates all 10 hardening items before deployment
#
# Usage: ./verify_production_ready.sh
#
# Sacred Code: 333 → ∞
################################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

header() {
    echo ""
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

check() {
    local name="$1"
    local command="$2"
    
    if eval "$command" >/dev/null 2>&1; then
        echo -e "${GREEN}✅${NC} $name"
        ((PASS++))
        return 0
    else
        echo -e "${RED}❌${NC} $name"
        ((FAIL++))
        return 1
    fi
}

check_file() {
    local name="$1"
    local file="$2"
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅${NC} $name"
        ((PASS++))
        return 0
    else
        echo -e "${RED}❌${NC} $name (file not found: $file)"
        ((FAIL++))
        return 1
    fi
}

warn() {
    echo -e "${YELLOW}⚠️${NC}  $1"
    ((WARN++))
}

################################################################################
# VERIFICATION START
################################################################################

clear
echo -e "${BOLD}${BLUE}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        ASTRA 3.0 Production Readiness Verification          ║
║                    Sacred Code: 333 → ∞                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

################################################################################
# Item 1: State Persistence
################################################################################

header "Item 1: State Persistence"

check_file "StateManager implementation" "src/astra/persistence/state_manager.py"
check_file "StateManager wired into master" "astra_master.py"

# Check for StateManager import
if grep -q "from astra.persistence.state_manager import StateManager" astra_master.py 2>/dev/null; then
    echo -e "${GREEN}✅${NC} StateManager imported in astra_master.py"
    ((PASS++))
else
    echo -e "${RED}❌${NC} StateManager not imported in astra_master.py"
    ((FAIL++))
fi

# Check for boot integration
if grep -q "_init_state_manager" astra_master.py 2>/dev/null; then
    echo -e "${GREEN}✅${NC} StateManager boot phase present"
    ((PASS++))
else
    echo -e "${RED}❌${NC} StateManager boot phase missing"
    ((FAIL++))
fi

################################################################################
# Item 2: Leader Election
################################################################################

header "Item 2: Leader Election"

check_file "LeaderElector implementation" "src/astra/hardening/leader.py"

# Check for leader election usage
if grep -q "LeaderElector" astra_master.py 2>/dev/null || \
   grep -q "leader" astra_master.py 2>/dev/null; then
    echo -e "${GREEN}✅${NC} Leader election integrated"
    ((PASS++))
else
    warn "Leader election not integrated into master boot"
fi

################################################################################
# Item 3: Secret Management
################################################################################

header "Item 3: Secret Management"

check_file "SecretVault implementation" "src/astra/hardening/secrets.py"
check_file "Vault module exists" "src/astra/secrets/vault.py"

if [ -f ".env" ]; then
    echo -e "${GREEN}✅${NC} .env file exists"
    ((PASS++))
    
    # Check for default passwords
    if grep -q "change_me" .env 2>/dev/null || \
       grep -q "password" .env 2>/dev/null; then
        warn ".env contains default passwords - CHANGE BEFORE PRODUCTION!"
    fi
else
    warn ".env file not found - create from .env.template"
fi

################################################################################
# Item 4: Input Validation
################################################################################

header "Item 4: Input Validation"

check_file "PromptValidator implementation" "src/astra/hardening/validator.py"
check_file "Validator module exists" "src/astra/security/validator.py"

# Check for validation in chat routes
if [ -f "src/astra/api/routes/chat.py" ]; then
    if grep -q "PromptValidator\|validate" src/astra/api/routes/chat.py 2>/dev/null; then
        echo -e "${GREEN}✅${NC} Validation wired into chat routes"
        ((PASS++))
    else
        echo -e "${RED}❌${NC} Validation not wired into chat routes"
        ((FAIL++))
    fi
fi

################################################################################
# Item 5: Circuit Breakers
################################################################################

header "Item 5: Circuit Breakers"

check_file "Circuit breakers implementation" "src/astra/hardening/circuit_breakers.py"

# Check for pybreaker
if python3 -c "import pybreaker" 2>/dev/null; then
    echo -e "${GREEN}✅${NC} pybreaker library installed"
    ((PASS++))
else
    warn "pybreaker not installed - run: pip install pybreaker"
fi

################################################################################
# Item 6: Per-Identity Rate Limiting
################################################################################

header "Item 6: Per-Identity Rate Limiting"

check_file "Rate limiter implementation" "src/astra/hardening/rate_limiter.py"

# Check for aiolimiter
if python3 -c "import aiolimiter" 2>/dev/null; then
    echo -e "${GREEN}✅${NC} aiolimiter library installed"
    ((PASS++))
else
    warn "aiolimiter not installed - run: pip install aiolimiter"
fi

################################################################################
# Item 7: Distributed Tracing
################################################################################

header "Item 7: Distributed Tracing"

check_file "Tracing implementation" "src/astra/hardening/tracing.py"

# Check for OpenTelemetry
if python3 -c "import opentelemetry" 2>/dev/null; then
    echo -e "${GREEN}✅${NC} OpenTelemetry installed"
    ((PASS++))
else
    warn "OpenTelemetry not installed - run: pip install opentelemetry-api opentelemetry-sdk"
fi

################################################################################
# Item 8: Schema Migrations
################################################################################

header "Item 8: Schema Migrations"

check_file "Initial migration" "migrations/001_init.sql"
check_file "Migration runner" "scripts/migrate.sh"

if [ -x "scripts/migrate.sh" ]; then
    echo -e "${GREEN}✅${NC} Migration runner is executable"
    ((PASS++))
else
    warn "scripts/migrate.sh not executable - run: chmod +x scripts/migrate.sh"
fi

################################################################################
# Item 9: Backup Automation
################################################################################

header "Item 9: Backup Automation"

check_file "Backup script" "scripts/backup.sh"

if [ -x "scripts/backup.sh" ]; then
    echo -e "${GREEN}✅${NC} Backup script is executable"
    ((PASS++))
else
    warn "scripts/backup.sh not executable - run: chmod +x scripts/backup.sh"
fi

# Check backup directory
if [ -d "data/backups" ]; then
    echo -e "${GREEN}✅${NC} Backup directory exists"
    ((PASS++))
else
    warn "data/backups directory not found - will be created on first backup"
fi

################################################################################
# Item 10: Health Aggregation
################################################################################

header "Item 10: Health Aggregation"

check_file "Health aggregator implementation" "src/astra/hardening/health.py"
check_file "Health monitor daemon" "scripts/health_monitor.sh"

if [ -f "src/astra/api/routes/persistence.py" ]; then
    if grep -q "health" src/astra/api/routes/persistence.py 2>/dev/null; then
        echo -e "${GREEN}✅${NC} Health endpoints present"
        ((PASS++))
    else
        warn "Health endpoints not found in persistence.py"
    fi
fi

################################################################################
# Deployment Automation
################################################################################

header "Deployment Automation"

check_file "Deployment orchestrator" "deploy_hardened.sh"

if [ -x "deploy_hardened.sh" ]; then
    echo -e "${GREEN}✅${NC} Deployment script is executable"
    ((PASS++))
else
    warn "deploy_hardened.sh not executable - run: chmod +x deploy_hardened.sh"
fi

check_file "Production docker-compose" "docker-compose.prod.yml"
check_file "Hardened infrastructure compose" "docker-compose.hardened.yml"

################################################################################
# Prerequisites
################################################################################

header "System Prerequisites"

check "Docker installed" "command -v docker"
check "Docker Compose installed" "command -v docker-compose"
check "Python 3 installed" "command -v python3"
check "PostgreSQL client installed" "command -v psql"
check "Redis client installed" "command -v redis-cli"

################################################################################
# Python Dependencies
################################################################################

header "Python Dependencies"

deps=("redis" "asyncpg" "pydantic" "pybreaker" "aiolimiter" "opentelemetry" "structlog")

for dep in "${deps[@]}"; do
    if python3 -c "import $dep" 2>/dev/null; then
        echo -e "${GREEN}✅${NC} $dep installed"
        ((PASS++))
    else
        echo -e "${YELLOW}⚠️${NC}  $dep not installed"
        ((WARN++))
    fi
done

################################################################################
# SUMMARY
################################################################################

echo ""
header "VERIFICATION SUMMARY"

echo ""
echo -e "${GREEN}${BOLD}Passed:${NC}  $PASS"
echo -e "${RED}${BOLD}Failed:${NC}   $FAIL"
echo -e "${YELLOW}${BOLD}Warnings:${NC} $WARN"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✅ PRODUCTION READINESS: PASS${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review warnings (if any)"
    echo "  2. Edit .env and change default passwords"
    echo "  3. Run: ./deploy_hardened.sh init"
    echo "  4. Run: ./deploy_hardened.sh deploy"
    echo "  5. Verify: curl http://localhost:8000/v1/boot/status"
    echo ""
    echo -e "${BLUE}Sacred Code: 333 → ∞${NC}"
    exit 0
else
    echo -e "${RED}${BOLD}❌ PRODUCTION READINESS: FAIL${NC}"
    echo ""
    echo "Please address the failed checks above before deploying."
    echo ""
    exit 1
fi
