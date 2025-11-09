<#
.SYNOPSIS
    Pre-Canary Evidence Pack Generator for ASTRA Core

.DESCRIPTION
    Executes all blocking verification gates before canary deployment:
    1. Security scans (pip-audit, bandit, safety)
    2. Test coverage analysis (pytest --cov)
    3. Backup/restore validation (dry-run)
    
    Saves all artifacts to audit/PRE_CANARY_{timestamp}/

.PARAMETER Stamp
    Timestamp for evidence directory (default: current datetime)

.EXAMPLE
    .\scripts\pre_canary.ps1
    
.EXAMPLE
    .\scripts\pre_canary.ps1 -Stamp "20251101-143000"
#>

Param(
    [string]$Stamp = (Get-Date -Format "yyyyMMdd-HHmmss")
)

$ErrorActionPreference = "Continue"  # Continue on errors to collect all evidence
$AuditDir = "audit\PRE_CANARY_$Stamp"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  ASTRA CORE - PRE-CANARY EVIDENCE PACK" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Create evidence directory
New-Item -ItemType Directory -Force -Path $AuditDir | Out-Null
Write-Host "[INFO] Evidence directory: $AuditDir" -ForegroundColor Green

# ===== GIT SNAPSHOT =====
Write-Host "`n==[1/6 GIT SNAPSHOT]==" -ForegroundColor Yellow
try {
    git rev-parse HEAD | Out-File -FilePath "$AuditDir\GIT_COMMIT.txt" -Encoding UTF8
    git status --porcelain | Out-File -FilePath "$AuditDir\GIT_STATUS.txt" -Encoding UTF8
    git log -1 --pretty=format:"%H%n%an%n%ae%n%ai%n%s" | Out-File -FilePath "$AuditDir\GIT_LASTCOMMIT.txt" -Encoding UTF8
    Write-Host "  [OK] Git snapshot captured" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Git snapshot failed: $_" -ForegroundColor Yellow
}

# ===== SECURITY SCANS =====
Write-Host "`n==[2/6 SECURITY SCANS]==" -ForegroundColor Yellow

# Install scan tools
Write-Host "  Installing security scan tools..." -ForegroundColor Gray
pip install --quiet --upgrade pip-audit bandit safety 2>&1 | Out-Null

# pip-audit
Write-Host "  Running pip-audit..." -ForegroundColor Gray
try {
    pip-audit -r requirements.txt --desc 2>&1 | Tee-Object -FilePath "$AuditDir\pip_audit_report.txt"
    $pipAuditExitCode = $LASTEXITCODE
    if ($pipAuditExitCode -eq 0) {
        Write-Host "  [OK] pip-audit: No vulnerabilities found" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] pip-audit: Vulnerabilities detected (see report)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [ERROR] pip-audit failed: $_" -ForegroundColor Red
}

# bandit
Write-Host "  Running bandit..." -ForegroundColor Gray
try {
    bandit -r src/ -f json -o "$AuditDir\bandit_report.json" 2>&1 | Out-Null
    bandit -r src/ -f txt 2>&1 | Tee-Object -FilePath "$AuditDir\bandit_report.txt"
    $banditExitCode = $LASTEXITCODE
    if ($banditExitCode -eq 0) {
        Write-Host "  [OK] bandit: No issues found" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] bandit: Issues detected (see report)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [ERROR] bandit failed: $_" -ForegroundColor Red
}

# safety
Write-Host "  Running safety..." -ForegroundColor Gray
try {
    safety check -r requirements.txt --json 2>&1 | Out-File -FilePath "$AuditDir\safety_report.json" -Encoding UTF8
    safety check -r requirements.txt 2>&1 | Tee-Object -FilePath "$AuditDir\safety_report.txt"
    $safetyExitCode = $LASTEXITCODE
    if ($safetyExitCode -eq 0) {
        Write-Host "  [OK] safety: No vulnerabilities found" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] safety: Vulnerabilities detected (see report)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [ERROR] safety failed: $_" -ForegroundColor Red
}

# ===== TESTS + COVERAGE =====
Write-Host "`n==[3/6 TESTS + COVERAGE]==" -ForegroundColor Yellow
Write-Host "  Running pytest with coverage (target: >=70%)..." -ForegroundColor Gray

