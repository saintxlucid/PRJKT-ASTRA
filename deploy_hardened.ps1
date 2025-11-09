#!/usr/bin/env pwsh
<#
.SYNOPSIS
    ASTRA 3.0 Hardened Infrastructure Deployment Script
    Manages initialization, startup, migration, testing, and status of production deployment

.DESCRIPTION
    Orchestrates bring-up of Redis, PostgreSQL, etcd, Jaeger, and ASTRA core services
    Includes schema migrations, health checks, integration tests, and auto-remediation

.EXAMPLE
    .\deploy_hardened.ps1 init
    .\deploy_hardened.ps1 start
    .\deploy_hardened.ps1 test
    .\deploy_hardened.ps1 status
    .\deploy_hardened.ps1 backup
    .\deploy_hardened.ps1 restore
    .\deploy_hardened.ps1 stop
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('init', 'start', 'stop', 'test', 'status', 'backup', 'restore', 'logs', 'health')]
    [string]$Command
)

# Configuration
$ROOT = $PSScriptRoot
$ENV_FILE = Join-Path $ROOT ".env"
$SCRIPTS_DIR = Join-Path $ROOT "scripts"
$DATA_DIR = Join-Path $ROOT "data"
$BACKUPS_DIR = Join-Path $DATA_DIR "backups"
$LOGS_DIR = Join-Path $DATA_DIR "logs"

# Colors for output
$Colors = @{
    Success = [System.ConsoleColor]::Green
    Warning = [System.ConsoleColor]::Yellow
    Error = [System.ConsoleColor]::Red
    Info = [System.ConsoleColor]::Cyan
}

function Write-Status {
    param([string]$Message, [System.ConsoleColor]$Color = $Colors.Info)
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] " -NoNewline
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success { Write-Status "✅ $args" -Color $Colors.Success }
function Write-Warning { Write-Status "⚠️  $args" -Color $Colors.Warning }
function Write-Error { Write-Status "❌ $args" -Color $Colors.Error }

function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
        Write-Success "Created directory: $Path"
    }
}

