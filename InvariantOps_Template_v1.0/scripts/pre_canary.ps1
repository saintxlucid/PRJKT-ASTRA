# Pre-Canary Evidence Collection Script
# Run before every production deployment to collect invariant evidence

param(
    [string]$Branch = "main",
    [string]$OutputDir = "evidence_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
)

Write-Host "🔍 Collecting pre-canary evidence..." -ForegroundColor Cyan

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

# 1. Git commit info
Write-Host "📝 Git commit info..." -ForegroundColor Yellow
git log -1 --pretty=format:"Commit: %H%nAuthor: %an%nDate: %ai%nMessage: %s" > "$OutputDir/commit_info.txt"

# 2. SBOM generation
Write-Host "📦 Generating SBOM..." -ForegroundColor Yellow
pip freeze > "$OutputDir/requirements.txt"
cyclonedx-py environment > "$OutputDir/sbom.json"

# 3. Security scans
Write-Host "🔒 Running security scans..." -ForegroundColor Yellow
pip-audit --format json > "$OutputDir/pip_audit.json"
bandit -r . -f json -o "$OutputDir/bandit.json" 2>$null
safety check --json > "$OutputDir/safety.json" 2>$null

# 4. Test results
Write-Host "🧪 Running tests..." -ForegroundColor Yellow
pytest --cov=. --cov-report=xml:$OutputDir/coverage.xml --cov-report=html:$OutputDir/coverage_html --junit-xml=$OutputDir/test_results.xml

# 5. Check operational invariants
Write-Host "⚖️ Verifying invariants..." -ForegroundColor Yellow
python scripts/assert_go_nogo.sh "$OutputDir" | Tee-Object -FilePath "$OutputDir/invariants_check.txt"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ GO: All invariants hold. Evidence pack: $OutputDir" -ForegroundColor Green
} else {
    Write-Host "❌ NO-GO: Invariants breached. Review $OutputDir/invariants_check.txt" -ForegroundColor Red
    exit 1
}

Write-Host "📂 Evidence pack: $OutputDir" -ForegroundColor Cyan
