#!/usr/bin/env pwsh
<#
.SYNOPSIS
    ASTRA 3.0 Health Monitor & Auto-Remediation
    Continuous monitoring with automatic service restart on failures
#>

param(
    [int]$CheckInterval = 30,          # Seconds between checks
    [int]$FailureThreshold = 3,        # Consecutive failures before action
    [switch]$Remediate = $true,        # Enable auto-remediation
    [switch]$Verbose = $false
)

$ROOT = $PSScriptRoot
$COMPOSE_FILE = Join-Path $ROOT "docker-compose.prod.yml"
$LOG_FILE = Join-Path $ROOT "data/logs/health_monitor.log"

# Service endpoints to monitor
$Services = @(
    @{ name = "astra-master"; port = 8000; healthPath = "/health" }
    @{ name = "memory-service"; port = 7007; healthPath = "/health" }
    @{ name = "sigil-gate"; port = 7701; healthPath = "/health" }
    @{ name = "supervisor"; port = 7703; healthPath = "/health" }
    @{ name = "postgres"; port = 5432; command = "pg_isready -U astra" }
    @{ name = "redis"; port = 6379; command = "redis-cli ping" }
)

# Track failure counts
$FailureCounts = @{}
$Services | ForEach-Object { $FailureCounts[$_.name] = 0 }

function Log-Status {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $entry = "[$timestamp] [$Level] $Message"
    Write-Host $entry
    Add-Content -Path $LOG_FILE -Value $entry -Encoding UTF8
}

function Check-Service {
    param([hashtable]$Service)
    
    try {
        if ($Service.ContainsKey('healthPath')) {
            # HTTP health check
            $url = "http://localhost:$($Service.port)$($Service.healthPath)"
            $response = Invoke-WebRequest -Uri $url -TimeoutSec 5 -ErrorAction SilentlyContinue
            return $response.StatusCode -eq 200
        } elseif ($Service.ContainsKey('command')) {
            # Command-based check
            $result = docker exec $($Service.name) $($Service.command) 2>&1
            return $LASTEXITCODE -eq 0
        }
    } catch {
        return $false
    }
}

function Remediate-Service {
    param([string]$ServiceName)
    
    if (-not $Remediate) {
        Log-Status "Remediation disabled, skipping $ServiceName" "WARN"
        return
    }
    
    Log-Status "🔧 Attempting remediation for $ServiceName..." "WARN"
    
    try {
        docker compose -f $COMPOSE_FILE restart $ServiceName
        Log-Status "✅ Restarted $ServiceName" "INFO"
        Start-Sleep -Seconds 5
    } catch {
        Log-Status "❌ Failed to remediate $ServiceName: $_" "ERROR"
    }
}

function Get-ServiceStatus {
    $status = @{}
    
    foreach ($service in $Services) {
        $healthy = Check-Service $service
        $status[$service.name] = $healthy
        
        if ($healthy) {
            $FailureCounts[$service.name] = 0
            if ($Verbose) { Log-Status "✅ $($service.name) healthy" "DEBUG" }
        } else {
            $FailureCounts[$service.name]++
            Log-Status "⚠️  $($service.name) unhealthy (failures: $($FailureCounts[$service.name]))" "WARN"
            
            if ($FailureCounts[$service.name] -ge $FailureThreshold) {
                Log-Status "🚨 $($service.name) exceeded failure threshold - triggering remediation" "ERROR"
                Remediate-Service $service.name
                $FailureCounts[$service.name] = 0
            }
        }
    }
    
    return $status
}

function Display-Summary {
    param([hashtable]$Status)
    
    $healthy = ($Status.Values | Where-Object { $_ }).Count
    $total = $Status.Count
    
    Write-Host "`n╔═════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║   ASTRA 3.0 Health Summary             ║" -ForegroundColor Cyan
    Write-Host "║   $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')                    ║" -ForegroundColor Cyan
    Write-Host "╠═════════════════════════════════════════╣" -ForegroundColor Cyan
    
    foreach ($service in $Services) {
        $isHealthy = $Status[$service.name]
        $symbol = if ($isHealthy) { "✅" } else { "❌" }
        Write-Host "║ $symbol $($service.name.PadRight(27)) │ $($FailureCounts[$service.name]) failures" -ForegroundColor $(if ($isHealthy) { "Green" } else { "Red" })
    }
    
    Write-Host "║                                         ║" -ForegroundColor Cyan
    Write-Host "║ Overall: $healthy/$total services healthy   ║" -ForegroundColor Cyan
    Write-Host "╚═════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

# Main monitoring loop
Log-Status "🚀 ASTRA 3.0 Health Monitor started" "INFO"
Log-Status "Check interval: ${CheckInterval}s | Failure threshold: ${FailureThreshold} | Auto-remediation: $Remediate" "INFO"

try {
    while ($true) {
        $status = Get-ServiceStatus
        Display-Summary $status
        Start-Sleep -Seconds $CheckInterval
    }
} catch {
    Log-Status "❌ Monitor error: $_" "ERROR"
    exit 1
} finally {
    Log-Status "🛑 Health Monitor stopped" "INFO"
}