try {
    pytest --cov=src --cov-report=term --cov-report=html:"$AuditDir\htmlcov" `
           --cov-report=json:"$AuditDir\coverage.json" `
           --cov-report=xml:"$AuditDir\coverage.xml" `
           -v 2>&1 | Tee-Object -FilePath "$AuditDir\test_report.txt"
    
    $pytestExitCode = $LASTEXITCODE
    
    # Parse coverage percentage
    if (Test-Path "$AuditDir\coverage.json") {
        $coverageData = Get-Content "$AuditDir\coverage.json" -Raw | ConvertFrom-Json
        $coveragePct = [math]::Round($coverageData.totals.percent_covered, 2)
        
        if ($coveragePct -ge 70) {
            Write-Host "  [OK] Coverage: $coveragePct% (target: >=70%)" -ForegroundColor Green
        } elseif ($coveragePct -ge 60) {
            Write-Host "  [WARN] Coverage: $coveragePct% (below target of 70%)" -ForegroundColor Yellow
        } else {
            Write-Host "  [FAIL] Coverage: $coveragePct% (critically below 70%)" -ForegroundColor Red
        }
    } else {
        Write-Host "  [WARN] Coverage data not found" -ForegroundColor Yellow
    }
    
    if ($pytestExitCode -eq 0) {
        Write-Host "  [OK] All tests passed" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] Some tests failed (exit code: $pytestExitCode)" -ForegroundColor Red
    }
} catch {
    Write-Host "  [ERROR] pytest failed: $_" -ForegroundColor Red
}

# ===== BACKUP VALIDATION =====
Write-Host "`n==[4/6 BACKUP / RESTORE VALIDATION]==" -ForegroundColor Yellow
$backupName = "pre-deploy-$Stamp"

# Check if backup tools exist
if (Test-Path "tools\backup\backup_runner.py") {
    Write-Host "  Running backup dry-run..." -ForegroundColor Gray
    try {
        python tools\backup\backup_runner.py --dry-run --verbose 2>&1 | Tee-Object -FilePath "$AuditDir\backup_dry_run.txt"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Backup dry-run successful" -ForegroundColor Green
        } else {
            Write-Host "  [WARN] Backup dry-run completed with warnings" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  [ERROR] Backup dry-run failed: $_" -ForegroundColor Red
    }
    
    Write-Host "  Running backup execution..." -ForegroundColor Gray
    try {
        python tools\backup\backup_runner.py --target "local://backup/$backupName" 2>&1 | Tee-Object -FilePath "$AuditDir\backup_exec.txt"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Backup execution successful" -ForegroundColor Green
        } else {
            Write-Host "  [WARN] Backup execution completed with warnings" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  [ERROR] Backup execution failed: $_" -ForegroundColor Red
    }
    
    if (Test-Path "tools\backup\restore_runner.py") {
        Write-Host "  Running restore dry-run..." -ForegroundColor Gray
        try {
            python tools\backup\restore_runner.py --source "local://backup/$backupName" --target staging --dry-run 2>&1 | Tee-Object -FilePath "$AuditDir\restore_dry_run.txt"
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [OK] Restore dry-run successful" -ForegroundColor Green
            } else {
                Write-Host "  [WARN] Restore dry-run completed with warnings" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "  [ERROR] Restore dry-run failed: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "  [WARN] restore_runner.py not found - skipping restore validation" -ForegroundColor Yellow
        "SKIPPED: restore_runner.py not found" | Out-File -FilePath "$AuditDir\restore_dry_run.txt" -Encoding UTF8
    }
} else {
    Write-Host "  [WARN] backup_runner.py not found - skipping backup validation" -ForegroundColor Yellow
    "SKIPPED: backup_runner.py not found" | Out-File -FilePath "$AuditDir\backup_dry_run.txt" -Encoding UTF8
    "SKIPPED: backup_runner.py not found" | Out-File -FilePath "$AuditDir\backup_exec.txt" -Encoding UTF8
    "SKIPPED: backup_runner.py not found" | Out-File -FilePath "$AuditDir\restore_dry_run.txt" -Encoding UTF8
}

# ===== FILE HASHES =====
Write-Host "`n==[5/6 FILE INTEGRITY]==" -ForegroundColor Yellow
Write-Host "  Generating file hashes..." -ForegroundColor Gray
try {
    $filesToHash = @(
        "Dockerfile",
        "requirements.txt",
        "pyproject.toml"
    ) + (Get-ChildItem -Path "k8s" -Filter "*.yaml" -Recurse | Select-Object -ExpandProperty FullName)
    
    $hashes = @()
    foreach ($file in $filesToHash) {
        if (Test-Path $file) {
            $hash = (Get-FileHash -Path $file -Algorithm SHA256).Hash
            $relativePath = Resolve-Path -Relative $file
            $hashes += "$hash  $relativePath"
        }
    }
    
    $hashes | Out-File -FilePath "$AuditDir\FILE_HASHES.txt" -Encoding UTF8
    Write-Host "  [OK] File hashes generated for $($hashes.Count) files" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] File hash generation failed: $_" -ForegroundColor Red
}

# ===== SBOM GENERATION =====
Write-Host "`n==[6/6 SBOM GENERATION]==" -ForegroundColor Yellow
Write-Host "  Installing cyclonedx-bom..." -ForegroundColor Gray
pip install --quiet cyclonedx-bom 2>&1 | Out-Null

Write-Host "  Generating SBOM..." -ForegroundColor Gray
try {
    cyclonedx-py --format json --outfile "$AuditDir\SBOM_cyclonedx.json" 2>&1 | Out-Null
    if (Test-Path "$AuditDir\SBOM_cyclonedx.json") {
        Write-Host "  [OK] SBOM generated" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] SBOM file not created" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [ERROR] SBOM generation failed: $_" -ForegroundColor Red
}

# ===== SUMMARY =====
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  EVIDENCE PACK COMPLETE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Location: $AuditDir" -ForegroundColor Green
Write-Host "  Files generated:" -ForegroundColor White
Get-ChildItem -Path $AuditDir -File | ForEach-Object {
    Write-Host "    - $($_.Name)" -ForegroundColor Gray
}

Write-Host "`n  Next step: Run assert_go_nogo.ps1 to validate results" -ForegroundColor Yellow
Write-Host "  Command: .\scripts\assert_go_nogo.ps1 -AuditDir '$AuditDir'`n" -ForegroundColor Cyan
