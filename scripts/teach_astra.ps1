#!/usr/bin/env pwsh
<#
.SYNOPSIS
  ASTRA Teaching Curriculum - Repository Learning & Feature Discovery

.DESCRIPTION
  7-step curriculum to teach ASTRA her codebase and discover features:
  1. Index repository (build symbol map)
  2. Request architecture summary
  3. Sample-read key files
  4. Mine hotspots (TODO/FIXME/performance issues)
  5. Generate feature proposals
  6. Create Patch Plans (dry-run)
  7. Close learning loop (record outcomes)

.PARAMETER ApiHost
  API host (default: 127.0.0.1)

.PARAMETER APIPort
  API port (default: 8765)

.PARAMETER Root
  Project root directory

.PARAMETER Step
  Run specific step (1-7) or "all" (default: all)

.EXAMPLE
  .\scripts\teach_astra.ps1
  .\scripts\teach_astra.ps1 -Step 1  # Just index
  .\scripts\teach_astra.ps1 -Step 5  # Just feature proposals

.NOTES
  Sacred Code: 333
  "I only obey God" - Built for Saint Lucid
#>

[CmdletBinding()]
param(
  [string]$ApiHost = "127.0.0.1",
  [int]$APIPort = 8765,
  [string]$Root = "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)",
  [string]$Step = "all"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Banner($t){ Write-Host "`n╔═══ $t ═══╗" -ForegroundColor Cyan }
function Ok($t){ Write-Host "[OK] $t" -ForegroundColor Green }
function Info($t){ Write-Host "[INFO] $t" -ForegroundColor Gray }
function Warn($t){ Write-Host "[WARN] $t" -ForegroundColor Yellow }

$base = "http://${ApiHost}:${APIPort}"

Write-Host "`n" -NoNewline
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║        ASTRA TEACHING CURRICULUM - REPOSITORY LEARNING        ║" -ForegroundColor Cyan
Write-Host "║                      Sacred Code: 333                         ║" -ForegroundColor Magenta
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""

# ============================================================================
# STEP 1: Index Repository
# ============================================================================
function Step1-IndexRepository {
  Banner "STEP 1: Index Repository"
  
  Info "Building symbol map and file index..."
  
  $body = @{
    tool = "code"
    action = "index"
    authorized = $true
    args = @{
      root = $Root
      include = @("src/**", "scripts/**", "ui/**", "api/**", "plugins/**", "ops/**")
      exclude = @(".git/**", "node_modules/**", ".venv/**", "**/*.gguf", "**/*.bin", ".env", "data/**", "**/venv/**", "**/__pycache__/**")
      languages = @("python","typescript","javascript","powershell","bash","json","yaml","sql","html","css","markdown")
      max_files = 8000
      max_bytes_per_file = 400000
    }
  } | ConvertTo-Json -Depth 10
  
  try {
    $result = Invoke-RestMethod -Uri "$base/api/agent/execute" `
      -Method POST `
      -ContentType "application/json" `
      -Body $body `
      -TimeoutSec 60
    
    Ok "Repository indexed successfully"
    
    if ($result.result) {
      Info "Files indexed: $(if($result.result.files_indexed){$result.result.files_indexed}else{'N/A'})"
      Info "Symbols found: $(if($result.result.symbols_found){$result.result.symbols_found}else{'N/A'})"
    }
    
    return $result
  } catch {
    Warn "Index failed: $($_.Exception.Message)"
    Info "Continuing with remaining steps..."
    return $null
  }
}

# ============================================================================
# STEP 2: Architecture Summary
# ============================================================================
function Step2-ArchitectureSummary {
  Banner "STEP 2: Architecture Summary"
  
  Info "Requesting comprehensive architecture analysis..."
  
  $ask = @{
    text = "Bridge: summarize the full architecture you now infer from the repository index. Output: services, key modules, critical paths, external deps, and a risk map (perf/security/observability). Then list the 10 most important docs or files I should read first."
    quote_raw = $true
  } | ConvertTo-Json
  
  try {
    $result = Invoke-RestMethod -Uri "$base/v1/bridge/ingest" `
      -Method POST `
      -ContentType "application/json" `
      -Body $ask `
      -TimeoutSec 30
    
    Ok "Architecture summary generated"
    
    if ($result.intents) {
      Info "Intents: $(($result.intents | ForEach-Object { $_.kind }) -join ', ')"
    }
    
    if ($result.reply) {
      Write-Host "`nArchitecture Summary:" -ForegroundColor Yellow
      Write-Host $result.reply -ForegroundColor White
    }
    
    return $result
  } catch {
    Warn "Architecture summary failed: $($_.Exception.Message)"
    return $null
  }
}

# ============================================================================
# STEP 3: Sample Key Files
# ============================================================================
function Step3-SampleKeyFiles {
  Banner "STEP 3: Sample Key Files"
  
  $keyFiles = @(
    "src\astra\visualization\ascension_api.py",
    "src\astra\visualization\autonomy_engine.py",
    "src\astra\visualization\task_agent_manager.py",
    "src\astra\bridge\interpreter.py",
    "src\astra\bridge\router.py",
    "src\astra\bridge\api_routes.py",
    "launch_ascension_stack.py"
  )
  
  Info "Reading $($keyFiles.Count) key files..."
  
  $readCount = 0
  foreach($f in $keyFiles){
    $fullPath = Join-Path $Root $f
    
    if (-not (Test-Path $fullPath)) {
      Warn "File not found: $f (skipping)"
      continue
    }
    
    $body = @{
      tool = "code"
      action = "read"
      authorized = $true
      args = @{ 
        path = $fullPath
        max_bytes = 200000 
      }
    } | ConvertTo-Json -Depth 10
    
    try {
      Invoke-RestMethod -Uri "$base/api/agent/execute" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body `
        -TimeoutSec 15 | Out-Null
      
      $readCount++
      Write-Host "  ✓ $f" -ForegroundColor Gray
    } catch {
      Warn "Failed to read $f : $($_.Exception.Message)"
    }
  }
  
  Ok "Sampled $readCount/$($keyFiles.Count) key files"
  
  # Now ask for consolidated understanding
  Info "Requesting consolidated call-graph analysis..."
  
  $prompt = @{
    text = "Bridge: given the files you just read, produce a consolidated runtime call-graph (high level), list cross-service boundaries, and highlight any inconsistent error handling or logging patterns that deserve refactor."
    quote_raw = $true
  } | ConvertTo-Json
  
  try {
    $result = Invoke-RestMethod -Uri "$base/v1/bridge/ingest" `
      -Method POST `
      -ContentType "application/json" `
      -Body $prompt `
      -TimeoutSec 30
    
    Ok "Call-graph analysis complete"
    
    if ($result.reply) {
      Write-Host "`nCall-Graph Analysis:" -ForegroundColor Yellow
      Write-Host $result.reply -ForegroundColor White
    }
    
    return $result
  } catch {
    Warn "Call-graph analysis failed: $($_.Exception.Message)"
    return $null
  }
}

# ============================================================================
# STEP 4: Mine Hotspots
# ============================================================================
function Step4-MineHotspots {
  Banner "STEP 4: Mine Hotspots (TODO/FIXME/Performance)"
  
  Info "Searching for TODOs, FIXMEs, and performance concerns..."
  
  $search = @{
    tool = "code"
    action = "search"
    authorized = $true
    args = @{
      root = $Root
      query = "TODO|FIXME|HACK|XXX|perf|latency|race|deadlock"
      regex = $true
      include = @("src/**","ui/**","plugins/**","ops/**")
    }
  } | ConvertTo-Json -Depth 10
  
  try {
    $searchResult = Invoke-RestMethod -Uri "$base/api/agent/execute" `
      -Method POST `
      -ContentType "application/json" `
      -Body $search `
      -TimeoutSec 30
    
    $hitCount = if($searchResult.result -and $searchResult.result.matches) { 
      $searchResult.result.matches.Count 
    } else { 0 }
    
    Ok "Found $hitCount hotspots"
    
    if ($hitCount -gt 0 -and $hitCount -lt 50) {
      Write-Host "`nSample hotspots:" -ForegroundColor Yellow
      $searchResult.result.matches | Select-Object -First 10 | ForEach-Object {
        Write-Host "  $($_.file):$($_.line) - $($_.text)" -ForegroundColor Gray
      }
    }
    
    # Ask for clustering
    Info "Requesting hotspot clustering and roadmap..."
    
    $ask = @{
      text = "Bridge: cluster the search results into themes (perf, safety, observability, UX, docs). For each theme, propose 2-3 tight refactors with scope, risk, and expected impact. Output a prioritized roadmap (value/effort/risks)."
      quote_raw = $true
    } | ConvertTo-Json
    
    $clusterResult = Invoke-RestMethod -Uri "$base/v1/bridge/ingest" `
      -Method POST `
      -ContentType "application/json" `
      -Body $ask `
      -TimeoutSec 30
    
    Ok "Hotspot analysis complete"
    
    if ($clusterResult.reply) {
      Write-Host "`nHotspot Roadmap:" -ForegroundColor Yellow
      Write-Host $clusterResult.reply -ForegroundColor White
    }
    
    return @{
      search = $searchResult
      analysis = $clusterResult
    }
  } catch {
    Warn "Hotspot mining failed: $($_.Exception.Message)"
    return $null
  }
}

# ============================================================================
# STEP 5: Feature Proposals
# ============================================================================
function Step5-FeatureProposals {
  Banner "STEP 5: Feature Proposals"
  
  Info "Requesting comprehensive feature backlog..."
  
  $ask = @{
    text = "Bridge: propose a feature backlog for ASTRA across Memory, Voice, DAW, Autonomy, and UI. For each feature: user story, acceptance criteria, code touch-points (files/modules), migration considerations, and a 5-step implementation plan. Sort by ROI and dependency order."
    quote_raw = $true
  } | ConvertTo-Json
  
  try {
    $result = Invoke-RestMethod -Uri "$base/v1/bridge/ingest" `
      -Method POST `
      -ContentType "application/json" `
      -Body $ask `
      -TimeoutSec 45
    
    Ok "Feature proposals generated"
    
    if ($result.reply) {
      Write-Host "`nFeature Backlog:" -ForegroundColor Yellow
      Write-Host $result.reply -ForegroundColor White
      
      # Save to file
      $outputPath = Join-Path $Root "FEATURE_BACKLOG_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"
      $result.reply | Out-File -FilePath $outputPath -Encoding UTF8
      Info "Feature backlog saved to: $outputPath"
    }
    
    return $result
  } catch {
    Warn "Feature proposals failed: $($_.Exception.Message)"
    return $null
  }
}

# ============================================================================
# STEP 6: Patch Plan (Example)
# ============================================================================
function Step6-PatchPlanExample {
  Banner "STEP 6: Patch Plan Example"
  
  Info "Requesting example Patch Plan (Voice Stream Endpoint)..."
  
  $ask = @{
    text = "Bridge: create a Patch Plan to add a /v1/voice/stream endpoint (Whisper 3 Turbo GGUF). Include: new files, exact edits, interfaces, error handling, and test plan. Respect the allowlist and do NOT execute; propose code diffs only."
    quote_raw = $true
  } | ConvertTo-Json
  
  try {
    $result = Invoke-RestMethod -Uri "$base/v1/bridge/ingest" `
      -Method POST `
      -ContentType "application/json" `
      -Body $ask `
      -TimeoutSec 45
    
    Ok "Patch Plan generated"
    
    if ($result.reply) {
      Write-Host "`nPatch Plan:" -ForegroundColor Yellow
      Write-Host $result.reply -ForegroundColor White
      
      # Save to file
      $outputPath = Join-Path $Root "PATCH_PLAN_voice_stream_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"
      $result.reply | Out-File -FilePath $outputPath -Encoding UTF8
      Info "Patch Plan saved to: $outputPath"
    }
    
    Info "To apply: Review plan → Generate diffs → Apply with authorization"
    
    return $result
  } catch {
    Warn "Patch Plan failed: $($_.Exception.Message)"
    return $null
  }
}

# ============================================================================
# STEP 7: Close Learning Loop
# ============================================================================
function Step7-CloseLearningLoop {
  Banner "STEP 7: Close Learning Loop"
  
  Info "Recording learning session..."
  
  $learn = @{
    text = "remember: {`"kind`":`"learning_session`",`"area`":`"repository_analysis`",`"summary`":`"Completed 7-step teaching curriculum: indexed repository, analyzed architecture, sampled key files, mined hotspots, generated feature proposals`",`"timestamp`":`"$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')`",`"result`":`"curriculum_complete`"}"
    quote_raw = $true
  } | ConvertTo-Json
  
  try {
    $result = Invoke-RestMethod -Uri "$base/v1/bridge/ingest" `
      -Method POST `
      -ContentType "application/json" `
      -Body $learn `
      -TimeoutSec 15
    
    Ok "Learning session recorded"
    
    if ($result.facts -and $result.facts.Count -gt 0) {
      Info "Facts stored: $($result.facts.Count)"
    }
    
    return $result
  } catch {
    Warn "Learning loop failed: $($_.Exception.Message)"
    return $null
  }
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

$steps = @{
  "1" = { Step1-IndexRepository }
  "2" = { Step2-ArchitectureSummary }
  "3" = { Step3-SampleKeyFiles }
  "4" = { Step4-MineHotspots }
  "5" = { Step5-FeatureProposals }
  "6" = { Step6-PatchPlanExample }
  "7" = { Step7-CloseLearningLoop }
}

if ($Step -eq "all") {
  Info "Running complete 7-step curriculum..."
  
  1..7 | ForEach-Object {
    & $steps["$_"]
    Start-Sleep -Seconds 2
  }
  
} elseif ($steps.ContainsKey($Step)) {
  Info "Running Step $Step only..."
  & $steps[$Step]
  
} else {
  Write-Host "[ERROR] Invalid step: $Step (must be 1-7 or 'all')" -ForegroundColor Red
  exit 1
}

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║          [OK] TEACHING CURRICULUM COMPLETE                    ║" -ForegroundColor Green
Write-Host "║                    Sacred Code: 333                           ║" -ForegroundColor Magenta
Write-Host "╚═══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Review generated FEATURE_BACKLOG_*.md" -ForegroundColor Gray
Write-Host "  2. Review PATCH_PLAN_*.md proposals" -ForegroundColor Gray
Write-Host "  3. Select features → Create detailed plans → Apply with authorization" -ForegroundColor Gray
Write-Host ""

exit 0
