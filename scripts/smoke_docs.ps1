Param(
  [string]$ApiKey = $env:BRIDGE_API_KEY,
  [string]$Pdf = "docs-sample\sample.pdf",
  [string]$BaseUrl = "http://localhost:8777"
)

Write-Host "[*] ASTRA Docs smoke test" -ForegroundColor Cyan
if (-not $ApiKey) { Write-Host "[X] Missing ApiKey. Pass -ApiKey or set BRIDGE_API_KEY env var." -ForegroundColor Red; exit 1 }

try {
  $resp = Invoke-WebRequest "$BaseUrl/health" -TimeoutSec 5 -UseBasicParsing
  Write-Host "[OK] Docs health: $($resp.StatusCode)" -ForegroundColor Green
} catch {
  Write-Host "[!] Docs health check failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

if (Test-Path $Pdf) {
  Write-Host "[*] Ingesting PDF: $Pdf" -ForegroundColor Cyan
  $form = @{ file = Get-Item $Pdf }
  $headers = @{ 'x-api-key' = $ApiKey }
  $ingestResp = Invoke-WebRequest -Uri "$BaseUrl/v1/documents/ingest" -Method Post -Headers $headers -Form $form -UseBasicParsing
  Write-Host "[>] Ingest response: $($ingestResp.Content)"
} else {
  Write-Host "[!] PDF not found: $Pdf (skipping ingest)" -ForegroundColor Yellow
}

Write-Host "[*] Searching for 'introduction'" -ForegroundColor Cyan
$searchUrl = "$BaseUrl/v1/documents/search?q=introduction&top=3"
$searchResp = Invoke-WebRequest -Uri $searchUrl -Headers @{ 'x-api-key' = $ApiKey } -UseBasicParsing
Write-Host "[>] Search response: $($searchResp.Content)"

Write-Host "[DONE]" -ForegroundColor Green