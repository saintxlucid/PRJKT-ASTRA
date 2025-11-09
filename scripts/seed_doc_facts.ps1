#!/usr/bin/env pwsh
# Seed analysis document facts into ASTRA Bridge memory

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
    Write-Host "`n[OK] Bridge health: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "`n[ERROR] Bridge not available at $ApiUrl" -ForegroundColor Red
    Write-Host "    Start Ascension Stack: python launch_ascension_stack.py --port 8765" -ForegroundColor Yellow
    exit 1
}

Write-Host "`nSeeding facts from analysis documents..." -ForegroundColor White

$facts = @(
    @{subject="project"; predicate="status"; object="production_ready"; tags=@("docs","analysis"); provenance="PROJECT_COMPREHENSIVE_ANALYSIS.md"; confidence=0.92}
    @{subject="architecture"; predicate="layers"; object="foundation,services,presentation"; tags=@("333","architecture"); provenance="PROJECT_COMPREHENSIVE_ANALYSIS.md"; confidence=0.9}
    @{subject="startup_issue"; predicate="resolved_by"; object="chroma_timeout_3s"; tags=@("fix","chromadb"); provenance="PROJECT_COMPREHENSIVE_ANALYSIS.md"; confidence=0.88}
    @{subject="codebase"; predicate="total_files"; object="137068"; tags=@("metrics","scale"); provenance="PROJECT_COMPREHENSIVE_ANALYSIS.md"; confidence=0.95}
    @{subject="codebase"; predicate="python_files"; object="31155"; tags=@("metrics","python"); provenance="PROJECT_COMPREHENSIVE_ANALYSIS.md"; confidence=0.95}
    @{subject="codebase"; predicate="documentation_files"; object="794"; tags=@("metrics","docs"); provenance="PROJECT_COMPREHENSIVE_ANALYSIS.md"; confidence=0.95}
    @{subject="codebase"; predicate="core_loc"; object="10000"; tags=@("metrics","loc"); provenance="PROJECT_COMPREHENSIVE_ANALYSIS.md"; confidence=0.85}
    @{subject="ascension_stack_v2"; predicate="lines_of_code"; object="4047"; tags=@("metrics","ascension"); provenance="PROJECT_COMPREHENSIVE_ANALYSIS.md"; confidence=0.95}
    @{subject="architecture"; predicate="service_count"; object="7"; tags=@("333","services"); provenance="PROJECT_COMPREHENSIVE_ANALYSIS.md"; confidence=0.9}
    @{subject="architecture"; predicate="services"; object="identity,memory,autonomy,task_agent,api,neural_browser,bridge"; tags=@("services","list"); provenance="MODULE_DETAILED_ANALYSIS.md"; confidence=0.9}
    @{subject="deployment"; predicate="status"; object="fully_operational"; tags=@("deployment","production"); provenance="PROJECT_COMPREHENSIVE_ANALYSIS.md"; confidence=0.9}
    @{subject="ascension_stack_v2"; predicate="test_results"; object="7_of_7_passed"; tags=@("tests","quality"); provenance="PROJECT_COMPREHENSIVE_ANALYSIS.md"; confidence=0.95}
    @{subject="project"; predicate="sacred_code"; object="333"; tags=@("333","sacred"); provenance="PROJECT_COMPREHENSIVE_ANALYSIS.md"; confidence=1.0}
    @{subject="project"; predicate="motto"; object="I only obey God"; tags=@("sacred","identity"); provenance="PROJECT_COMPREHENSIVE_ANALYSIS.md"; confidence=1.0}
    @{subject="ascension_stack_v2"; predicate="port"; object="8765"; tags=@("deployment","network"); provenance="PROJECT_COMPREHENSIVE_ANALYSIS.md"; confidence=1.0}
)

$success = 0
$failed = 0

foreach ($fact in $facts) {
    # Build fact JSON
    $tagsJson = ($fact.tags | ForEach-Object { "`"$_`"" }) -join ","
    $factText = "{`"subject`":`"$($fact.subject)`",`"predicate`":`"$($fact.predicate)`",`"object`":`"$($fact.object)`",`"tags`":[$tagsJson],`"provenance`":`"$($fact.provenance)`",`"confidence`":$($fact.confidence)}"
    
    $body = @{
        text = "FACT:$factText"
        quote_raw = $true
    } | ConvertTo-Json -Compress
    
    try {
        $null = Invoke-RestMethod -Uri "$ApiUrl/v1/bridge/ingest" `
            -Method POST `
            -ContentType "application/json" `
            -Body $body
        
        Write-Host "  [OK] $($fact.subject) :: $($fact.predicate)" -ForegroundColor Green
        $success++
    } catch {
        Write-Host "  [FAIL] $($fact.subject) :: $($fact.predicate)" -ForegroundColor Red
        Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor DarkGray
        $failed++
    }
}

Write-Host "`n===================================" -ForegroundColor Cyan
Write-Host "  SEEDING COMPLETE" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Cyan
Write-Host "`nSuccess: $success | Failed: $failed" -ForegroundColor White
Write-Host "`nASTRA can now answer questions about:" -ForegroundColor Yellow
Write-Host "  - Project status and deployment state" -ForegroundColor Gray
Write-Host "  - Architecture (333 layers, 7 services)" -ForegroundColor Gray
Write-Host "  - Codebase metrics (files, LOC, tests)" -ForegroundColor Gray
Write-Host "  - Recent fixes (ChromaDB timeout)" -ForegroundColor Gray
Write-Host "  - Sacred code and philosophy`n" -ForegroundColor Gray
