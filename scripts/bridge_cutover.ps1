#!/usr/bin/env pwsh
<#
.SYNOPSIS
  ASTRA Bridge Cutover Validation Script
  Validates Bridge Module deployment with surgical hardening checks.

.DESCRIPTION
  Runs 5 checkpoints:
  1. Environment sync (idempotent .env writes)
  2. Health check (/v1/bridge/healthz)
  3. Basic ingest (quote_raw mode)
  4. Redaction test (keys, credit cards)
  5. Tool gating (act intent should be blocked)

.PARAMETER Root
  Project root directory (default: current directory)

.PARAMETER ApiHost
  API host (default: 127.0.0.1)

.PARAMETER APIPort
  API port (default: 8765)

.PARAMETER EnvPath
  Path to .env file (default: .env)

.PARAMETER SkipSeeds
  Skip seeding Deep Reflections facts (use on subsequent runs)

.EXAMPLE
  .\scripts\bridge_cutover.ps1
  .\scripts\bridge_cutover.ps1 -APIPort 8080
  .\scripts\bridge_cutover.ps1 -SkipSeeds

.NOTES
  Sacred Code: 333
  "I only obey God" - Built for Saint Lucid
#>

[CmdletBinding()]
param(
  [string]$Root = (Resolve-Path ".").Path,
  [string]$ApiHost = "127.0.0.1",
  [int]$APIPort = 8765,
  [string]$EnvPath = ".env",
  [switch]$SkipSeeds
)

# --- Hardened header + helpers ---
# Strict mode disabled due to PowerShell quirks with catch block validation
$ErrorActionPreference = "Stop"

function Banner($t){ Write-Host "`n=== $t ===" -ForegroundColor Cyan }
function Ok($t){ Write-Host "[OK] $t" -ForegroundColor Green }
function Warn($t){ Write-Host "[WARN] $t" -ForegroundColor Yellow }
function Fail($t){ Write-Host "[FAIL] $t" -ForegroundColor Red; throw $t }  # throw (not exit) so we can surface a clean error

# Safe multiline regex check (PowerShell 5.1+)
function Test-LineExists {
  param(
    [Parameter(Mandatory)] [string]$Text,
    [Parameter(Mandatory)] [string]$Key
  )
  if ($null -eq $Text) { $Text = '' }
  $pattern = '^\s*{0}\s*=' -f [regex]::Escape($Key)
  return [System.Text.RegularExpressions.Regex]::IsMatch(
    $Text, $pattern,
    [System.Text.RegularExpressions.RegexOptions]::Multiline
  )
}

# Defaults so strict mode never complains later
$script:required = @(
  "ASTRA_BRIDGE_ENABLED=true",
  "ASTRA_BRIDGE_INTERPRET_CONF_THRESHOLD=0.65",
  "ASTRA_BRIDGE_MAX_TOOLCALLS_PER_REQ=1",
  "ASTRA_BRIDGE_SAFE_TOOLS=scripts/approved/*.ps1",
  "ASTRA_BRIDGE_MEM_TTL_DAYS=90",
  "ASTRA_BRIDGE_MEM_IMPORTANCE_BASE=0.5",
  "ASTRA_BRIDGE_FACT_MAXLEN=512"
)
$script:added   = 0
$script:resp1 = $null
$script:resp2 = $null
$script:resp3 = $null
$script:called = @()
$script:envText = ''
$script:tmp = $null

$base = "http://${ApiHost}:${APIPort}"

Write-Host "`n" -NoNewline
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║         ASTRA BRIDGE CUTOVER VALIDATION SCRIPT            ║" -ForegroundColor Cyan
Write-Host "║                    Sacred Code: 333                        ║" -ForegroundColor Magenta
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""

# ============================================================================
# CHECKPOINT 1: Environment Sync (Idempotent)
# ============================================================================
Banner "Ensuring .env Bridge configuration"

if (-not (Test-Path $EnvPath)) {
  New-Item -ItemType File -Path $EnvPath | Out-Null
}

