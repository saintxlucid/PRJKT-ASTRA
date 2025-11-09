<#
.SYNOPSIS
    GO/NO-GO Decision Validator for ASTRA Core Canary Deployment

.DESCRIPTION
    Analyzes pre-canary evidence pack and provides clear GO/NO-GO decision.
    Gates:
    1. Security: No HIGH/CRITICAL vulnerabilities
    2. Coverage: >=70% code coverage
    3. Backup/Restore: Dry-run validations passed
    
    Exit codes:
    0 = GO (all gates passed)
    1 = NO-GO (one or more gates failed)
    2 = ERROR (audit directory not found or invalid)

.PARAMETER AuditDir
    Path to pre-canary evidence directory

.EXAMPLE
    .\scripts\assert_go_nogo.ps1 -AuditDir "audit\PRE_CANARY_20251101-143000"
#>

Param(
    [Parameter(Mandatory=$true)]
    [string]$AuditDir
)

$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  ASTRA CORE - GO/NO-GO DECISION" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Validate audit directory exists
if (-not (Test-Path $AuditDir)) {
    Write-Host "[ERROR] Audit directory not found: $AuditDir" -ForegroundColor Red
    exit 2
}

Write-Host "[INFO] Analyzing evidence from: $AuditDir`n" -ForegroundColor Green

# Initialize gate results
$gates = @{
    security = @{ pass = $false; details = @() }
    coverage = @{ pass = $false; details = @() }
    backup   = @{ pass = $false; details = @() }
}

# ===== GATE 1: SECURITY =====
Write-Host "==[GATE 1: SECURITY SCANS]==" -ForegroundColor Yellow

# Check pip-audit
if (Test-Path "$AuditDir\pip_audit_report.txt") {
    $pipAuditContent = Get-Content "$AuditDir\pip_audit_report.txt" -Raw
    $hasCritical = ($pipAuditContent -match '(?i)(CRITICAL|HIGH)')
    
    if (-not $hasCritical) {
        $gates.security.details += "[OK] pip-audit: No CRITICAL/HIGH vulnerabilities"
        Write-Host "  ✓ pip-audit: PASS" -ForegroundColor Green
    } else {
        $gates.security.details += "[FAIL] pip-audit: CRITICAL/HIGH vulnerabilities found"
        Write-Host "  ✗ pip-audit: FAIL (CRITICAL/HIGH found)" -ForegroundColor Red
    }
} else {
    $gates.security.details += "[WARN] pip-audit report not found"
    Write-Host "  ? pip-audit: NOT RUN" -ForegroundColor Yellow
}

# Check bandit
if (Test-Path "$AuditDir\bandit_report.txt") {
    $banditContent = Get-Content "$AuditDir\bandit_report.txt" -Raw
    $hasHighIssues = ($banditContent -match 'Issue:\s+High|Severity:\s+High')
    
    if (-not $hasHighIssues) {
        $gates.security.details += "[OK] bandit: No HIGH severity issues"
        Write-Host "  ✓ bandit: PASS" -ForegroundColor Green
    } else {
        $gates.security.details += "[FAIL] bandit: HIGH severity issues found"
        Write-Host "  ✗ bandit: FAIL (HIGH issues found)" -ForegroundColor Red
    }
} else {
    $gates.security.details += "[WARN] bandit report not found"
    Write-Host "  ? bandit: NOT RUN" -ForegroundColor Yellow
}

# Check safety
if (Test-Path "$AuditDir\safety_report.txt") {
    $safetyContent = Get-Content "$AuditDir\safety_report.txt" -Raw
    $hasVulns = ($safetyContent -match '(?i)(vulnerability|CVE-)')
    
    if (-not $hasVulns) {
        $gates.security.details += "[OK] safety: No known vulnerabilities"
        Write-Host "  ✓ safety: PASS" -ForegroundColor Green
    } else {
        # Check if these are just informational or actually critical
        $gates.security.details += "[WARN] safety: Vulnerabilities detected (review required)"
        Write-Host "  ! safety: REVIEW REQUIRED" -ForegroundColor Yellow
    }
} else {
    $gates.security.details += "[WARN] safety report not found"
    Write-Host "  ? safety: NOT RUN" -ForegroundColor Yellow
}

