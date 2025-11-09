# docs_ci.ps1
# Comprehensive documentation CI checks
# Usage: .\scripts\docs_ci.ps1

$ErrorActionPreference = "Stop"
$root = "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
Set-Location $root

Write-Host "`n╔═══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   ASTRA Documentation CI Validation Suite    ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════╝`n" -ForegroundColor Cyan

$allPassed = $true

# ============================================
# Check 1: Run link and anchor validator
# ============================================
Write-Host "📝 Check 1: Validating links and anchors..." -ForegroundColor Yellow
try {
    & "$root\scripts\docs_validate.ps1"
    if ($LASTEXITCODE -ne 0) { 
        $allPassed = $false
        Write-Host "   ❌ Link validation failed`n" -ForegroundColor Red
    } else {
        Write-Host "   ✅ All links and anchors valid`n" -ForegroundColor Green
    }
} catch {
    Write-Host "   ❌ Error running link validator: $_`n" -ForegroundColor Red
    $allPassed = $false
}

# ============================================
# Check 2: Required files present
# ============================================
Write-Host "📂 Check 2: Verifying required documentation files..." -ForegroundColor Yellow
$must = @(
  "DOCUMENTATION_INDEX.md",
  "DEPLOYMENT_GUIDE_CONSOLIDATED.md",
  "ARCHITECTURE_PRODUCTION.md",
  "PROJECT_FINAL_REPORT.md",
  "QUICKSTART.md",
  "README.md",
  "ASTRA_ACTIVATION.md"
)

$missing = $must | Where-Object { -not (Test-Path (Join-Path $root $_)) }
if ($missing) { 
    Write-Host "   ❌ Missing required files:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "      • $_" -ForegroundColor Red }
    Write-Host ""
    $allPassed = $false
} else {
    Write-Host "   ✅ All $($must.Count) required files present`n" -ForegroundColor Green
}

# ============================================
# Check 3: Documentation index completeness
# ============================================
Write-Host "📊 Check 3: Checking documentation index completeness..." -ForegroundColor Yellow
$indexPath = Join-Path $root "DOCUMENTATION_INDEX.md"
if (Test-Path $indexPath) {
    $indexContent = Get-Content $indexPath -Raw
    $requiredSections = @(
        "Quick Start",
        "Architecture",
        "Deployment",
        "Testing",
        "Documentation Usage Patterns"
    )
    
    $missingSections = $requiredSections | Where-Object { $indexContent -notmatch $_ }
    if ($missingSections) {
        Write-Host "   ⚠️  Missing sections in index:" -ForegroundColor Yellow
        $missingSections | ForEach-Object { Write-Host "      • $_" -ForegroundColor Yellow }
        Write-Host ""
    } else {
        Write-Host "   ✅ Documentation index complete`n" -ForegroundColor Green
    }
} else {
    Write-Host "   ❌ DOCUMENTATION_INDEX.md not found`n" -ForegroundColor Red
    $allPassed = $false
}

# ============================================
# Check 4: Navigation banners present
# ============================================
Write-Host "🧭 Check 4: Verifying navigation banners..." -ForegroundColor Yellow
$primaryDocs = @(
    "QUICKSTART.md",
    "DEPLOYMENT_GUIDE_CONSOLIDATED.md",
    "ARCHITECTURE_PRODUCTION.md",
    "PROJECT_FINAL_REPORT.md"
)

$missingBanners = @()
foreach ($doc in $primaryDocs) {
    $docPath = Join-Path $root $doc
    if (Test-Path $docPath) {
        $content = Get-Content $docPath -Raw
        if ($content -notmatch '\[.*Docs Home.*\]\(DOCUMENTATION_INDEX\.md\)') {
            $missingBanners += $doc
        }
    }
}

if ($missingBanners) {
    Write-Host "   ⚠️  Missing navigation banners in:" -ForegroundColor Yellow
    $missingBanners | ForEach-Object { Write-Host "      • $_" -ForegroundColor Yellow }
    Write-Host ""
} else {
    Write-Host "   ✅ All primary docs have navigation banners`n" -ForegroundColor Green
}

# ============================================
# Check 5: File statistics
# ============================================
Write-Host "📈 Check 5: Documentation statistics..." -ForegroundColor Yellow
$allMds = Get-ChildItem $root -Filter *.md -Recurse | Where-Object { 
    $_.FullName -notmatch '\\node_modules\\|\\venv\\|\\__pycache__\\|\\.git\\' 
}
$rootMds = Get-ChildItem $root -Filter *.md | Where-Object { $_.Directory.FullName -eq $root }

Write-Host "   📄 Total markdown files: $($allMds.Count)" -ForegroundColor Cyan
Write-Host "   📄 Root-level docs: $($rootMds.Count)" -ForegroundColor Cyan

$totalSize = ($allMds | Measure-Object -Property Length -Sum).Sum / 1KB
Write-Host "   💾 Total documentation size: $([math]::Round($totalSize, 2)) KB`n" -ForegroundColor Cyan

# ============================================
# Final Result
# ============================================
Write-Host "════════════════════════════════════════════════" -ForegroundColor Cyan
if ($allPassed) {
    Write-Host "✅ ALL DOCUMENTATION CI CHECKS PASSED" -ForegroundColor Green
    Write-Host "════════════════════════════════════════════════`n" -ForegroundColor Cyan
    exit 0
} else {
    Write-Host "❌ SOME DOCUMENTATION CHECKS FAILED" -ForegroundColor Red
    Write-Host "════════════════════════════════════════════════`n" -ForegroundColor Cyan
    exit 1
}