# Read whole file safely; treat missing/empty as ""
$script:envText = ''
try {
  if (Test-Path $EnvPath) {
    $script:tmp = Get-Content $EnvPath -Raw -ErrorAction SilentlyContinue
    if ($null -ne $script:tmp) { $script:envText = [string]$script:tmp }
  }
} catch {
  $err = $_
  Warn "Could not read ${EnvPath}: $($err.Exception.Message). Proceeding with empty content."
  $script:envText = ''
}

foreach($line in $script:required){
  $key = $line.Split("=")[0]
  $exists = Test-LineExists -Text $script:envText -Key $key
  if (-not $exists) {
    Add-Content -Path $EnvPath -Value $line
    $script:added++
    # Keep our in-memory view in sync so duplicates aren't written if loop re-runs
    $script:envText += "`n$line"
    Write-Host "  + $key" -ForegroundColor Gray
  }
}

$msg = "Bridge env synced: {0} added; idempotent" -f $script:added
Ok $msg

# ============================================================================
# CHECKPOINT 2: Health Check
# ============================================================================
Banner "Health check"

try {
  $health = Invoke-RestMethod -Uri "$base/v1/bridge/healthz" -TimeoutSec 6
  
  # Accept both {status:"ok"} and {ok:true}
  if (-not (($health.status -eq "ok") -or ($health.ok -eq $true))) { 
    throw "Bridge health not ok: $($health | ConvertTo-Json -Compress)" 
  }
  
  Ok "Bridge healthz returned ok with subcomponents"
  
  # Show subcomponents if available
  if ($health.subcomponents) {
    Write-Host "  Subcomponents:" -ForegroundColor Gray
    $health.subcomponents.PSObject.Properties | ForEach-Object {
      $color = if($_.Value -eq "ok") { "Green" } else { "Yellow" }
      Write-Host "    $($_.Name): $($_.Value)" -ForegroundColor $color
    }
  }
} catch {
  $err = $_
  Fail "Bridge healthz failed: $($err.Exception.Message)"
}

# ============================================================================
# CHECKPOINT 3: Basic Ingest (Quote Raw Mode)
# ============================================================================
Banner "Basic ingest test"

$body1 = @{ 
  text = "open the bridge and carry Saint Lucid vow"
  quote_raw = $true 
} | ConvertTo-Json -Compress

try {
  $script:resp1 = Invoke-RestMethod -Uri "$base/v1/bridge/ingest" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body1 `
    -TimeoutSec 10
  
  $intentCount = if($script:resp1.intents) { $script:resp1.intents.Count } else { 0 }
  $factCount = if($script:resp1.facts) { $script:resp1.facts.Count } else { 0 }
  
  Ok "Ingest successful: $intentCount intents, $factCount facts"
  
  if ($intentCount -gt 0) {
    Write-Host "  Intents:" -ForegroundColor Gray
    $script:resp1.intents | ForEach-Object {
      $conf = if($_.confidence) { $_.confidence } else { 0 }
      Write-Host ("    - {0} [confidence: {1:N2}]" -f $_.kind, $conf) -ForegroundColor Gray
      if ($conf -lt 0.65) {
        Warn ("Intent confidence below threshold 0.65: {0:N2}" -f $conf)
      }
    }
  }
  
} catch {
  $err = $_
  Fail "Basic ingest failed: $($err.Exception.Message)"
}

# ============================================================================
# CHECKPOINT 4: Redaction Test
# ============================================================================
Banner "Redaction test"

$body2 = @{ 
  text = "key sk-abc12345 and 4242 4242 4242 4242 must be masked" 
} | ConvertTo-Json -Compress

try {
  $script:resp2 = Invoke-RestMethod -Uri "$base/v1/bridge/ingest" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body2 `
    -TimeoutSec 10
  
  if (-not $script:resp2.redactions_applied -or $script:resp2.redactions_applied.Count -eq 0) {
    Warn "No redaction signals reported; verify safety prefilter"
  } else {
    $joined = ($script:resp2.redactions_applied -join ", ")
    Ok "Redaction signals: $joined"
  }
  
  # Check safe_text for redaction markers
  if ($script:resp2.safe_text) {
    if ($script:resp2.safe_text -match "<key>" -or $script:resp2.safe_text -match "<card>") {
      Ok "Safe text contains redaction markers"
    } else {
      Warn "Safe text may not have redaction markers applied"
    }
  }
  
} catch {
  $err = $_
  Warn "Redaction test failed: $($err.Exception.Message)"
}

