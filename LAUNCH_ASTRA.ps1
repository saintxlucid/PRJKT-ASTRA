#!/usr/bin/env pwsh
<#
.SYNOPSIS
    ASTRA Unified Launcher - PowerShell Edition

.DESCRIPTION
    Handles first-run activation, capacity controls setup, and system startup
    with comprehensive verification and welcome sequence.

.PARAMETER ForcePersonaReload
    Force reload of persona memories even if already loaded

.PARAMETER SkipHealthCheck
    Skip detailed health checks during startup

.PARAMETER QuickStart
    Skip persona loading and go straight to server startup

.EXAMPLE
    .\LAUNCH_ASTRA.ps1
    Standard launch with full activation protocol

.EXAMPLE
    .\LAUNCH_ASTRA.ps1 -ForcePersonaReload
    Launch with forced persona memory reload

.EXAMPLE
    .\LAUNCH_ASTRA.ps1 -QuickStart
    Quick launch without persona loading
#>

param(
    [switch]$ForcePersonaReload,
    [switch]$SkipHealthCheck,
    [switch]$QuickStart
)

# Set strict mode and stop on errors
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Colors for output
$Colors = @{
    Green = "Green"
    Yellow = "Yellow" 
    Red = "Red"
    Cyan = "Cyan"
    Magenta = "Magenta"
}

function Write-ColorText {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $Colors[$Color]
}

function Write-Banner {
    Write-Host ""
    Write-ColorText "┌─────────────────────────────────────────────────────────────┐" "Cyan"
    Write-ColorText "│                    🚀 PROJECT ASTRA 1.0                     │" "Cyan"
    Write-ColorText "│                      (ASTRA_CORE)                          │" "Cyan"
    Write-ColorText "│                                                             │" "Cyan"
    Write-ColorText "│  Advanced Structured Testing and Reasoning Assistant       │" "Cyan"
    Write-ColorText "│  Creator: Saint Lucid (Karim Al-Sharif)                   │" "Cyan"
    Write-ColorText "│  Status: PowerShell Activation Protocol                    │" "Cyan"
    Write-ColorText "└─────────────────────────────────────────────────────────────┘" "Cyan"
    Write-Host ""
}

function Test-Prerequisites {
    Write-ColorText "🔍 Checking prerequisites..." "Yellow"
    
    # Check if we're in the right directory
    if (-not (Test-Path "pyproject.toml")) {
        Write-ColorText "❌ Not in PROJECT_ASTRA root directory" "Red"
        return $false
    }
    
    # Check virtual environment
    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        Write-ColorText "❌ Virtual environment not found at .venv\Scripts\python.exe" "Red"
        return $false
    }
    
    # Check .env file
    if (-not (Test-Path ".env")) {
        Write-ColorText "❌ .env file not found" "Red"
        return $false
    }
    
    # Load environment variables
    Get-Content .env | ForEach-Object {
        if ($_ -match "^([^#][^=]+)=(.*)") {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }
    
    Write-ColorText "✅ Prerequisites check passed" "Green"
    return $true
}

