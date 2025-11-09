# seed_architecture_facts.ps1
# Seeds core architecture facts into ASTRA's memory via Bridge
# Run this once after starting the Ascension Stack to teach ASTRA about the codebase

param(
    [string]$ApiUrl = "http://127.0.0.1:8765",
    [string]$SeedFile = "data\bridge_seed.jsonl"
)

Write-Host "`n=== ASTRA Architecture Facts Seeding ===" -ForegroundColor Cyan
Write-Host "API: $ApiUrl" -ForegroundColor Gray
Write-Host "Seed File: $SeedFile`n" -ForegroundColor Gray

# Check if seed file exists
if (-not (Test-Path $SeedFile)) {
    Write-Host "[✗] Seed file not found: $SeedFile" -ForegroundColor Red
    exit 1
}

# Check if API is available
try {
    $health = Invoke-RestMethod -Uri "$ApiUrl/v1/bridge/healthz" -Method GET -ErrorAction Stop
    Write-Host "[✓] Bridge API is healthy" -ForegroundColor Green
} catch {
    Write-Host "[✗] Bridge API not available. Start the Ascension Stack first." -ForegroundColor Red
    Write-Host "    Run: python launch_ascension_stack.py --port 8765" -ForegroundColor Yellow
    exit 1
}

# Read and post each line
$lines = Get-Content $SeedFile
$total = $lines.Count
$success = 0
$failed = 0

Write-Host "`nSeeding $total facts..." -ForegroundColor Yellow

foreach ($line in $lines) {
    if ($line.Trim() -eq "") {
        continue
    }
    
    try {
        # Parse JSON to extract the text field
        $json = $line | ConvertFrom-Json
        $factText = $json.text
        
        # Extract subject for display
        $subjectMatch = $factText -match '"subject":"([^"]+)"'
        $subject = if ($matches) { $matches[1] } else { "unknown" }
        
        # Post to bridge ingest endpoint
        $response = Invoke-RestMethod -Uri "$ApiUrl/v1/bridge/ingest" `
            -Method POST `
            -ContentType "application/json" `
            -Body $line `
            -ErrorAction Stop
        
        $success++
        Write-Host "  [✓] $subject" -ForegroundColor Green
        
    } catch {
        $failed++
        Write-Host "  [✗] Failed: $_" -ForegroundColor Red
    }
}

Write-Host "`n=== Seeding Complete ===" -ForegroundColor Cyan
Write-Host "Total: $total | Success: $success | Failed: $failed" -ForegroundColor White

if ($success -gt 0) {
    Write-Host "`n[✓] ASTRA now knows the architecture!" -ForegroundColor Green
    Write-Host "    Next: Run .\scripts\index_codebase.ps1 to index the full repository" -ForegroundColor Yellow
}

exit 0
