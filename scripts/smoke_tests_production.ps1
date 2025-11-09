# ASTRA Production Smoke Tests
# Run these tests before and after cutover to verify system health

Param(
    [string]$BridgeUrl = "https://bridge.example.com",
    [string]$DocsUrl = "https://docs.example.com",
    [string]$QdrantUrl = "http://localhost:6333",
    [string]$AdminKey = $env:ADMIN_KEY,
    [string]$AgentKey = $env:AGENT_KEY,
    [string]$SamplePdf = "docs-sample\sample.pdf"
)

$ErrorActionPreference = "Continue"
$FailCount = 0
$PassCount = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Method = "GET",
        [hashtable]$Headers = @{},
        [string]$Body = $null,
        [string]$ExpectedPattern = $null
    )
    
    Write-Host "`n[TEST] $Name" -ForegroundColor Cyan
    Write-Host "  URL: $Url" -ForegroundColor Gray
    
    try {
        $params = @{
            Uri = $Url
            Method = $Method
            UseBasicParsing = $true
            TimeoutSec = 10
        }
        
        if ($Headers.Count -gt 0) {
            $params.Headers = $Headers
        }
        
        if ($Body) {
            $params.Body = $Body
            $params.ContentType = "application/json"
        }
        
        $response = Invoke-WebRequest @params
        $content = $response.Content
        
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
            if ($ExpectedPattern -and $content -notmatch $ExpectedPattern) {
                Write-Host "  [FAIL] Response doesn't match pattern: $ExpectedPattern" -ForegroundColor Red
                Write-Host "  Response: $($content.Substring(0, [Math]::Min(200, $content.Length)))..." -ForegroundColor Yellow
                $script:FailCount++
                return $false
            }
            Write-Host "  [PASS] Status: $($response.StatusCode)" -ForegroundColor Green
            Write-Host "  Response: $($content.Substring(0, [Math]::Min(100, $content.Length)))..." -ForegroundColor Gray
            $script:PassCount++
            return $true
        } else {
            Write-Host "  [FAIL] Status: $($response.StatusCode)" -ForegroundColor Red
            $script:FailCount++
            return $false
        }
    }
    catch {
        Write-Host "  [FAIL] Error: $($_.Exception.Message)" -ForegroundColor Red
        $script:FailCount++
        return $false
    }
}

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "ASTRA PRODUCTION SMOKE TESTS" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray

# Validate keys
if (-not $AdminKey) {
    Write-Host "`n[WARN] ADMIN_KEY not set. Admin tests will be skipped." -ForegroundColor Yellow
}
if (-not $AgentKey) {
    Write-Host "[ERROR] AGENT_KEY not set. Set via env var or -AgentKey parameter." -ForegroundColor Red
    exit 1
}

# Test 1: Bridge Health (Public)
Test-Endpoint -Name "Bridge Health" `
    -Url "$BridgeUrl/health" `
    -ExpectedPattern '"ok".*true'