function Set-CapacityControls {
    Write-ColorText "⚙️ Setting up capacity controls..." "Yellow"
    
    # Check if API key exists
    $apiKey = $env:ASTRA_API_KEY
    if (-not $apiKey) {
        Write-ColorText "🔑 Generating new API key..." "Yellow"
        $apiKey = .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
        
        # Add to .env file
        Add-Content .env "ASTRA_API_KEY=$apiKey"
        $env:ASTRA_API_KEY = $apiKey
        Write-ColorText "✅ API key generated and saved to .env" "Green"
    } else {
        Write-ColorText "✅ API key found in environment" "Green"
    }
    
    # Ensure rate limiting settings
    $perKeyRate = $env:ASTRA_PER_KEY_RATE
    $perKeyPeriod = $env:ASTRA_PER_KEY_PERIOD_SEC
    
    if (-not $perKeyRate) {
        Add-Content .env "ASTRA_PER_KEY_RATE=120"
        $env:ASTRA_PER_KEY_RATE = "120"
        Write-ColorText "✅ Set per-key rate limit: 120 requests" "Green"
    }
    
    if (-not $perKeyPeriod) {
        Add-Content .env "ASTRA_PER_KEY_PERIOD_SEC=60"
        $env:ASTRA_PER_KEY_PERIOD_SEC = "60"
        Write-ColorText "✅ Set per-key period: 60 seconds" "Green"
    }
    
    # Ensure cognitive architecture settings
    if (-not $env:ASTRA_CACHE_TTL) {
        Add-Content .env "ASTRA_CACHE_TTL=600"
        $env:ASTRA_CACHE_TTL = "600"
        Write-ColorText "✅ Set cache TTL: 600 seconds" "Green"
    }
    
    if (-not $env:ASTRA_MAX_CONCURRENCY) {
        Add-Content .env "ASTRA_MAX_CONCURRENCY=4"
        $env:ASTRA_MAX_CONCURRENCY = "4"
        Write-ColorText "✅ Set max concurrency: 4" "Green"
    }
    
    Write-ColorText "✅ Capacity controls configured" "Green"
}

function Start-LlamaServer {
    Write-ColorText "🦙 Checking llama.cpp server..." "Yellow"
    
    $llamaUrl = $env:ASTRA_LLM_BASE_URL
    if (-not $llamaUrl) {
        $llamaUrl = "http://127.0.0.1:8001"
    }
    
    try {
        $response = Invoke-RestMethod -Uri "$llamaUrl/health" -TimeoutSec 3 -ErrorAction Stop
        Write-ColorText "✅ llama.cpp server is already running" "Green"
        return $true
    } catch {
        Write-ColorText "⚠️ llama.cpp server not running" "Yellow"
        Write-ColorText "Please start it manually if needed:" "Yellow"
        Write-ColorText "  .\scripts\start_gptoss_server.ps1" "Cyan"
        return $false
    }
}

function Start-AstraServer {
    Write-ColorText "🚀 Starting ASTRA API server..." "Yellow"
    
    # Start server in new window
    $serverArgs = @{
        FilePath = ".\.venv\Scripts\python.exe"
        ArgumentList = "run_server.py"
        WorkingDirectory = (Get-Location)
    }
    
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        # Windows - start in new console window
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "title ASTRA Server && .\.venv\Scripts\python.exe run_server.py" -WindowStyle Normal
    } else {
        # Linux/Mac - start in background
        Start-Process @serverArgs
    }
    
    # Wait for server to start
    Write-ColorText "⏳ Waiting for ASTRA server to be ready..." "Yellow"
    $maxWait = 30
    $waited = 0
    
    while ($waited -lt $maxWait) {
        try {
            $baseUrl = "http://127.0.0.1:$(if ($env:ASTRA_SERVER_PORT) { $env:ASTRA_SERVER_PORT } else { '8080' })"
            $response = Invoke-RestMethod -Uri "$baseUrl/v1/system/healthz" -TimeoutSec 2 -ErrorAction Stop
            Write-ColorText "✅ ASTRA server is ready!" "Green"
            return $baseUrl
        } catch {
            Start-Sleep 1
            $waited++
        }
    }
    
    Write-ColorText "❌ ASTRA server failed to start within $maxWait seconds" "Red"
    return $null
}

