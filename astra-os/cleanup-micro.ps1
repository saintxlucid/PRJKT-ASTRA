#!/usr/bin/env pwsh
# cleanup-micro.ps1 - ASTRA OS Micro-Optimization Cleanup Script
# Removes all non-essential files to minimize workspace footprint

param(
    [switch]$Aggressive,
    [switch]$KeepDeps,
    [switch]$DryRun
)

Write-Host "`n🎯 ASTRA OS Micro-Optimization Cleanup`n" -ForegroundColor Cyan

$startSize = (Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1GB
Write-Host "📊 Current workspace size: $([math]::Round($startSize, 2)) GB`n" -ForegroundColor Yellow

$removed = 0

# Function to remove with confirmation
function Remove-SafeItem {
    param($Path, $Description)
    
    if (Test-Path $Path) {
        $size = (Get-ChildItem -Recurse -Path $Path -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1MB
        
        if ($DryRun) {
            Write-Host "  [DRY RUN] Would remove: $Description ($([math]::Round($size, 1)) MB)" -ForegroundColor Gray
        } else {
            Write-Host "  ➜ Removing: $Description ($([math]::Round($size, 1)) MB)..." -ForegroundColor Yellow
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $Path
            Write-Host "    ✓ Removed" -ForegroundColor Green
        }
        
        $script:removed += $size
    }
}

# 1. Remove node_modules (largest contributor)
Write-Host "📦 Removing Node.js dependencies..." -ForegroundColor Cyan
if (-not $KeepDeps) {
    Get-ChildItem -Recurse -Filter "node_modules" -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-SafeItem $_.FullName "node_modules at $($_.Parent.Name)"
    }
}

# 2. Remove build artifacts
Write-Host "`n🏗️  Removing build artifacts..." -ForegroundColor Cyan
Remove-SafeItem "dist" "Production build"
Remove-SafeItem "build" "Build directory"
Remove-SafeItem ".next" "Next.js build"
Remove-SafeItem ".vite" "Vite cache"
Remove-SafeItem "out" "Output directory"
Remove-SafeItem "apps\pantheon\dist" "Pantheon build"

Get-ChildItem -Recurse -Filter "*.tsbuildinfo" -File -ErrorAction SilentlyContinue | ForEach-Object {
    if (-not $DryRun) { Remove-Item $_.FullName -Force }
    $script:removed += $_.Length / 1MB
}

# 3. Remove Python artifacts
Write-Host "`n🐍 Removing Python artifacts..." -ForegroundColor Cyan
if (-not $KeepDeps) {
    Remove-SafeItem ".venv" "Python virtual environment"
    Remove-SafeItem "venv" "Python venv"
}

Get-ChildItem -Recurse -Filter "__pycache__" -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-SafeItem $_.FullName "Python cache"
}

Get-ChildItem -Recurse -Filter "*.pyc" -File -ErrorAction SilentlyContinue | ForEach-Object {
    if (-not $DryRun) { Remove-Item $_.FullName -Force }
    $script:removed += $_.Length / 1MB
}

Get-ChildItem -Recurse -Filter "*.pyo" -File -ErrorAction SilentlyContinue | ForEach-Object {
    if (-not $DryRun) { Remove-Item $_.FullName -Force }
    $script:removed += $_.Length / 1MB
}

# 4. Remove data files (databases, indexes)
Write-Host "`n💾 Removing ephemeral data..." -ForegroundColor Cyan
Get-ChildItem -Recurse -Filter "*.sqlite" -File -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-SafeItem $_.FullName "SQLite database: $($_.Name)"
}

Get-ChildItem -Recurse -Filter "*.faiss" -File -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-SafeItem $_.FullName "FAISS index: $($_.Name)"
}

Get-ChildItem -Recurse -Filter "*.db" -File -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-SafeItem $_.FullName "Database: $($_.Name)"
}

# 5. Remove logs
Write-Host "`n📄 Removing logs..." -ForegroundColor Cyan
Remove-SafeItem "logs" "Log directory"

Get-ChildItem -Recurse -Filter "*.log" -File -ErrorAction SilentlyContinue | ForEach-Object {
    if (-not $DryRun) { Remove-Item $_.FullName -Force }
    $script:removed += $_.Length / 1MB
}

# 6. Remove temporary files
Write-Host "`n🗑️  Removing temporary files..." -ForegroundColor Cyan
Remove-SafeItem "tmp" "Temp directory"
Remove-SafeItem "temp" "Temp directory"

Get-ChildItem -Recurse -Filter "*.tmp" -File -ErrorAction SilentlyContinue | ForEach-Object {
    if (-not $DryRun) { Remove-Item $_.FullName -Force }
    $script:removed += $_.Length / 1MB
}

# 7. Aggressive mode (remove optional/large files)
if ($Aggressive) {
    Write-Host "`n⚡ AGGRESSIVE MODE: Removing optional files..." -ForegroundColor Red
    
    # Remove source maps
    Get-ChildItem -Recurse -Filter "*.map" -File -ErrorAction SilentlyContinue | ForEach-Object {
        if (-not $DryRun) { Remove-Item $_.FullName -Force }
        $script:removed += $_.Length / 1MB
    }
    
    # Remove test files
    Get-ChildItem -Recurse -Filter "*.test.*" -File -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-SafeItem $_.FullName "Test file: $($_.Name)"
    }
    
    # Remove large documentation
    Get-ChildItem -Recurse -Filter "*.md" -File -ErrorAction SilentlyContinue | Where-Object { $_.Length -gt 100KB } | ForEach-Object {
        Remove-SafeItem $_.FullName "Large doc: $($_.Name)"
    }
}

# Calculate final size
Write-Host "`n📊 Calculating final size..." -ForegroundColor Cyan
$endSize = (Get-ChildItem -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum / 1GB

# Summary
Write-Host "`n" + "="*60 -ForegroundColor Cyan
Write-Host "✨ Cleanup Complete!" -ForegroundColor Green
Write-Host "="*60 -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "`n[DRY RUN MODE - No files were actually removed]`n" -ForegroundColor Yellow
}

Write-Host "`n📊 Statistics:" -ForegroundColor Cyan
Write-Host "  Before:  $([math]::Round($startSize, 2)) GB" -ForegroundColor White
Write-Host "  After:   $([math]::Round($endSize, 2)) GB" -ForegroundColor White
Write-Host "  Removed: $([math]::Round($removed / 1024, 2)) GB" -ForegroundColor Green
Write-Host "  Savings: $([math]::Round(($startSize - $endSize) / $startSize * 100, 1))%`n" -ForegroundColor Green

# Next steps
Write-Host "📝 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Reinstall dependencies: pnpm install --prod" -ForegroundColor White
Write-Host "  2. Start mock service: python services\memory\mock_server.py" -ForegroundColor White
Write-Host "  3. Start UI: cd apps\pantheon && pnpm run dev`n" -ForegroundColor White

if ($Aggressive) {
    Write-Host "⚠️  Note: Aggressive mode removed optional files. Check git status." -ForegroundColor Yellow
}
