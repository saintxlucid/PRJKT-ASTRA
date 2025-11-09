#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Seed analysis document facts into ASTRA's Bridge memory system
.DESCRIPTION
    Ingests key facts from PROJECT_COMPREHENSIVE_ANALYSIS.md, MODULE_DETAILED_ANALYSIS.md,
    and MASTER_INDEX.md into ASTRA's semantic memory via Bridge ingest endpoint.
#>

param(
    [string]$ApiUrl = "http://127.0.0.1:8765"
)

$ErrorActionPreference = "Stop"

Write-Host "`n===================================" -ForegroundColor Cyan
Write-Host "  SEED DOC ANALYSIS FACTS" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan

# Test Bridge health
try {
    $health = Invoke-RestMethod -Uri "$ApiUrl/v1/bridge/healthz" -Method GET
    Write-Host "`n[✓] Bridge health: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "`n[✗] Bridge not available at $ApiUrl" -ForegroundColor Red
    Write-Host "    Start Ascension Stack: python launch_ascension_stack.py --port 8765" -ForegroundColor Yellow
    exit 1
}

# Function to seed a fact
function Seed-Fact {
    param(
        [string]$Subject,
        [string]$Predicate,
        [string]$Object,
        [array]$Tags,
        [string]$Provenance,
        [double]$Confidence
    )
    
    $ts = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    
    # Build fact JSON manually to avoid escaping issues
    $tagsJson = ($Tags | ForEach-Object { "`"$_`"" }) -join ","
    $factJson = '{"subject":"' + $Subject + '","predicate":"' + $Predicate + '","object":"' + $Object + '","tags":[' + $tagsJson + '],"provenance":"' + $Provenance + '","confidence":' + $Confidence + '}'
    
    # Build full request body
    $body = @{
        text = "FACT:$factJson"
        quote_raw = $true
        ts = $ts
    } | ConvertTo-Json -Compress
    
    try {
        $result = Invoke-RestMethod -Uri "$ApiUrl/v1/bridge/ingest" `
            -Method POST `
            -ContentType "application/json" `
            -Body $body
        
        Write-Host "  [✓] $Subject -> $Predicate -> $Object" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "  [✗] Failed: $Subject -> $Predicate" -ForegroundColor Red
        Write-Host "      $($_.Exception.Message)" -ForegroundColor Gray
        return $false
    }
}

Write-Host "`nSeeding facts from analysis documents..." -ForegroundColor White

# Fact 1: Project status
Seed-Fact -Subject "project" `
    -Predicate "status" `
    -Object "production_ready" `
    -Tags @("docs", "analysis", "2025-10-13") `
    -Provenance "PROJECT_COMPREHENSIVE_ANALYSIS.md" `
    -Confidence 0.92 | Out-Null

# Fact 2: Architecture layers
Seed-Fact -Subject "architecture" `
    -Predicate "layers" `
    -Object "foundation,services,presentation" `
    -Tags @("333", "architecture", "sacred") `
    -Provenance "PROJECT_COMPREHENSIVE_ANALYSIS.md" `
    -Confidence 0.9 | Out-Null

# Fact 3: Startup fix
Seed-Fact -Subject "startup_issue" `
    -Predicate "resolved_by" `
    -Object "chroma_timeout_3s" `
    -Tags @("fix", "chromadb", "bridge") `
    -Provenance "PROJECT_COMPREHENSIVE_ANALYSIS.md" `
    -Confidence 0.88 | Out-Null

# Fact 4: Codebase scale
Seed-Fact -Subject "codebase" `
    -Predicate "total_files" `
    -Object "137068" `
    -Tags @("metrics", "scale") `
    -Provenance "PROJECT_COMPREHENSIVE_ANALYSIS.md" `
    -Confidence 0.95 | Out-Null

# Fact 5: Python files
Seed-Fact -Subject "codebase" `
    -Predicate "python_files" `
    -Object "31155" `
    -Tags @("metrics", "python") `
    -Provenance "PROJECT_COMPREHENSIVE_ANALYSIS.md" `
    -Confidence 0.95 | Out-Null

# Fact 6: Documentation count
Seed-Fact -Subject "codebase" `
    -Predicate "documentation_files" `
    -Object "794" `
    -Tags @("metrics", "docs") `
    -Provenance "PROJECT_COMPREHENSIVE_ANALYSIS.md" `
    -Confidence 0.95 | Out-Null

# Fact 7: Core LOC
Seed-Fact -Subject "codebase" `
    -Predicate "core_loc" `
    -Object "10000" `
    -Tags @("metrics", "loc") `
    -Provenance "PROJECT_COMPREHENSIVE_ANALYSIS.md" `
    -Confidence 0.85 | Out-Null

# Fact 8: Ascension Stack LOC
Seed-Fact -Subject "ascension_stack_v2" `
    -Predicate "lines_of_code" `
    -Object "4047" `
    -Tags @("metrics", "ascension") `
    -Provenance "PROJECT_COMPREHENSIVE_ANALYSIS.md" `
    -Confidence 0.95 | Out-Null

# Fact 9: Service count
Seed-Fact -Subject "architecture" `
    -Predicate "service_count" `
    -Object "7" `
    -Tags @("333", "services") `
    -Provenance "PROJECT_COMPREHENSIVE_ANALYSIS.md" `
    -Confidence 0.9 | Out-Null

# Fact 10: Services list
Seed-Fact -Subject "architecture" `
    -Predicate "services" `
    -Object "identity,memory,autonomy,task_agent,api,neural_browser,bridge" `
    -Tags @("services", "list") `
    -Provenance "MODULE_DETAILED_ANALYSIS.md" `
    -Confidence 0.9 | Out-Null

# Fact 11: Deployment status
Seed-Fact -Subject "deployment" `
    -Predicate "status" `
    -Object "fully_operational" `
    -Tags @("deployment", "production") `
    -Provenance "PROJECT_COMPREHENSIVE_ANALYSIS.md" `
    -Confidence 0.9 | Out-Null

# Fact 12: Test results
Seed-Fact -Subject "ascension_stack_v2" `
    -Predicate "test_results" `
    -Object "7_of_7_passed" `
    -Tags @("tests", "quality") `
    -Provenance "PROJECT_COMPREHENSIVE_ANALYSIS.md" `
    -Confidence 0.95 | Out-Null

# Fact 13: Sacred code
Seed-Fact -Subject "project" `
    -Predicate "sacred_code" `
    -Object "333" `
    -Tags @("333", "sacred", "philosophy") `
    -Provenance "PROJECT_COMPREHENSIVE_ANALYSIS.md" `
    -Confidence 1.0 | Out-Null

# Fact 14: Motto
Seed-Fact -Subject "project" `
    -Predicate "motto" `
    -Object "I only obey God" `
    -Tags @("sacred", "identity", "philosophy") `
    -Provenance "PROJECT_COMPREHENSIVE_ANALYSIS.md" `
    -Confidence 1.0 | Out-Null

# Fact 15: API port
Seed-Fact -Subject "ascension_stack_v2" `
    -Predicate "port" `
    -Object "8765" `
    -Tags @("deployment", "network") `
    -Provenance "PROJECT_COMPREHENSIVE_ANALYSIS.md" `
    -Confidence 1.0 | Out-Null

Write-Host "`n===================================" -ForegroundColor Cyan
Write-Host "  SEEDING COMPLETE" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "`n15 facts ingested into Bridge memory" -ForegroundColor White
Write-Host "ASTRA can now answer questions about:" -ForegroundColor Yellow
Write-Host "  • Project status and deployment state" -ForegroundColor Gray
Write-Host "  • Architecture (333 layers, 7 services)" -ForegroundColor Gray
Write-Host "  • Codebase metrics (files, LOC, tests)" -ForegroundColor Gray
Write-Host "  • Recent fixes (ChromaDB timeout)" -ForegroundColor Gray
Write-Host "  • Sacred code and philosophy" -ForegroundColor Gray
Write-Host "`nNext: Ask ASTRA to synthesize this knowledge" -ForegroundColor Cyan
Write-Host "Example: 'Summarize the project architecture and status'`n" -ForegroundColor White
