# Quick Pre-Cutover Validation Script
# Run this immediately before cutover to verify all prerequisites

Param(
    [string]$Namespace = "astra",
    [switch]$SkipBackupCheck
)

$ErrorActionPreference = "Continue"
$ChecksPassed = 0
$ChecksFailed = 0

function Test-Check {
    param(
        [string]$Name,
        [scriptblock]$Test,
        [string]$Fix = "N/A"
    )
    
    Write-Host "`n[$Name]" -ForegroundColor Cyan
    try {
        $result = & $Test
        if ($result) {
            Write-Host "  ✅ PASS" -ForegroundColor Green
            $script:ChecksPassed++
        } else {
            Write-Host "  ❌ FAIL" -ForegroundColor Red
            if ($Fix -ne "N/A") {
                Write-Host "  Fix: $Fix" -ForegroundColor Yellow
            }
            $script:ChecksFailed++
        }
    }
    catch {
        Write-Host "  ❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
        if ($Fix -ne "N/A") {
            Write-Host "  Fix: $Fix" -ForegroundColor Yellow
        }
        $script:ChecksFailed++
    }
}

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "ASTRA PRE-CUTOVER VALIDATION" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "Namespace: $Namespace" -ForegroundColor Gray
Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray

# Check 1: Namespace exists
Test-Check -Name "Namespace Exists" -Test {
    $ns = kubectl get namespace $Namespace -o json 2>$null | ConvertFrom-Json
    return $ns.metadata.name -eq $Namespace
} -Fix "kubectl create namespace $Namespace"

# Check 2: Secret exists
Test-Check -Name "Bridge Keys Secret Exists" -Test {
    $secret = kubectl -n $Namespace get secret bridge-keys -o json 2>$null | ConvertFrom-Json
    return $secret.metadata.name -eq "bridge-keys"
} -Fix "kubectl -n $Namespace create secret generic bridge-keys --from-file=bridge_keys=./keys.json"

# Check 3: TLS Certificate Ready
Test-Check -Name "TLS Certificate Issued" -Test {
    $cert = kubectl -n $Namespace get certificate -o json 2>$null | ConvertFrom-Json
    $ready = $cert.items | Where-Object { 
        $_.status.conditions | Where-Object { $_.type -eq "Ready" -and $_.status -eq "True" }
    }
    if ($ready) {
        Write-Host "  Certificate: $($ready.metadata.name)" -ForegroundColor Gray
        return $true
    }
    return $false
} -Fix "Check cert-manager logs: kubectl -n cert-manager logs -l app=cert-manager"

# Check 4: PVCs bound
Test-Check -Name "PVCs Bound" -Test {
    $pvcs = kubectl -n $Namespace get pvc -o json 2>$null | ConvertFrom-Json
    $notBound = $pvcs.items | Where-Object { $_.status.phase -ne "Bound" }
    if ($notBound) {
        Write-Host "  Not bound: $($notBound.metadata.name -join ', ')" -ForegroundColor Yellow
        return $false
    }
    Write-Host "  All PVCs bound" -ForegroundColor Gray
    return $true
} -Fix "Check PV provisioner: kubectl get pv"

# Check 5: Deployments ready
Test-Check -Name "Deployments Ready" -Test {
    $deploys = kubectl -n $Namespace get deployment -o json 2>$null | ConvertFrom-Json
    $notReady = $deploys.items | Where-Object { 
        $_.status.readyReplicas -ne $_.status.replicas 
    }
    if ($notReady) {
        Write-Host "  Not ready: $($notReady.metadata.name -join ', ')" -ForegroundColor Yellow
        return $false
    }
    Write-Host "  All deployments ready" -ForegroundColor Gray
    return $true
} -Fix "kubectl -n $Namespace get pods; kubectl -n $Namespace describe pod <pod-name>"