# Test 2: Bridge List Tools (Admin)
if ($AdminKey) {
    Test-Endpoint -Name "Bridge List Tools (Admin)" `
        -Url "$BridgeUrl/tools" `
        -Headers @{ 'x-api-key' = $AdminKey } `
        -ExpectedPattern 'llama'
}

# Test 3: Bridge Tool Call - Llama (Agent)
$llamaPayload = @{
    tool_name = "llama"
    args = @{
        messages = @(
            @{ role = "user"; content = "ping" }
        )
        max_tokens = 10
    }
} | ConvertTo-Json -Depth 5

Test-Endpoint -Name "Bridge Tool Call - Llama (Agent)" `
    -Url "$BridgeUrl/call" `
    -Method "POST" `
    -Headers @{ 'x-api-key' = $AgentKey } `
    -Body $llamaPayload `
    -ExpectedPattern 'result'

# Test 4: Docs Health
Test-Endpoint -Name "Docs Health" `
    -Url "$DocsUrl/health" `
    -ExpectedPattern '"ok".*true'

# Test 5: Docs Ingest (Agent) - Only if sample PDF exists
if (Test-Path $SamplePdf) {
    Write-Host "`n[TEST] Docs Ingest (Agent)" -ForegroundColor Cyan
    Write-Host "  URL: $DocsUrl/v1/documents/ingest" -ForegroundColor Gray
    Write-Host "  PDF: $SamplePdf" -ForegroundColor Gray
    
    try {
        $form = @{ file = Get-Item $SamplePdf }
        $headers = @{ 'x-api-key' = $AgentKey }
        $ingestResp = Invoke-WebRequest -Uri "$DocsUrl/v1/documents/ingest" `
            -Method Post -Headers $headers -Form $form -UseBasicParsing -TimeoutSec 30
        
        if ($ingestResp.StatusCode -eq 200 -and $ingestResp.Content -match '"ingested_chunks"') {
            Write-Host "  [PASS] Status: $($ingestResp.StatusCode)" -ForegroundColor Green
            Write-Host "  Response: $($ingestResp.Content.Substring(0, [Math]::Min(100, $ingestResp.Content.Length)))..." -ForegroundColor Gray
            $script:PassCount++
        } else {
            Write-Host "  [FAIL] Unexpected response" -ForegroundColor Red
            $script:FailCount++
        }
    }
    catch {
        Write-Host "  [FAIL] Error: $($_.Exception.Message)" -ForegroundColor Red
        $script:FailCount++
    }
} else {
    Write-Host "`n[SKIP] Docs Ingest - Sample PDF not found: $SamplePdf" -ForegroundColor Yellow
}

# Test 6: Docs Search (Agent)
Test-Endpoint -Name "Docs Search (Agent)" `
    -Url "$DocsUrl/v1/documents/search?q=test&top=3" `
    -Headers @{ 'x-api-key' = $AgentKey } `
    -ExpectedPattern '\['

# Test 7: Qdrant Collections (via port-forward or if accessible)
Write-Host "`n[TEST] Qdrant Collections" -ForegroundColor Cyan
Write-Host "  URL: $QdrantUrl/collections" -ForegroundColor Gray
Write-Host "  Note: Requires kubectl port-forward or internal access" -ForegroundColor Gray

try {
    $qdrantResp = Invoke-WebRequest -Uri "$QdrantUrl/collections" -UseBasicParsing -TimeoutSec 5
    if ($qdrantResp.StatusCode -eq 200 -and $qdrantResp.Content -match 'astra_docs') {
        Write-Host "  [PASS] Qdrant accessible, collection found" -ForegroundColor Green
        $script:PassCount++
    } else {
        Write-Host "  [WARN] Qdrant accessible but collection not found" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "  [SKIP] Qdrant not accessible (expected if not port-forwarded)" -ForegroundColor Yellow
}

# Test 8: Admin Usage Endpoint (Admin)
if ($AdminKey) {
    Test-Endpoint -Name "Bridge Admin Usage (Admin)" `
        -Url "$BridgeUrl/admin/usage" `
        -Headers @{ 'x-api-key' = $AdminKey } `
        -ExpectedPattern '\{'
}

# Test 9: Bridge Metrics
Test-Endpoint -Name "Bridge Metrics" `
    -Url "$BridgeUrl/metrics" `
    -ExpectedPattern 'bridge_calls_total'

# Test 10: Docs Metrics
Test-Endpoint -Name "Docs Metrics" `
    -Url "$DocsUrl/metrics" `
    -ExpectedPattern 'docs_'

# Summary
Write-Host "`n" + ("=" * 70) -ForegroundColor Cyan
Write-Host "TEST SUMMARY" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "Passed: $PassCount" -ForegroundColor Green
Write-Host "Failed: $FailCount" -ForegroundColor $(if ($FailCount -gt 0) { "Red" } else { "Green" })
Write-Host "Finished: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray

if ($FailCount -gt 0) {
    Write-Host "`n[RESULT] SMOKE TESTS FAILED - Do not proceed with cutover" -ForegroundColor Red
    exit 1
} else {
    Write-Host "`n[RESULT] SMOKE TESTS PASSED - Safe to proceed" -ForegroundColor Green
    exit 0
}