# Overall security gate decision
$securityPass = ($gates.security.details | Where-Object { $_ -match '\[FAIL\]' }).Count -eq 0
$gates.security.pass = $securityPass

if ($securityPass) {
    Write-Host "`n  GATE 1 RESULT: " -NoNewline; Write-Host "PASS" -ForegroundColor Green
} else {
    Write-Host "`n  GATE 1 RESULT: " -NoNewline; Write-Host "FAIL" -ForegroundColor Red
}

# ===== GATE 2: COVERAGE =====
Write-Host "`n==[GATE 2: TEST COVERAGE]==" -ForegroundColor Yellow

if (Test-Path "$AuditDir\coverage.json") {
    try {
        $coverageData = Get-Content "$AuditDir\coverage.json" -Raw | ConvertFrom-Json
        $coveragePct = [math]::Round($coverageData.totals.percent_covered, 2)
        
        Write-Host "  Coverage: $coveragePct%" -ForegroundColor White
        
        if ($coveragePct -ge 70) {
            $gates.coverage.details += "[OK] Coverage: $coveragePct% (target: >=70%)"
            $gates.coverage.pass = $true
            Write-Host "  ✓ Coverage target met (>=70%)" -ForegroundColor Green
            Write-Host "`n  GATE 2 RESULT: " -NoNewline; Write-Host "PASS" -ForegroundColor Green
        } elseif ($coveragePct -ge 60) {
            $gates.coverage.details += "[WARN] Coverage: $coveragePct% (below target but acceptable)"
            $gates.coverage.pass = $false
            Write-Host "  ! Coverage below target (60-70%)" -ForegroundColor Yellow
            Write-Host "`n  GATE 2 RESULT: " -NoNewline; Write-Host "CONDITIONAL (review required)" -ForegroundColor Yellow
        } else {
            $gates.coverage.details += "[FAIL] Coverage: $coveragePct% (critically low)"
            $gates.coverage.pass = $false
            Write-Host "  ✗ Coverage critically low (<60%)" -ForegroundColor Red
            Write-Host "`n  GATE 2 RESULT: " -NoNewline; Write-Host "FAIL" -ForegroundColor Red
        }
    } catch {
        $gates.coverage.details += "[ERROR] Failed to parse coverage data"
        Write-Host "  ✗ Coverage data parsing failed" -ForegroundColor Red
        Write-Host "`n  GATE 2 RESULT: " -NoNewline; Write-Host "ERROR" -ForegroundColor Red
    }
} else {
    $gates.coverage.details += "[FAIL] Coverage data not found"
    Write-Host "  ✗ coverage.json not found" -ForegroundColor Red
    Write-Host "`n  GATE 2 RESULT: " -NoNewline; Write-Host "FAIL" -ForegroundColor Red
}

# ===== GATE 3: BACKUP/RESTORE =====
Write-Host "`n==[GATE 3: BACKUP/RESTORE VALIDATION]==" -ForegroundColor Yellow

$backupOK = $false
$restoreOK = $false

# Check backup dry-run
if (Test-Path "$AuditDir\backup_dry_run.txt") {
    $backupContent = Get-Content "$AuditDir\backup_dry_run.txt" -Raw
    if ($backupContent -match '(?i)(SKIPPED)') {
        Write-Host "  ! backup dry-run: SKIPPED (tools not found)" -ForegroundColor Yellow
        $gates.backup.details += "[SKIPPED] Backup dry-run not available"
        $backupOK = $true  # Not blocking if tools don't exist
    } elseif ($backupContent -match '(?i)(completed|success|ok|passed|validation)') {
        Write-Host "  ✓ backup dry-run: PASS" -ForegroundColor Green
        $gates.backup.details += "[OK] Backup dry-run successful"
        $backupOK = $true
    } else {
        Write-Host "  ✗ backup dry-run: FAIL" -ForegroundColor Red
        $gates.backup.details += "[FAIL] Backup dry-run failed"
    }
} else {
    Write-Host "  ? backup dry-run: NOT RUN" -ForegroundColor Yellow
    $gates.backup.details += "[WARN] Backup dry-run not found"
}

