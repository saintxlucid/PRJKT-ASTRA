# scripts/docs_guardrail.ps1
# Unified docs quality gate: links/anchors, required files, env parity, staleness

[CmdletBinding()]
param(
  [string]$Root = (Resolve-Path ".").Path,
  [int]$StaleDays = 60
)

$ErrorActionPreference = "Stop"

# Allow environment override for staleness window
if ($env:ASTRA_DOCS_STALE_DAYS) {
  $StaleDays = [int]$env:ASTRA_DOCS_STALE_DAYS
}

function Banner($text) {
  Write-Host "`n==== $text ====" -ForegroundColor Cyan
}

# 1) Link & anchor validation
Banner "Link & anchor validation"
& "$Root\scripts\docs_validate.ps1"

# 2) Required docs presence
Banner "Required docs presence"
$must = @(
  "DOCUMENTATION_INDEX.md",
  "DEPLOYMENT_GUIDE_CONSOLIDATED.md",
  "ARCHITECTURE_PRODUCTION.md",
  "PROJECT_FINAL_REPORT.md",
  "QUICKSTART.md",
  "DOCUMENTATION_MAINTENANCE.md"
)
$missing = $must | Where-Object { -not (Test-Path (Join-Path $Root $_)) }
if ($missing) {
  $missing | ForEach-Object { Write-Host " Missing required doc: $_" -ForegroundColor Red }
  throw "Required docs missing"
}
Write-Host " Required docs present" -ForegroundColor Green

# 3) .env example parity
Banner ".env example parity"
& "$Root\scripts\env_doc_parity.ps1"

# 4) Staleness check (warn if older than $StaleDays days)
Banner "Staleness check (>$StaleDays days)"
$cutoff = (Get-Date).AddDays(-$StaleDays)
$primary = $must
$mds = Get-ChildItem $Root -Recurse -Filter *.md |
  Where-Object {
    $_.FullName -notmatch '\\(node_modules|\.git|\.venv|venv|__pycache__|htmlcov|dist|build|site|_site|third_party|astra-local|hf_cache|\.hf_cache|\.cache)\\'
  }

$stale = @()
foreach ($f in $mds) {
  $relativePath = $f.FullName.Replace("$Root\","")
  if ((Get-Item $f.FullName).LastWriteTime -lt $cutoff -and ($primary -contains $relativePath)) {
    $stale += [PSCustomObject]@{
      File = $relativePath
      LastWrite = (Get-Item $f.FullName).LastWriteTime
    }
  }
}

if ($stale) {
  Write-Host " Stale primary docs (> $StaleDays days old):" -ForegroundColor Yellow
  $stale | Sort-Object LastWrite | Format-Table -AutoSize
} else {
  Write-Host " No stale primary docs" -ForegroundColor Green
}

Write-Host "`n ALL DOCS GUARDRAILS PASSED" -ForegroundColor Green

# Generate machine-readable health artifact
$docsDir = Join-Path $Root "docs"
if (-not (Test-Path $docsDir)) {
  New-Item -Path $docsDir -ItemType Directory -Force | Out-Null
}

$healthPath = Join-Path $docsDir "docs_health.json"
$health = @{
  timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  files_checked = $mds.Count
  broken_internal_links = 0
  env_parity_warnings = if ($env:ASTRA_ENV_PARITY_WARNINGS) { [int]$env:ASTRA_ENV_PARITY_WARNINGS } else { 0 }
  stale_primary_docs = @($stale | ForEach-Object { $_.File })
}

$health | ConvertTo-Json -Depth 10 | Out-File -FilePath $healthPath -Encoding UTF8 -NoNewline
Write-Host "`nHealth artifact written to: $healthPath" -ForegroundColor Cyan