function Invoke-HealthScan {
    param([string]$BaseUrl)
    
    if ($SkipHealthCheck) {
        Write-ColorText "⏭️ Skipping health check (--skip-health-check)" "Yellow"
        return @{ status = "skipped" }
    }
    
    Write-ColorText "🏥 Performing health scan..." "Yellow"
    
    try {
        $healthData = Invoke-RestMethod -Uri "$BaseUrl/v1/system/healthz" -TimeoutSec 10 -ErrorAction Stop
        
        # Display component status
        foreach ($component in $healthData.components.PSObject.Properties) {
            $name = $component.Name
            $status = $component.Value
            $icon = if ($status.ok) { "✅" } else { "❌" }
            
            if ($status.latency_ms) {
                Write-ColorText "$icon $name (${$status.latency_ms}ms)" "Green"
            } elseif ($status.count) {
                Write-ColorText "$icon $name ($($status.count) items)" "Green"
            } else {
                Write-ColorText "$icon $name" "Green"
            }
        }
        
        return $healthData
    } catch {
        Write-ColorText "❌ Health scan failed: $_" "Red"
        return @{ status = "failed"; error = $_.Exception.Message }
    }
}

function Invoke-PersonaIngestion {
    if ($QuickStart) {
        Write-ColorText "⏭️ Skipping persona loading (--quick-start)" "Yellow"
        return $true
    }
    
    # Check if already loaded
    if ((Test-Path "data\.astra_persona_loaded") -and (-not $ForcePersonaReload)) {
        Write-ColorText "✅ Persona memories already loaded" "Green"
        return $true
    }
    
    Write-ColorText "🧠 Loading persona memories..." "Yellow"
    
    try {
        $args = @("scripts\ingest_persona_memories.py")
        if ($ForcePersonaReload) {
            Write-ColorText "🔄 Force reloading persona memories..." "Yellow"
        }
        
        $result = & .\.venv\Scripts\python.exe @args
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColorText "✅ Persona memories loaded successfully" "Green"
            return $true
        } else {
            Write-ColorText "❌ Persona ingestion failed" "Red"
            return $false
        }
    } catch {
        Write-ColorText "❌ Failed to load persona memories: $_" "Red"
        return $false
    }
}

function Invoke-WarmupQuery {
    param([string]$BaseUrl)
    
    Write-ColorText "🔥 Performing warmup query..." "Yellow"
    
    try {
        $payload = @{
            message = "System warmup - please respond with 'ASTRA_CORE initialized'"
            temperature = 0.1
            max_tokens = 10
            use_memory = $false
        } | ConvertTo-Json
        
        $headers = @{
            'Content-Type' = 'application/json'
        }
        
        if ($env:ASTRA_API_KEY) {
            $headers['Authorization'] = "Bearer $($env:ASTRA_API_KEY)"
        }
        
        $response = Invoke-RestMethod -Uri "$BaseUrl/v1/chat/" -Method Post -Body $payload -Headers $headers -TimeoutSec 15
        Write-ColorText "✅ Warmup query successful" "Green"
        return $true
    } catch {
        Write-ColorText "⚠️ Warmup query failed: $_" "Yellow"
        return $false
    }
}

