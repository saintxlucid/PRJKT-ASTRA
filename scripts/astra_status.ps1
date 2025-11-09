#!/usr/bin/env pwsh
<#
.SYNOPSIS
    ASTRA Status Checker

.DESCRIPTION
    Quick status check for all ASTRA components with color-coded output
    and actionable recommendations.

.EXAMPLE
    .\scripts\astra_status.ps1
    Check all components and display status
#>

param(
    [switch]$Detailed,
    [switch]$Json
)

# Set strict mode
Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

# Colors for output
$Colors = @{
    Green = "Green"
    Yellow = "Yellow"
    Red = "Red"
    Cyan = "Cyan"
    Magenta = "Magenta"
    White = "White"
}

function Write-ColorText {
    param([string]$Text, [string]$Color = "White")
    if (-not $Json) {
        Write-Host $Text -ForegroundColor $Colors[$Color]
    }
}

function Test-Component {
    param(
        [string]$Name,
        [string]$Url,
        [int]$TimeoutSec = 3
    )
    
    try {
        $response = Invoke-RestMethod -Uri $Url -TimeoutSec $TimeoutSec -ErrorAction Stop
        return @{
            name = $Name
            status = "healthy"
            url = $Url
            response = $response
            error = $null
        }
    } catch {
        return @{
            name = $Name
            status = "unhealthy"
            url = $Url
            response = $null
            error = $_.Exception.Message
        }
    }
}

function Get-AstraStatus {
    # Load environment variables
    if (Test-Path ".env") {
        Get-Content .env | ForEach-Object {
            if ($_ -match "^([^#][^=]+)=(.*)") {
                [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
            }
        }
    }
    
    $astraPort = if ($env:ASTRA_SERVER_PORT) { $env:ASTRA_SERVER_PORT } else { "8080" }
    $llamaUrl = if ($env:ASTRA_LLM_BASE_URL) { $env:ASTRA_LLM_BASE_URL } else { "http://127.0.0.1:8001" }
    $astraUrl = "http://127.0.0.1:$astraPort"
    
    $results = @{
        timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        overall_status = "unknown"
        components = @{}
        recommendations = @()
    }
    
    # Check llama.cpp server
    Write-ColorText "🦙 Checking llama.cpp server..." "Yellow"
    $llamaStatus = Test-Component -Name "llama.cpp" -Url "$llamaUrl/health"
    $results.components.llama = $llamaStatus
    
    if ($llamaStatus.status -eq "healthy") {
        Write-ColorText "  ✅ llama.cpp server: HEALTHY" "Green"
    } else {
        Write-ColorText "  ❌ llama.cpp server: UNHEALTHY" "Red"
        $results.recommendations += "Start llama.cpp server: .\scripts\start_gptoss_server.ps1"
    }
    
    # Check ASTRA API server
    Write-ColorText "🚀 Checking ASTRA API server..." "Yellow"
    $astraStatus = Test-Component -Name "astra_api" -Url "$astraUrl/v1/system/health"
    $results.components.astra_api = $astraStatus
    
    if ($astraStatus.status -eq "healthy") {
        Write-ColorText "  ✅ ASTRA API: HEALTHY" "Green"
        
        # Get detailed health if available
        if ($Detailed) {
            try {
                $healthzData = Invoke-RestMethod -Uri "$astraUrl/v1/system/healthz" -TimeoutSec 5
                $results.components.detailed_health = $healthzData
                
                Write-ColorText "  📊 Component Details:" "Cyan"
                foreach ($component in $healthzData.components.PSObject.Properties) {
                    $name = $component.Name
                    $status = $component.Value
                    $icon = if ($status.ok) { "✅" } else { "❌" }
                    
                    $detail = ""
                    if ($status.latency_ms) { $detail = " (${status.latency_ms}ms)" }
                    elseif ($status.count) { $detail = " ($($status.count) items)" }
                    
                    Write-ColorText "    $icon $name$detail" "White"
                }
            } catch {
                Write-ColorText "  ⚠️ Could not get detailed health info" "Yellow"
            }
        }
    } else {
        Write-ColorText "  ❌ ASTRA API: UNHEALTHY" "Red"
        $results.recommendations += "Start ASTRA server: .\LAUNCH_ASTRA.ps1"
    }
    
    # Check configuration files
    Write-ColorText "⚙️ Checking configuration..." "Yellow"
    $configStatus = @{
        env_file = Test-Path ".env"
        venv = Test-Path ".venv\Scripts\python.exe"
        persona_loaded = Test-Path "data\.astra_persona_loaded"
    }
    $results.components.config = $configStatus
    
    foreach ($check in $configStatus.GetEnumerator()) {
        $icon = if ($check.Value) { "✅" } else { "❌" }
        Write-ColorText "  $icon $($check.Key): $($check.Value)" "White"
        
        if (-not $check.Value) {
            switch ($check.Key) {
                "env_file" { $results.recommendations += "Create .env file from .env.example" }
                "venv" { $results.recommendations += "Set up virtual environment: poetry install" }
                "persona_loaded" { $results.recommendations += "Load persona: .\LAUNCH_ASTRA.ps1 -ForcePersonaReload" }
            }
        }
    }
    
    # Determine overall status
    $healthyComponents = 0
    $totalComponents = 0
    
    if ($llamaStatus.status -eq "healthy") { $healthyComponents++ }
    if ($astraStatus.status -eq "healthy") { $healthyComponents++ }
    $totalComponents = 2
    
    if ($healthyComponents -eq $totalComponents) {
        $results.overall_status = "healthy"
        Write-ColorText "`n🎉 Overall Status: HEALTHY" "Green"
    } elseif ($healthyComponents -gt 0) {
        $results.overall_status = "degraded"
        Write-ColorText "`n⚠️ Overall Status: DEGRADED" "Yellow"
    } else {
        $results.overall_status = "unhealthy"
        Write-ColorText "`n❌ Overall Status: UNHEALTHY" "Red"
    }
    
    # Show recommendations
    if ($results.recommendations.Count -gt 0 -and -not $Json) {
        Write-ColorText "`n💡 Recommendations:" "Cyan"
        foreach ($rec in $results.recommendations) {
            Write-ColorText "  • $rec" "Yellow"
        }
    }
    
    return $results
}

# Main execution
try {
    if (-not $Json) {
        Write-ColorText "┌─────────────────────────────────────────┐" "Cyan"
        Write-ColorText "│        🔍 ASTRA Status Check           │" "Cyan"
        Write-ColorText "└─────────────────────────────────────────┘" "Cyan"
        Write-Host ""
    }
    
    $statusResult = Get-AstraStatus
    
    if ($Json) {
        $statusResult | ConvertTo-Json -Depth 10
    } else {
        Write-Host ""
        Write-ColorText "Status check completed at $($statusResult.timestamp)" "White"
    }
    
} catch {
    if ($Json) {
        @{
            error = $_.Exception.Message
            timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        } | ConvertTo-Json
    } else {
        Write-ColorText "❌ Status check failed: $_" "Red"
    }
    exit 1
}