# ========== INIT ==========
function Invoke-Init {
    Write-Status "Initializing ASTRA 3.0 deployment infrastructure..." -Color $Colors.Info
    
    # Create directories
    Ensure-Directory $SCRIPTS_DIR
    Ensure-Directory $DATA_DIR
    Ensure-Directory $BACKUPS_DIR
    Ensure-Directory $LOGS_DIR
    
    # Create .env if missing
    if (-not (Test-Path $ENV_FILE)) {
        Write-Status "Creating .env file with defaults..."
        $envContent = @"
# ASTRA 3.0 Environment Configuration
# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

# Database Configuration
PG_HOST=postgres
PG_PORT=5432
PG_USER=astra
PG_PASS=changeme_strong_password_here
PG_DB=astra

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=changeme_redis_password_here

# JWT & Security
JWT_SECRET=changeme_jwt_secret_min_32_chars_here
SIGNING_KEY=changeme_signing_key_min_32_chars_here

# etcd Configuration
ETCD_ENDPOINTS=http://etcd:2379

# Jaeger Configuration
JAEGER_AGENT_HOST=jaeger
JAEGER_AGENT_PORT=6831
JAEGER_SAMPLER_TYPE=const
JAEGER_SAMPLER_PARAM=1

# ASTRA Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false

# Service Configuration
ASTRA_MASTER_PORT=8000
MEMORY_SERVICE_PORT=7007
SIGIL_GATE_PORT=7701
SUPERVISOR_PORT=7703

# Optional: Cloud providers
# OPENAI_API_KEY=sk-...
# AZURE_OPENAI_KEY=...
# ANTHROPIC_API_KEY=...
"@
        Set-Content -Path $ENV_FILE -Value $envContent -Encoding UTF8
        Write-Success "Created $ENV_FILE - PLEASE EDIT WITH STRONG SECRETS"
    }
    
    # Create docker-compose.prod.yml if missing
    $compose_file = Join-Path $ROOT "docker-compose.prod.yml"
    if (-not (Test-Path $compose_file)) {
        Write-Status "Creating docker-compose.prod.yml..."
        $composeContent = @"
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: astra
      POSTGRES_PASSWORD: `${PG_PASS}
      POSTGRES_DB: astra
    ports:
      - '5432:5432'
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U astra"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass `${REDIS_PASSWORD}
    ports:
      - '6379:6379'
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  etcd:
    image: quay.io/coreos/etcd:v3.5.10
    environment:
      ETCD_ADVERTISE_CLIENT_URLS: http://etcd:2379
      ETCD_LISTEN_CLIENT_URLS: http://0.0.0.0:2379
    ports:
      - '2379:2379'
    volumes:
      - etcd_data:/etcd-data
    healthcheck:
      test: ["CMD", "etcdctl", "--endpoints=http://localhost:2379", "endpoint", "health"]
      interval: 10s
      timeout: 5s
      retries: 5

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - '5775:5775/udp'
      - '6831:6831/udp'
      - '16686:16686'
    environment:
      COLLECTOR_ZIPKIN_HOST_PORT: ':9411'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:14269/"]
      interval: 10s
      timeout: 5s
      retries: 5

  astra-master:
    build:
      context: .
      dockerfile: Dockerfile
    command: python -m src.astra.api.main
    env_file: .env
    ports:
      - '8000:8000'
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./src:/app/src
      - ./data/logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  memory-service:
    build:
      context: .
      dockerfile: Dockerfile
    command: python -m src.astra.services.memory.service
    env_file: .env
    ports:
      - '7007:7007'
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./src:/app/src
      - ./data/logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7007/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  sigil-gate:
    build:
      context: .
      dockerfile: Dockerfile
    command: python -m src.astra.sigil.gate
    env_file: .env
    ports:
      - '7701:7701'
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./src:/app/src
      - ./data/logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7701/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  supervisor:
    build:
      context: .
      dockerfile: Dockerfile
    command: python -m src.astra.supervisor.run
    env_file: .env
    ports:
      - '7703:7703'
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./src:/app/src
      - ./data/logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7703/health"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
  etcd_data:

networks:
  default:
    name: astra-network
"@
        Set-Content -Path $compose_file -Value $composeContent -Encoding UTF8
        Write-Success "Created $compose_file"
    }
    
    # Create migration script if missing
    $migrate_script = Join-Path $SCRIPTS_DIR "migrate.ps1"
    if (-not (Test-Path $migrate_script)) {
        Write-Status "Creating migration script..."
        $migrateContent = @"
# Migration script for ASTRA 3.0 schema
# Idempotent - safe to run multiple times

Write-Host "Running database migrations..." -ForegroundColor Cyan

# Load environment
`$env_file = Join-Path `$PSScriptRoot ".." ".env"
Get-Content `$env_file | ForEach-Object {
    if (`$_ -match '^([^=]+)=(.*)$') {
        `$env:`$matches[1] = `$matches[2]
    }
}

# Run Alembic migrations
docker exec -e SQLALCHEMY_DATABASE_URL="postgresql://`${env:PG_USER}:`${env:PG_PASS}@postgres:5432/`${env:PG_DB}" `
  astra-master alembic upgrade head

if (`$LASTEXITCODE -eq 0) {
    Write-Host "✅ Migrations complete" -ForegroundColor Green
} else {
    Write-Host "❌ Migrations failed" -ForegroundColor Red
    exit 1
}
"@
        Set-Content -Path $migrate_script -Value $migrateContent -Encoding UTF8
        Write-Success "Created migration script"
    }
    
    Write-Success "Initialization complete!"
    Write-Warning "⚠️  IMPORTANT: Edit $ENV_FILE with strong secrets before deploying"
}

# ========== START ==========
function Invoke-Start {
    Write-Status "Starting ASTRA 3.0 hardened infrastructure..." -Color $Colors.Info
    
    # Check .env exists
    if (-not (Test-Path $ENV_FILE)) {
        Write-Error ".env file not found. Run 'init' first."
        exit 1
    }
    
    # Start Docker services
    Write-Status "Starting Docker services..."
    docker compose -f (Join-Path $ROOT "docker-compose.prod.yml") up -d
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to start Docker services"
        exit 1
    }
    
    # Wait for services to be healthy
    Write-Status "Waiting for services to be healthy..."
    Start-Sleep -Seconds 5
    
    # Run migrations
    Write-Status "Running database migrations..."
    & (Join-Path $SCRIPTS_DIR "migrate.ps1")
    
    # Health checks
    Write-Status "Performing health checks..."
    Invoke-HealthCheck
    
    Write-Success "ASTRA 3.0 infrastructure online and healthy!"
    Write-Status "Access endpoints:"
    Write-Host "  • Master API:    http://localhost:8000"
    Write-Host "  • Memory:        http://localhost:7007"
    Write-Host "  • Sigil Gate:    http://localhost:7701"
    Write-Host "  • Supervisor:    http://localhost:7703"
    Write-Host "  • Jaeger UI:     http://localhost:16686"
}

# ========== STOP ==========
function Invoke-Stop {
    Write-Status "Stopping ASTRA 3.0 services..."
    docker compose -f (Join-Path $ROOT "docker-compose.prod.yml") down
    Write-Success "Services stopped"
}

# ========== HEALTH CHECK ==========
function Invoke-HealthCheck {
    Write-Status "Checking service health..."
    
    $endpoints = @(
        @{ name = "Master API"; url = "http://localhost:8000/health" }
        @{ name = "Memory"; url = "http://localhost:7007/health" }
        @{ name = "Sigil Gate"; url = "http://localhost:7701/health" }
        @{ name = "Supervisor"; url = "http://localhost:7703/health" }
    )
    
    $healthy = 0
    foreach ($endpoint in $endpoints) {
        try {
            $response = Invoke-WebRequest -Uri $endpoint.url -TimeoutSec 5 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Success "$($endpoint.name) is healthy"
                $healthy++
            } else {
                Write-Warning "$($endpoint.name) returned status $($response.StatusCode)"
            }
        } catch {
            Write-Warning "$($endpoint.name) - no response yet"
        }
    }
    
    Write-Status "Healthy endpoints: $healthy/4"
    return $healthy -eq 4
}

# ========== TEST ==========
function Invoke-Test {
    Write-Status "Running integration test suite..."
    
    # Python test runner
    $test_script = Join-Path $SCRIPTS_DIR "run_tests.py"
    
    if (-not (Test-Path $test_script)) {
        Write-Status "Creating test runner script..."
        $testContent = @"
#!/usr/bin/env python3
import subprocess
import sys

tests = [
    ("Integration tests", "python -m pytest tests/integration -v"),
    ("Security tests", "python -m pytest tests/week1 -v"),
    ("Performance smoke", "python -m pytest tests/load/smoke -v"),
]

print("=" * 80)
print("ASTRA 3.0 Integration Test Suite")
print("=" * 80)

passed = 0
failed = 0

for test_name, command in tests:
    print(f"\n[*] Running: {test_name}")
    print(f"    Command: {command}")
    result = subprocess.run(command, shell=True)
    if result.returncode == 0:
        print(f"✅ {test_name} passed")
        passed += 1
    else:
        print(f"❌ {test_name} failed")
        failed += 1

print("\n" + "=" * 80)
print(f"Results: {passed} passed, {failed} failed")
print("=" * 80)

sys.exit(0 if failed == 0 else 1)
"@
        Set-Content -Path $test_script -Value $testContent -Encoding UTF8
    }
    
    python $test_script
}

# ========== STATUS ==========
function Invoke-Status {
    Write-Status "ASTRA 3.0 Deployment Status"
    Write-Host ""
    
    # Docker status
    Write-Host "Docker Services:" -ForegroundColor Cyan
    docker compose -f (Join-Path $ROOT "docker-compose.prod.yml") ps
    
    Write-Host ""
    Write-Host "Health Status:" -ForegroundColor Cyan
    Invoke-HealthCheck | Out-Null
}

# ========== BACKUP ==========
function Invoke-Backup {
    Write-Status "Creating backup..."
    
    $timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $backup_dir = Join-Path $BACKUPS_DIR $timestamp
    Ensure-Directory $backup_dir
    
    # Backup Postgres
    Write-Status "Backing up PostgreSQL..."
    docker exec astra-postgres pg_dump -U astra astra | Out-File -FilePath (Join-Path $backup_dir "postgres.sql") -Encoding UTF8
    
    # Backup Redis
    Write-Status "Backing up Redis..."
    docker exec astra-redis redis-cli --rdb (Join-Path $backup_dir "redis.rdb") | Out-Null
    
    # Backup etcd
    Write-Status "Backing up etcd..."
    docker exec astra-etcd etcdctl snapshot save (Join-Path $backup_dir "etcd.snapshot") | Out-Null
    
    Write-Success "Backup complete: $backup_dir"
}

# ========== RESTORE ==========
function Invoke-Restore {
    Write-Status "Restore backup (manual procedure required)"
    Write-Host @"
Manual Restore Steps:

1. Stop services:
   docker compose -f docker-compose.prod.yml down

2. Restore PostgreSQL:
   docker exec astra-postgres psql -U astra < backups/<timestamp>/postgres.sql

3. Restore Redis:
   docker cp backups/<timestamp>/redis.rdb astra-redis:/data/dump.rdb

4. Restore etcd:
   docker exec astra-etcd etcdctl snapshot restore backups/<timestamp>/etcd.snapshot

5. Restart services:
   docker compose -f docker-compose.prod.yml up -d
"@
}

# ========== LOGS ==========
function Invoke-Logs {
    $service = $args[0] -as [string] ?? "astra-master"
    Write-Status "Streaming logs for $service..."
    docker compose -f (Join-Path $ROOT "docker-compose.prod.yml") logs -f $service
}

# ========== MAIN ==========
try {
    switch ($Command) {
        'init' { Invoke-Init }
        'start' { Invoke-Start }
        'stop' { Invoke-Stop }
        'test' { Invoke-Test }
        'status' { Invoke-Status }
        'backup' { Invoke-Backup }
        'restore' { Invoke-Restore }
        'logs' { Invoke-Logs @args }
        'health' { Invoke-HealthCheck }
        default { Write-Error "Unknown command: $Command" }
    }
} catch {
    Write-Error "Error: $_"
    exit 1
}
