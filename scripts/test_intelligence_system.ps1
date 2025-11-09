# test_intelligence_system.ps1
# Comprehensive smoke tests for ASTRA Intelligence & Updates System
# Tests: health, event posting, memory writes, announcement logic

param(
    [string]$ApiUrl = "http://127.0.0.1:8765"
)

Write-Host "`n======================================" -ForegroundColor Cyan
Write-Host "  ASTRA INTELLIGENCE SYSTEM TESTS" -ForegroundColor Cyan
Write-Host "======================================`n" -ForegroundColor Cyan

$passed = 0
$failed = 0
$skipped = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Endpoint,
        [object]$Body,
        [int]$ExpectedStatus = 200,
        [string[]]$ExpectedFields
    )
    
    Write-Host "TEST: $Name" -ForegroundColor Yellow
    
    try {
        $params = @{
            Uri = "$ApiUrl$Endpoint"
            Method = $Method
            ErrorAction = "Stop"
        }
        
        if ($Body) {
            $params.Body = ($Body | ConvertTo-Json -Compress -Depth 10)
            $params.ContentType = "application/json"
        }
        
        $response = Invoke-RestMethod @params
        
        # Check expected fields
        $missingFields = @()
        if ($ExpectedFields) {
            foreach ($field in $ExpectedFields) {
                if (-not ($response.PSObject.Properties.Name -contains $field)) {
                    $missingFields += $field
                }
            }
        }
        
        if ($missingFields.Count -eq 0) {
            Write-Host "  [✓] PASS" -ForegroundColor Green
            Write-Host "  Response: $($response | ConvertTo-Json -Compress -Depth 2)`n" -ForegroundColor Gray
            return $true
        } else {
            Write-Host "  [✗] FAIL - Missing fields: $($missingFields -join ', ')" -ForegroundColor Red
            return $false
        }
        
    } catch {
        Write-Host "  [✗] FAIL - $_`n" -ForegroundColor Red
        return $false
    }
}

# Test 1: Updates Health Check
if (Test-Endpoint -Name "Updates Health Check" `
                   -Method "GET" `
                   -Endpoint "/v1/updates/healthz" `
                   -ExpectedFields @("status", "enabled", "announce_level")) {
    $passed++
} else {
    $failed++
}

# Test 2: Bridge Health Check
if (Test-Endpoint -Name "Bridge Health Check" `
                   -Method "GET" `
                   -Endpoint "/v1/bridge/healthz" `
                   -ExpectedFields @("status")) {
    $passed++
} else {
    $skipped++
    Write-Host "  [!] Bridge may not be available - skipping" -ForegroundColor Yellow
}

# Test 3: Post Code Commit Event
$commitPayload = @{
    kind = "code_commit"
    title = "Test: Intelligence system smoke test"
    summary = "Automated test of updates system"
    actor = "test_suite"
    impact = "low"
    details = @{
        commit = "test123"
        files_changed = 1
        branch = "test"
    }
    refs = @("scripts/test_intelligence_system.ps1")
}

if (Test-Endpoint -Name "Post Code Commit Event" `
                   -Method "POST" `
                   -Endpoint "/v1/updates/event" `
                   -Body $commitPayload `
                   -ExpectedFields @("status", "rid", "wrote_episodes", "wrote_facts")) {
    $passed++
} else {
    $failed++
}

# Test 4: Post Build Failure (High Impact)
$buildFailPayload = @{
    kind = "build_failed"
    title = "Test: Simulated build failure"
    impact = "high"
    details = @{
        tests_total = 100
        tests_failed = 5
        coverage = 85.2
        duration_s = 120
    }
}

if (Test-Endpoint -Name "Post Build Failure Event" `
                   -Method "POST" `
                   -Endpoint "/v1/updates/event" `
                   -Body $buildFailPayload `
                   -ExpectedFields @("status", "announced")) {
    $passed++
} else {
    $failed++
}

# Test 5: Post Patch Applied Event
$patchPayload = @{
    kind = "patch_applied"
    title = "Test: Intelligence system deployment"
    summary = "Added updates router and memory integration"
    actor = "copilot"
    impact = "medium"
    details = @{
        files = @("src/astra/api/routes/updates.py", "src/astra/visualization/ascension_api.py")
        tests_added = 0
        lines_changed = 450
    }
}

if (Test-Endpoint -Name "Post Patch Applied Event" `
                   -Method "POST" `
                   -Endpoint "/v1/updates/event" `
                   -Body $patchPayload `
                   -ExpectedFields @("status", "wrote_facts")) {
    $passed++
} else {
    $failed++
}

# Test 6: Updates Stats Endpoint
if (Test-Endpoint -Name "Updates Stats" `
                   -Method "GET" `
                   -Endpoint "/v1/updates/stats" `
                   -ExpectedFields @("status")) {
    $passed++
} else {
    $failed++
}

# Summary
Write-Host "`n======================================" -ForegroundColor Cyan
Write-Host "  TEST RESULTS" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Passed:  $passed" -ForegroundColor Green
Write-Host "  Failed:  $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Gray" })
Write-Host "  Skipped: $skipped" -ForegroundColor Yellow
Write-Host "======================================`n" -ForegroundColor Cyan

if ($failed -eq 0) {
    Write-Host "[✓] All tests passed!" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Yellow
    Write-Host "  1. Run .\scripts\seed_architecture_facts.ps1" -ForegroundColor Gray
    Write-Host "  2. Run .\scripts\seed_curriculum.ps1" -ForegroundColor Gray
    Write-Host "  3. Ask ASTRA to verify understanding" -ForegroundColor Gray
    exit 0
} else {
    Write-Host "[✗] Some tests failed. Check the logs above." -ForegroundColor Red
    exit 1
}
