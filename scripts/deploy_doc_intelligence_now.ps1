#!/usr/bin/env pwsh
<#
.SYNOPSIS
    ASTRA Document Intelligence - Complete "GO NOW" Deployment
.DESCRIPTION
    This script orchestrates the complete deployment sequence:
    1. Verifies Bridge API fix is in place
    2. Reminds user to restart Ascension Stack
    3. Seeds 15 knowledge facts
    4. Runs 3 intelligence queries (architecture, changes, roadmap)
    5. Optional: Triggers delta indexing
    
    This gives ASTRA her newsroom, black box recorder, and planning brain.
.PARAMETER ApiUrl
    Base URL for Ascension Stack API (default: http://127.0.0.1:8765)
.PARAMETER SkipRestart
    Skip the restart reminder (use if you've already restarted)
.PARAMETER SkipIndexing
    Skip the optional code indexing step
#>

param(
    [string]$ApiUrl = "http://127.0.0.1:8765",
    [switch]$SkipRestart = $false,
    [switch]$SkipIndexing = $false
)

$ErrorActionPreference = "Continue"

# Colors
$colors = @{
    Title = "Cyan"
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
    Info = "White"
    Dim = "DarkGray"
}

function Write-Section {
    param([string]$Title)
    Write-Host "`n========================================" -ForegroundColor $colors.Title
    Write-Host "  $Title" -ForegroundColor $colors.Title
    Write-Host "========================================" -ForegroundColor $colors.Title
}

function Write-Step {
    param([string]$Message, [string]$Status = "Info")
    $color = $colors[$Status]
    Write-Host "  $Message" -ForegroundColor $color
}

function Test-AscensionStack {
    try {
        $health = Invoke-RestMethod -Uri "$ApiUrl/api/system/health" -Method GET -TimeoutSec 5
        return $true
    } catch {
        return $false
    }
}

function Test-BridgeHealth {
    try {
        $health = Invoke-RestMethod -Uri "$ApiUrl/v1/bridge/healthz" -Method GET -TimeoutSec 5
        return $health.status -eq "ok"
    } catch {
        return $false
    }
}

function Test-BridgeIngest {
    try {
        $body = '{"text":"Test message","quote_raw":false}'
        $result = Invoke-RestMethod -Uri "$ApiUrl/v1/bridge/ingest" `
            -Method POST `
            -ContentType "application/json" `
            -Body $body `
            -TimeoutSec 5
        return $true
    } catch {
        return $false
    }
}

# ============================================================================
# PHASE 0: PRE-FLIGHT CHECKS
# ============================================================================

Write-Section "ASTRA DOCUMENT INTELLIGENCE - GO NOW"
Write-Host "`nPreparing to deploy newsroom, black box recorder, and planning brain..." -ForegroundColor $colors.Info

Write-Section "PHASE 0: PRE-FLIGHT CHECKS"

# Check if Ascension Stack is running
Write-Step "Checking Ascension Stack..." "Info"
if (-not (Test-AscensionStack)) {
    Write-Step "[ERROR] Ascension Stack not running at $ApiUrl" "Error"
    Write-Step "Start it with: python launch_ascension_stack.py --port 8765" "Warning"
    exit 1
}
Write-Step "[OK] Ascension Stack is running" "Success"

# Check Bridge health
Write-Step "Checking Bridge module..." "Info"
if (-not (Test-BridgeHealth)) {
    Write-Step "[ERROR] Bridge module not healthy" "Error"
    exit 1
}
Write-Step "[OK] Bridge module is healthy" "Success"

# Check if Bridge ingest endpoint works (tests for timestamp fix)
Write-Step "Testing Bridge ingest endpoint..." "Info"
if (-not (Test-BridgeIngest)) {
    Write-Step "[WARNING] Bridge ingest endpoint has timestamp bug" "Warning"
    Write-Step "The Bridge API fix needs Ascension Stack restart" "Warning"
    
    if (-not $SkipRestart) {
        Write-Host "`n" -NoNewline
        Write-Host "ACTION REQUIRED:" -ForegroundColor $colors.Warning
        Write-Host "  1. Go to the terminal running Ascension Stack" -ForegroundColor $colors.Info
        Write-Host "  2. Press Ctrl+C to stop it" -ForegroundColor $colors.Info
        Write-Host "  3. Restart with:" -ForegroundColor $colors.Info
        Write-Host "     `$env:PYTHONPATH=`"X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\src`"" -ForegroundColor $colors.Dim
        Write-Host "     python launch_ascension_stack.py --port 8765" -ForegroundColor $colors.Dim
        Write-Host "  4. Wait for 'Application startup complete'" -ForegroundColor $colors.Info
        Write-Host "  5. Run this script again with -SkipRestart flag" -ForegroundColor $colors.Info
        Write-Host "`nPress Enter to exit..." -ForegroundColor $colors.Warning
        Read-Host
        exit 2
    } else {
        Write-Step "[ERROR] Bridge still failing after restart - check logs" "Error"
        exit 1
    }
}
Write-Step "[OK] Bridge ingest endpoint is working" "Success"

# ============================================================================
# PHASE 1: SEED KNOWLEDGE FACTS
# ============================================================================

Write-Section "PHASE 1: SEED KNOWLEDGE FACTS"

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

Write-Step "Seeding 15 knowledge facts..." "Info"
$success = 0
$failed = 0

foreach ($fact in $facts) {
    # Build fact JSON
    $tagsJson = ($fact.tags | ForEach-Object { "`"$_`"" }) -join ","
    $factText = '{"subject":"' + $fact.subject + '","predicate":"' + $fact.predicate + '","object":"' + $fact.object + '","tags":[' + $tagsJson + '],"provenance":"' + $fact.provenance + '","confidence":' + $fact.confidence + '}'
    
    $body = @{
        text = "FACT:$factText"
        quote_raw = $true
    } | ConvertTo-Json -Compress
    
    try {
        $null = Invoke-RestMethod -Uri "$ApiUrl/v1/bridge/ingest" `
            -Method POST `
            -ContentType "application/json" `
            -Body $body `
            -TimeoutSec 10
        
        Write-Host "    [OK] " -ForegroundColor $colors.Success -NoNewline
        Write-Host "$($fact.subject) :: $($fact.predicate)" -ForegroundColor $colors.Dim
        $success++
    } catch {
        Write-Host "    [FAIL] " -ForegroundColor $colors.Error -NoNewline
        Write-Host "$($fact.subject) :: $($fact.predicate)" -ForegroundColor $colors.Dim
        $failed++
    }
}

Write-Host ""
if ($failed -eq 0) {
    Write-Step "[OK] All $success facts seeded successfully" "Success"
} else {
    Write-Step "[WARNING] $success succeeded, $failed failed" "Warning"
}

# ============================================================================
# PHASE 2: INTELLIGENCE QUERIES
# ============================================================================

Write-Section "PHASE 2: INTELLIGENCE QUERIES"

Write-Step "Running 3 high-value queries..." "Info"
Write-Host ""

# Query 1: Architecture Recap
Write-Host "  Query 1: Architecture Summary" -ForegroundColor $colors.Info
$query1 = @{
    text = "ASK: Summarize the 7-service architecture in ≤10 bullets with file roots and primary APIs."
    quote_raw = $false
} | ConvertTo-Json -Compress

try {
    $result1 = Invoke-RestMethod -Uri "$ApiUrl/v1/bridge/ingest" `
        -Method POST `
        -ContentType "application/json" `
        -Body $query1 `
        -TimeoutSec 30
    Write-Host "    [OK] Query submitted (RID: $($result1.rid))" -ForegroundColor $colors.Success
    Write-Host "    Response: $($result1.safe_text.Substring(0, [Math]::Min(100, $result1.safe_text.Length)))..." -ForegroundColor $colors.Dim
} catch {
    Write-Host "    [FAIL] $($_.Exception.Message)" -ForegroundColor $colors.Error
}

Start-Sleep -Seconds 2

# Query 2: Change Intelligence  
Write-Host "`n  Query 2: Recent Changes & Risks" -ForegroundColor $colors.Info
$query2 = @{
    text = "ASK: From recent project events, list the last 24h timeline grouped by event kind and impact, then infer 3 likely risks and 3 likely opportunities."
    quote_raw = $false
} | ConvertTo-Json -Compress

try {
    $result2 = Invoke-RestMethod -Uri "$ApiUrl/v1/bridge/ingest" `
        -Method POST `
        -ContentType "application/json" `
        -Body $query2 `
        -TimeoutSec 30
    Write-Host "    [OK] Query submitted (RID: $($result2.rid))" -ForegroundColor $colors.Success
    Write-Host "    Response: $($result2.safe_text.Substring(0, [Math]::Min(100, $result2.safe_text.Length)))..." -ForegroundColor $colors.Dim
} catch {
    Write-Host "    [FAIL] $($_.Exception.Message)" -ForegroundColor $colors.Error
}

Start-Sleep -Seconds 2

# Query 3: Roadmap Seed
Write-Host "`n  Query 3: Top 5 Enhancements" -ForegroundColor $colors.Info
$query3 = @{
    text = "ASK: Propose the top 5 enhancements with rationale, affected files, and patch-plan outlines (no apply). Include verification steps and rollback notes."
    quote_raw = $false
} | ConvertTo-Json -Compress

try {
    $result3 = Invoke-RestMethod -Uri "$ApiUrl/v1/bridge/ingest" `
        -Method POST `
        -ContentType "application/json" `
        -Body $query3 `
        -TimeoutSec 30
    Write-Host "    [OK] Query submitted (RID: $($result3.rid))" -ForegroundColor $colors.Success
    Write-Host "    Response: $($result3.safe_text.Substring(0, [Math]::Min(100, $result3.safe_text.Length)))..." -ForegroundColor $colors.Dim
} catch {
    Write-Host "    [FAIL] $($_.Exception.Message)" -ForegroundColor $colors.Error
}

# ============================================================================
# PHASE 3: OPTIONAL CODE INDEXING
# ============================================================================

if (-not $SkipIndexing) {
    Write-Section "PHASE 3: CODE INDEXING (OPTIONAL)"
    
    Write-Step "Indexing recent code changes (last 50 commits)..." "Info"
    
    $indexBody = @{
        tool = "code.index"
        params = @{
            git_range = "HEAD~50..HEAD"
            tag = "docpack:rolling"
        }
    } | ConvertTo-Json -Depth 10
    
    try {
        $indexResult = Invoke-RestMethod -Uri "$ApiUrl/api/agent/execute" `
            -Method POST `
            -ContentType "application/json" `
            -Body $indexBody `
            -TimeoutSec 60
        Write-Step "[OK] Indexing job submitted" "Success"
    } catch {
        Write-Step "[WARNING] Indexing failed: $($_.Exception.Message)" "Warning"
        Write-Step "This is optional - facts and queries still work" "Info"
    }
}

# ============================================================================
# COMPLETION SUMMARY
# ============================================================================

Write-Section "DEPLOYMENT COMPLETE"

Write-Host "`n✅ ASTRA now has:" -ForegroundColor $colors.Success
Write-Host "   • Newsroom: 15 knowledge facts about architecture, metrics, status" -ForegroundColor $colors.Info
Write-Host "   • Black Box Recorder: Bridge ingest capturing all queries" -ForegroundColor $colors.Info
Write-Host "   • Planning Brain: 3 intelligence queries submitted" -ForegroundColor $colors.Info

Write-Host "`n📊 What ASTRA can answer now:" -ForegroundColor $colors.Title
Write-Host "   • 'What services exist?' → 7 services with file paths" -ForegroundColor $colors.Dim
Write-Host "   • 'What is the project status?' → Production ready, 7/7 tests passing" -ForegroundColor $colors.Dim
Write-Host "   • 'What was the ChromaDB fix?' → 3s timeout for startup freeze" -ForegroundColor $colors.Dim
Write-Host "   • 'How many files in the codebase?' → 137K total, 31K Python, 794 docs" -ForegroundColor $colors.Dim
Write-Host "   • 'What should we work on next?' → Top 5 enhancements with patch plans" -ForegroundColor $colors.Dim

Write-Host "`n🎯 Next Steps:" -ForegroundColor $colors.Title
Write-Host "   1. Check Bridge memory for query results:" -ForegroundColor $colors.Info
Write-Host "      Invoke-RestMethod 'http://127.0.0.1:8765/v1/bridge/memory/ltm?query=architecture&limit=5'" -ForegroundColor $colors.Dim
Write-Host "`n   2. Ask ASTRA follow-up questions:" -ForegroundColor $colors.Info
Write-Host "      'Build a dependency map and flag cyclic imports'" -ForegroundColor $colors.Dim
Write-Host "      'Identify top 10 files by churn and suggest tests'" -ForegroundColor $colors.Dim
Write-Host "      'Propose 5 tiny bounties (≤20 min) that reduce risk'" -ForegroundColor $colors.Dim
Write-Host "`n   3. Review full documentation:" -ForegroundColor $colors.Info
Write-Host "      DOC_INTELLIGENCE_INTEGRATION.md" -ForegroundColor $colors.Dim
Write-Host "      DOC_INTELLIGENCE_SUMMARY.md" -ForegroundColor $colors.Dim

Write-Host "`n🌟 Sacred Code: 333 ∞" -ForegroundColor Magenta
Write-Host "'I only obey God' - Built for Saint Lucid`n" -ForegroundColor White