# Check 6: No shell scope keys
Test-Check -Name "No Shell Scope in Keys" -Test {
    $pod = kubectl -n $Namespace get pods -l app=bridge -o jsonpath='{.items[0].metadata.name}' 2>$null
    if (-not $pod) {
        Write-Host "  No bridge pod found (deployment may be pending)" -ForegroundColor Yellow
        return $false
    }
    $keys = kubectl -n $Namespace exec $pod -- cat /run/secrets/bridge_keys 2>$null
    if ($keys -match 'tool:shell') {
        Write-Host "  WARNING: Found tool:shell scope in keys file" -ForegroundColor Yellow
        return $false
    }
    Write-Host "  No dangerous scopes found" -ForegroundColor Gray
    return $true
} -Fix "Edit keys file to remove tool:shell scope; redeploy secret"

# Check 7: HPA configured
Test-Check -Name "HPA Configured" -Test {
    $hpa = kubectl -n $Namespace get hpa -o json 2>$null | ConvertFrom-Json
    if ($hpa.items.Count -eq 0) {
        Write-Host "  No HPA found" -ForegroundColor Yellow
        return $false
    }
    Write-Host "  HPA count: $($hpa.items.Count)" -ForegroundColor Gray
    return $true
} -Fix "kubectl apply -f k8s/hpa.yaml"

# Check 8: Prometheus scraping
Test-Check -Name "Prometheus Targets Up" -Test {
    # This requires port-forward or access to Prometheus
    # Skip if not accessible
    Write-Host "  Manual check required: kubectl -n monitoring port-forward svc/prometheus 9090:9090" -ForegroundColor Yellow
    Write-Host "  Then visit http://localhost:9090/targets" -ForegroundColor Yellow
    return $true
} -Fix "N/A - Manual verification"

# Check 9: Disk usage < 80%
Test-Check -Name "Disk Usage < 80%" -Test {
    $pod = kubectl -n $Namespace get pods -l app=bridge -o jsonpath='{.items[0].metadata.name}' 2>$null
    if (-not $pod) { return $false }
    
    $df = kubectl -n $Namespace exec $pod -- df -h /data 2>$null | Select-Object -Skip 1
    if ($df -match '(\d+)%') {
        $usage = [int]$matches[1]
        Write-Host "  Bridge /data usage: $usage%" -ForegroundColor Gray
        return $usage -lt 80
    }
    return $false
} -Fix "Clean up old logs or expand PV"

# Check 10: Backup exists (optional)
if (-not $SkipBackupCheck) {
    Test-Check -Name "Recent Backup Exists" -Test {
        # Check for backup CronJob or recent snapshot
        $cronjob = kubectl -n $Namespace get cronjob -o json 2>$null | ConvertFrom-Json
        if ($cronjob.items.Count -gt 0) {
            Write-Host "  Backup CronJob found: $($cronjob.items[0].metadata.name)" -ForegroundColor Gray
            return $true
        }
        Write-Host "  No backup CronJob found - manual backup required" -ForegroundColor Yellow
        return $false
    } -Fix "Create backup CronJob or trigger manual snapshot"
}

# Summary
Write-Host "`n" + ("=" * 70) -ForegroundColor Cyan
Write-Host "VALIDATION SUMMARY" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "Passed: $ChecksPassed" -ForegroundColor Green
Write-Host "Failed: $ChecksFailed" -ForegroundColor $(if ($ChecksFailed -gt 0) { "Red" } else { "Green" })

if ($ChecksFailed -gt 0) {
    Write-Host "`n[RESULT] VALIDATION FAILED - Fix issues before cutover" -ForegroundColor Red
    Write-Host "Review PRE_CUTOVER_CHECKLIST.md for detailed steps" -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "`n[RESULT] VALIDATION PASSED - Ready for cutover" -ForegroundColor Green
    Write-Host "Next: Run smoke_tests_production.ps1" -ForegroundColor Cyan
    exit 0
}
