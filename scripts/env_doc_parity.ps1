# scripts/env_doc_parity.ps1
# Ensures environment variables in docs exist in .env.example

param([string]$Root = (Resolve-Path ".").Path)

$envExample = Join-Path $Root ".env.example"
if (-not (Test-Path $envExample)) {
  Write-Host "[WARN] .env.example not found" -ForegroundColor Yellow
  exit 0
}

$envVars = @{}
Get-Content $envExample | ForEach-Object {
  if ($_ -match '^([A-Z_]+)=') {
    $envVars[$Matches[1]] = $true
  }
}

$mds = Get-ChildItem $Root -Recurse -Filter *.md |
  Where-Object {
    $_.FullName -notmatch '\\(node_modules|\.git|\.venv|venv|__pycache__|htmlcov|dist|build|site|_site|third_party|astra-local|hf_cache|\.hf_cache|\.cache)\\'
  }

$docVars = @{}
foreach ($md in $mds) {
  try {
    $content = Get-Content $md.FullName -Raw -ErrorAction SilentlyContinue
    if ($content) {
      $varMatches = [regex]::Matches($content, '\bASTRA_[A-Z_]+\b')
      foreach ($m in $varMatches) {
        $docVars[$m.Value] = $true
      }
    }
  }
  catch {
    # Skip files that can't be read
  }
}

$missing = @()
foreach ($var in $docVars.Keys) {
  if (-not $envVars.ContainsKey($var)) {
    $missing += $var
  }
}

if ($missing) {
  Write-Host "[WARN] Variables in docs but not in .env.example:" -ForegroundColor Yellow
  $missing | Sort-Object | ForEach-Object { Write-Host "  * $_" -ForegroundColor Yellow }
  exit 0
}

Write-Host "[OK] Environment variable parity check complete" -ForegroundColor Green
exit 0