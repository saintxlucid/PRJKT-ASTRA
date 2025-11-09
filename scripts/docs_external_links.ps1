# scripts/docs_external_links.ps1
# External link sanity check - warn only, never fail
# Non-blocking probe with retries + timeout to avoid CI flakiness

[CmdletBinding()]
param(
  [string]$Root = (Resolve-Path ".").Path,
  [int]$TimeoutSeconds = 5,
  [int]$Retries = 2
)

Write-Host "`n==== External Link Sanity Check ====" -ForegroundColor Cyan
Write-Host "Checking external links (warn only, non-blocking)...`n" -ForegroundColor Yellow

$mds = Get-ChildItem $Root -Recurse -Filter *.md |
  Where-Object {
    $_.FullName -notmatch '\\(node_modules|\.git|\.venv|venv|__pycache__|htmlcov|dist|build|site|_site|third_party|astra-local|hf_cache|\.hf_cache|\.cache)\\'
  }

# Extract all external links (http/https)
$externalLinks = @{}
foreach ($md in $mds) {
  try {
    $content = Get-Content $md.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    if ($content) {
      $linkPattern = '\[([^\]]+)\]\(([^)]+)\)'
      $matches = [regex]::Matches($content, $linkPattern)
      
      foreach ($m in $matches) {
        $url = $m.Groups[2].Value
        if ($url -match '^https?://') {
          if (-not $externalLinks.ContainsKey($url)) {
            $externalLinks[$url] = @()
          }
          $externalLinks[$url] += $md.Name
        }
      }
    }
  }
  catch {
    # Skip files that can't be read
  }
}

if ($externalLinks.Count -eq 0) {
  Write-Host "[INFO] No external links found to check" -ForegroundColor Cyan
  exit 0
}

Write-Host "[INFO] Found $($externalLinks.Count) unique external URLs" -ForegroundColor Cyan

# Check each external link with retries
$results = @()
$slow = @()
$broken = @()

foreach ($url in $externalLinks.Keys | Select-Object -First 20) {
  $attempt = 0
  $success = $false
  $duration = 0
  
  while ($attempt -lt $Retries -and -not $success) {
    $attempt++
    try {
      $start = Get-Date
      $response = Invoke-WebRequest -Uri $url -Method Head -TimeoutSec $TimeoutSeconds -UseBasicParsing -ErrorAction Stop
      $duration = ((Get-Date) - $start).TotalMilliseconds
      $success = $true
      
      if ($duration -gt 2000) {
        $slow += [PSCustomObject]@{
          URL = $url
          Duration = [math]::Round($duration)
          Files = ($externalLinks[$url] | Select-Object -First 3) -join ", "
        }
      }
    }
    catch {
      if ($attempt -eq $Retries) {
        $broken += [PSCustomObject]@{
          URL = $url
          Error = $_.Exception.Message.Split("`n")[0]
          Files = ($externalLinks[$url] | Select-Object -First 3) -join ", "
        }
      }
      Start-Sleep -Milliseconds 500
    }
  }
}

# Report findings
Write-Host "`n[RESULTS]" -ForegroundColor Cyan

if ($slow.Count -gt 0) {
  Write-Host "`nSlow External Links (>2s):" -ForegroundColor Yellow
  $slow | Format-Table -AutoSize -Wrap
}

if ($broken.Count -gt 0) {
  Write-Host "`nBroken/Unreachable External Links:" -ForegroundColor Yellow
  $broken | Format-Table -AutoSize -Wrap
  Write-Host "[WARN] $($broken.Count) external links may be broken (non-blocking)" -ForegroundColor Yellow
}

if ($slow.Count -eq 0 -and $broken.Count -eq 0) {
  Write-Host "[OK] All sampled external links are healthy" -ForegroundColor Green
}

Write-Host "`n[INFO] External link check complete (warn-only mode)" -ForegroundColor Cyan
exit 0
