# ASTRA Security Scan Runner - Dependency & Code Auditing
# Runs pip-audit, bandit, and safety checks
# Reports saved to audit/ directory

$ErrorActionPreference = "Stop"

Write-Host "=== ASTRA Security Scan Runner ===" -ForegroundColor Cyan
Write-Host ""

# Ensure audit directory exists
New-Item -ItemType Directory -Force -Path "audit" | Out-Null

# Install/upgrade security tools
Write-Host "[1/4] Updating security tools..." -ForegroundColor Yellow
python -m pip install -U pip pip-audit bandit safety 2>&1 | Out-Null
Write-Host "✓ Tools updated" -ForegroundColor Green
Write-Host ""

# Run pip-audit (dependency vulnerabilities)
Write-Host "[2/4] Running pip-audit (dependency vulnerabilities)..." -ForegroundColor Yellow
try {
    pip-audit --fix 2>&1 | Tee-Object -FilePath "audit/pip_audit.log"
    Write-Host "✓ pip-audit complete" -ForegroundColor Green
} catch {
    Write-Host "⚠️  pip-audit found issues (see audit/pip_audit.log)" -ForegroundColor Red
}
Write-Host ""

# Run bandit (code security)
Write-Host "[3/4] Running bandit (code security analysis)..." -ForegroundColor Yellow
try {
    bandit -r src -f json -o audit/bandit_report.json
    $banditIssues = (Get-Content audit/bandit_report.json | ConvertFrom-Json).results.Count
    Write-Host "✓ bandit complete ($banditIssues issues found)" -ForegroundColor Green
} catch {
    Write-Host "⚠️  bandit encountered errors" -ForegroundColor Red
}
Write-Host ""

# Run safety (known vulnerabilities)
Write-Host "[4/4] Running safety (known vulnerability database)..." -ForegroundColor Yellow
try {
    safety check --full-report --json | Out-File -Encoding utf8 "audit/safety_report.json"
    Write-Host "✓ safety complete" -ForegroundColor Green
} catch {
    Write-Host "⚠️  safety found vulnerabilities (see audit/safety_report.json)" -ForegroundColor Red
}
Write-Host ""

# Summary
Write-Host "=== Scan Complete ===" -ForegroundColor Cyan
Write-Host "Reports available in audit/ directory:"
Write-Host "  - pip_audit.log"
Write-Host "  - bandit_report.json"
Write-Host "  - safety_report.json"
Write-Host ""
Write-Host "Review reports and remediate critical/high severity issues before deployment." -ForegroundColor Yellow