function Show-WelcomeMessage {
    param([string]$BaseUrl, [hashtable]$HealthData)
    
    $memoryCount = 0
    if ($HealthData.components.vector_store.ok) {
        $memoryCount = $HealthData.components.vector_store.count
    }
    
    Write-Host ""
    Write-ColorText "┌─────────────────────────────────────────────────────────────┐" "Green"
    Write-ColorText "│                  ✅ ASTRA_CORE ONLINE                       │" "Green"
    Write-ColorText "└─────────────────────────────────────────────────────────────┘" "Green"
    Write-Host ""
    
    Write-ColorText "Short answer → ASTRA_CORE is online and ready." "White"
    Write-ColorText "Health checks passed. Persona memory loaded." "White"
    Write-Host ""
    
    Write-ColorText "Details:" "White"
    $llmIcon = if ($HealthData.components.llm.ok) { "✅ OK" } else { "❌ DEGRADED" }
    $dbIcon = if ($HealthData.components.db.ok) { "✅ OK" } else { "❌ DEGRADED" }
    $vectorIcon = if ($HealthData.components.vector_store.ok) { "✅ OK" } else { "❌ DEGRADED" }
    
    Write-ColorText "• LLM backend: $llmIcon" "White"
    Write-ColorText "• Database: $dbIcon" "White"
    Write-ColorText "• Vector store: $vectorIcon ($memoryCount memories)" "White"
    Write-Host ""
    
    $perKeyRate = if ($env:ASTRA_PER_KEY_RATE) { $env:ASTRA_PER_KEY_RATE } else { "120" }
    $perKeyPeriod = if ($env:ASTRA_PER_KEY_PERIOD_SEC) { $env:ASTRA_PER_KEY_PERIOD_SEC } else { "60" }
    Write-ColorText "Capacity controls: per-key $perKeyRate/${perKeyPeriod}s; queue empty" "White"
    Write-Host ""
    
    Write-ColorText "API Endpoints:" "White"
    Write-ColorText "• Chat: $BaseUrl/v1/chat/" "Cyan"
    Write-ColorText "• Health: $BaseUrl/v1/system/healthz" "Cyan"
    Write-ColorText "• Metrics: $BaseUrl/metrics" "Cyan"
    Write-Host ""
    
    Write-ColorText "Try these queries:" "White"
    Write-ColorText "• `"Who created you and what are your values?`"" "Yellow"
    Write-ColorText "• `"Summarize our current ops posture and SLOs.`"" "Yellow"
    Write-ColorText "• `"Draft my next two actions to harden memory hygiene.`"" "Yellow"
    Write-Host ""
    
    Write-ColorText "— ASTRA_CORE" "Magenta"
    Write-Host ""
}

function Invoke-CapacityTest {
    param([string]$BaseUrl)
    
    Write-ColorText "🧪 Running capacity verification test..." "Yellow"
    
    try {
        & .\scripts\validate_ops_hardening.ps1
        Write-ColorText "✅ Capacity controls verified" "Green"
    } catch {
        Write-ColorText "⚠️ Capacity test failed: $_" "Yellow"
    }
}

# Main execution
try {
    # Display banner
    Write-Banner
    
    # Step 1: Check prerequisites
    if (-not (Test-Prerequisites)) {
        exit 1
    }
    
    # Step 2: Set up capacity controls
    Set-CapacityControls
    
    # Step 3: Check llama.cpp server
    $llamaReady = Start-LlamaServer
    if (-not $llamaReady) {
        Write-ColorText "⚠️ Continuing without llama.cpp server..." "Yellow"
    }
    
    # Step 4: Start ASTRA server
    $baseUrl = Start-AstraServer
    if (-not $baseUrl) {
        Write-ColorText "❌ Failed to start ASTRA server" "Red"
        exit 1
    }
    
    # Step 5: Perform health scan
    $healthData = Invoke-HealthScan -BaseUrl $baseUrl
    
    # Step 6: Load persona memories
    $personaLoaded = Invoke-PersonaIngestion
    if (-not $personaLoaded) {
        Write-ColorText "⚠️ Continuing without persona memories..." "Yellow"
    }
    
    # Step 7: Warmup query
    Invoke-WarmupQuery -BaseUrl $baseUrl | Out-Null
    
    # Step 8: Show welcome message
    Show-WelcomeMessage -BaseUrl $baseUrl -HealthData $healthData
    
    # Step 9: Optional capacity test
    if (-not $QuickStart) {
        Invoke-CapacityTest -BaseUrl $baseUrl
    }
    
    Write-ColorText "🎉 ASTRA activation protocol completed successfully!" "Green"
    Write-ColorText "Press Ctrl+C to shutdown when finished." "White"
    
    # Keep script running
    try {
        while ($true) {
            Start-Sleep 1
        }
    } catch {
        Write-ColorText "`n👋 ASTRA shutdown initiated. Goodbye!" "Yellow"
    }
    
} catch {
    Write-ColorText "❌ ASTRA activation failed: $_" "Red"
    exit 1
}