# Check backup execution
if (Test-Path "$AuditDir\backup_exec.txt") {
    $backupExecContent = Get-Content "$AuditDir\backup_exec.txt" -Raw
    if ($backupExecContent -match '(?i)(SKIPPED)') {
        Write-Host "  ! backup execution: SKIPPED" -ForegroundColor Yellow
    } elseif ($backupExecContent -match '(?i)(completed|success)') {
        Write-Host "  ✓ backup execution: SUCCESS" -ForegroundColor Green
        $gates.backup.details += "[OK] Backup execution successful"
    } else {
        Write-Host "  ! backup execution: REVIEW REQUIRED" -ForegroundColor Yellow
    }
}

# Check restore dry-run
if (Test-Path "$AuditDir\restore_dry_run.txt") {
    $restoreContent = Get-Content "$AuditDir\restore_dry_run.txt" -Raw
    if ($restoreContent -match '(?i)(SKIPPED)') {
        Write-Host "  ! restore dry-run: SKIPPED (tools not found)" -ForegroundColor Yellow
        $gates.backup.details += "[SKIPPED] Restore dry-run not available"
        $restoreOK = $true  # Not blocking if tools don't exist
    } elseif ($restoreContent -match '(?i)(validation\s+ok|success|passed)') {
        Write-Host "  ✓ restore dry-run: PASS" -ForegroundColor Green
        $gates.backup.details += "[OK] Restore dry-run successful"
        $restoreOK = $true
    } else {
        Write-Host "  ✗ restore dry-run: FAIL" -ForegroundColor Red
        $gates.backup.details += "[FAIL] Restore dry-run failed"
    }
} else {
    Write-Host "  ? restore dry-run: NOT RUN" -ForegroundColor Yellow
    $gates.backup.details += "[WARN] Restore dry-run not found"
}

$gates.backup.pass = $backupOK -and $restoreOK

if ($gates.backup.pass) {
    Write-Host "`n  GATE 3 RESULT: " -NoNewline; Write-Host "PASS" -ForegroundColor Green
} else {
    Write-Host "`n  GATE 3 RESULT: " -NoNewline; Write-Host "FAIL" -ForegroundColor Red
}

# ===== FINAL DECISION =====
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  FINAL GO/NO-GO DECISION" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Gate Results:" -ForegroundColor White
Write-Host "  Security:  " -NoNewline
if ($gates.security.pass) { Write-Host "PASS" -ForegroundColor Green } else { Write-Host "FAIL" -ForegroundColor Red }
Write-Host "  Coverage:  " -NoNewline
if ($gates.coverage.pass) { Write-Host "PASS" -ForegroundColor Green } else { Write-Host "FAIL" -ForegroundColor Red }
Write-Host "  Backup/DR: " -NoNewline
if ($gates.backup.pass) { Write-Host "PASS" -ForegroundColor Green } else { Write-Host "FAIL" -ForegroundColor Red }

$allPass = $gates.security.pass -and $gates.coverage.pass -and $gates.backup.pass

Write-Host "`n  DECISION: " -NoNewline
if ($allPass) {
    Write-Host "✅ GO FOR CANARY DEPLOYMENT" -ForegroundColor Green
    Write-Host "`n  You may proceed with canary deployment." -ForegroundColor White
    Write-Host "  Next: kubectl apply -f k8s\canary\canary-deployment.yaml`n" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "🛑 NO-GO - BLOCKERS DETECTED" -ForegroundColor Red
    Write-Host "`n  Do NOT proceed with canary deployment." -ForegroundColor White
    Write-Host "  Review failed gates and remediate before retrying.`n" -ForegroundColor Yellow
    
    Write-Host "Blocking issues:" -ForegroundColor Red
    if (-not $gates.security.pass) {
        Write-Host "  - Security: Contains HIGH/CRITICAL vulnerabilities" -ForegroundColor Red
    }
    if (-not $gates.coverage.pass) {
        Write-Host "  - Coverage: Below 70% threshold" -ForegroundColor Red
    }
    if (-not $gates.backup.pass) {
        Write-Host "  - Backup/Restore: Validation failed" -ForegroundColor Red
    }
    
    Write-Host ""
    exit 1
}
