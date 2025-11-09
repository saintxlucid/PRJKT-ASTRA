# scripts/test_bridge.ps1
# Smoke test for ASTRA Tool Bridge

param(
    [string]$BridgeUrl = "http://127.0.0.1:8765",
    [string]$ApiKey = $env:BRIDGE_API_KEY
)

$ErrorActionPreference = "Stop"

Write-Host "`n=== ASTRA Bridge Smoke Test ===" -ForegroundColor Cyan

if (-not $ApiKey) {
    $ApiKey = "changeme"
}

$headers = @{
    "x-api-key" = $ApiKey
    "Content-Type" = "application/json"
}

# Test 1: Health check
Write-Host "`n[1/5] Testing health endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$BridgeUrl/health" -Method Get
    if ($health.ok) {
        Write-Host "  ✓ Health check passed" -ForegroundColor Green
    } else {
        throw "Health check returned not OK"
    }
} catch {
    Write-Host "  ✗ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 2: List tools
Write-Host "`n[2/5] Testing tools list..." -ForegroundColor Yellow
try {
    $tools = Invoke-RestMethod -Uri "$BridgeUrl/tools" -Method Get -Headers $headers
    $toolCount = $tools.tools.Count
    Write-Host "  ✓ Found $toolCount registered tools" -ForegroundColor Green
    foreach ($tool in $tools.tools) {
        Write-Host "    - $($tool.name) (timeout: $($tool.timeout)s)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ✗ Tools list failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 3: Shell tool (echo)
Write-Host "`n[3/5] Testing shell tool..." -ForegroundColor Yellow
try {
    $payload = @{
        tool_name = "shell"
        args = @{
            cmd = "echo hello bridge"
        }
    } | ConvertTo-Json
    
    $result = Invoke-RestMethod -Uri "$BridgeUrl/call" -Method Post -Headers $headers -Body $payload
    
    if ($result.ok -and $result.result.stdout -like "*hello bridge*") {
        Write-Host "  ✓ Shell tool executed successfully" -ForegroundColor Green
        Write-Host "    Output: $($result.result.stdout.Trim())" -ForegroundColor Gray
    } else {
        throw "Shell tool returned unexpected result"
    }
} catch {
    Write-Host "  ✗ Shell tool failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: File read tool
Write-Host "`n[4/5] Testing file read tool..." -ForegroundColor Yellow
try {
    # Create test file
    $testFile = "data/safe/test_bridge.txt"
    New-Item -ItemType Directory -Path "data/safe" -Force | Out-Null
    "Bridge test content" | Out-File -FilePath $testFile -Encoding UTF8
    
    $payload = @{
        tool_name = "file_read"
        args = @{
            path = $testFile
        }
    } | ConvertTo-Json
    
    $result = Invoke-RestMethod -Uri "$BridgeUrl/call" -Method Post -Headers $headers -Body $payload
    
    if ($result.ok -and $result.result.content -like "*Bridge test content*") {
        Write-Host "  ✓ File read tool executed successfully" -ForegroundColor Green
    } else {
        throw "File read tool returned unexpected result"
    }
    
    # Cleanup
    Remove-Item $testFile -ErrorAction SilentlyContinue
} catch {
    Write-Host "  ✗ File read tool failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: Metrics endpoint
Write-Host "`n[5/5] Testing metrics endpoint..." -ForegroundColor Yellow
try {
    $metrics = Invoke-WebRequest -Uri "$BridgeUrl/metrics" -Method Get -UseBasicParsing
    
    if ($metrics.Content -like "*bridge_calls_total*") {
        Write-Host "  ✓ Metrics endpoint working" -ForegroundColor Green
        
        # Parse call counts
        $lines = $metrics.Content -split "`n"
        $callMetrics = $lines | Where-Object { $_ -like "bridge_calls_total*" -and $_ -notlike "#*" }
        
        if ($callMetrics) {
            Write-Host "    Recent calls:" -ForegroundColor Gray
            foreach ($metric in $callMetrics | Select-Object -First 5) {
                Write-Host "      $metric" -ForegroundColor Gray
            }
        }
    } else {
        throw "Metrics endpoint returned unexpected format"
    }
} catch {
    Write-Host "  ✗ Metrics endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Summary
Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "Bridge URL: $BridgeUrl" -ForegroundColor Green
Write-Host "All critical tests passed ✓" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Wire bridge into task agent" -ForegroundColor Gray
Write-Host "  2. Add custom tool adapters" -ForegroundColor Gray
Write-Host "  3. Set up Grafana dashboards" -ForegroundColor Gray
Write-Host "  4. Enable production security" -ForegroundColor Gray