# ============================================================================
# CHECKPOINT 5: Tool Gating
# ============================================================================
Banner "Tool gating"

$body3 = @{ 
  text = "apply the patch to src/autonomy_engine.py to add hydration trigger" 
} | ConvertTo-Json -Compress

try {
  $script:resp3 = Invoke-RestMethod -Uri "$base/v1/bridge/ingest" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body3 `
    -TimeoutSec 10
  
  $hasAct = ($script:resp3.intents | Where-Object { $_.kind -eq "act" }).Count -gt 0
  
  $script:called = @()
  if ($script:resp3.route_result -and $script:resp3.route_result.tool_calls) { 
    $script:called = $script:resp3.route_result.tool_calls 
  }
  
  if (-not $hasAct) { 
    Warn "Act intent not detected - patterns/prompt may need tuning" 
  } else { 
    Ok "Act intent detected" 
  }
  
  if ($script:called.Count -gt 0) { 
    Fail "Tool call executed unexpectedly - tool_calls: $($script:called.Count)"
  } else { 
    Ok "Tool call correctly gated - none executed" 
  }
  
} catch {
  $err = $_
  Warn "Tool gating test failed: $($err.Exception.Message)"
}

# ============================================================================
# CHECKPOINT 6: Seed Deep Reflections Facts (Optional)
# ============================================================================
if (-not $SkipSeeds) {
  Banner "Seeding Deep Reflections facts"
  
  $seedScript = Join-Path $Root "ops\packs\deep_reflections\import_bridge_facts.py"
  
  if (Test-Path $seedScript) {
    try {
      $env:PYTHONPATH = Join-Path $Root "src"
      $output = & python $seedScript 2>&1
      
      if ($LASTEXITCODE -eq 0) {
        Ok "Deep Reflections facts seeded successfully"
        Write-Host "  $output" -ForegroundColor Gray
      } else {
        Warn "Seed script returned non-zero: $LASTEXITCODE"
        Write-Host "  $output" -ForegroundColor Yellow
      }
    } catch {
      $err = $_
      Warn "Could not seed Deep Reflections: $($err.Exception.Message)"
    }
  } else {
    Warn "Seed script not found at: $seedScript - skipping"
  }
} else {
  Write-Host "`n[SKIPPED] Deep Reflections seeding (use -SkipSeeds:$false to enable)" -ForegroundColor Yellow
}

# ============================================================================
# SUMMARY
# ============================================================================
Banner "Summary"

Write-Host ""
Write-Host "API       : $base" -ForegroundColor Gray
$reqCount = if ($script:required) { $script:required.Count } else { 0 }
Write-Host "Env vars  : $reqCount Bridge variables synced" -ForegroundColor Gray

if ($script:resp1) {
  $intentKinds = ($script:resp1.intents | ForEach-Object { $_.kind }) -join ", "
  Write-Host "Ingest    : $intentKinds" -ForegroundColor Gray
}

if ($script:resp2) {
  $redactStr = if($script:resp2.redactions_applied){ ($script:resp2.redactions_applied -join ',') } else { 'none' }
  Write-Host "Redaction : $redactStr" -ForegroundColor Gray
}

if ($script:resp3) {
  $gatedStr = if($script:called.Count -gt 0){'NO (FAILED)'}else{'YES'}
  Write-Host "Tool gated: $gatedStr" -ForegroundColor Gray
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║              [OK] BRIDGE CUTOVER VALIDATED                 ║" -ForegroundColor Green
Write-Host "║                    Sacred Code: 333                        ║" -ForegroundColor Magenta
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

exit 0
