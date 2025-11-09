#!/usr/bin/env pwsh
# Unblock BGE-M3 Migration - Disk Space Cleanup
# Safely clears temp files and caches to free 2-3 GB

$ErrorActionPreference = "Stop"

Write-Host "🧹 DISK CLEANUP FOR BGE-M3 MIGRATION" -ForegroundColor Cyan
Write-Host "=" * 60
Write-Host ""

# Check available space before
$beforeSpace = (Get-PSDrive C).Free / 1GB
Write-Host "Current free space on C: $([math]::Round($beforeSpace, 2)) GB" -ForegroundColor Yellow
Write-Host ""

if ($beforeSpace -lt 2) {
    Write-Host "⚠️  Less than 2 GB free. Cleaning temp files..." -ForegroundColor Yellow
} else {
    Write-Host "✓ Sufficient space available, but cleaning anyway for good measure..." -ForegroundColor Green
}

Write-Host ""

# Function to safely delete with error handling
function Remove-SafeRecursive {
    param($Path, $Description)
    
    if (Test-Path $Path) {
        Write-Host "  Cleaning $Description..." -ForegroundColor Cyan
        try {
            Get-ChildItem -Path $Path -Recurse -Force -ErrorAction SilentlyContinue | 
                Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
            Write-Host "    ✓ Cleaned" -ForegroundColor Green
        } catch {
            Write-Host "    ⚠️  Partial cleanup (some files in use)" -ForegroundColor Yellow
        }
    }
}

# 1. Windows Temp
Remove-SafeRecursive "$env:LOCALAPPDATA\Temp" "Windows local temp"
Remove-SafeRecursive "$env:TEMP" "Windows user temp"

# 2. Python pip cache
Remove-SafeRecursive "$env:USERPROFILE\.cache\pip" "Python pip cache"

# 3. HuggingFace cache (temp files only)
$hfCachePath = "$env:USERPROFILE\.cache\huggingface\hub"
if (Test-Path $hfCachePath) {
    Write-Host "  Cleaning HuggingFace temp files..." -ForegroundColor Cyan
    try {
        Get-ChildItem -Path $hfCachePath -Filter "*.tmp" -Recurse -Force -ErrorAction SilentlyContinue |
            Remove-Item -Force -ErrorAction SilentlyContinue
        Get-ChildItem -Path $hfCachePath -Filter "*.incomplete" -Recurse -Force -ErrorAction SilentlyContinue |
            Remove-Item -Force -ErrorAction SilentlyContinue
        Write-Host "    ✓ Cleaned temp files only (keeping models)" -ForegroundColor Green
    } catch {
        Write-Host "    ⚠️  Partial cleanup" -ForegroundColor Yellow
    }
}

# 4. Project-specific cleanup
$projectRoot = Split-Path -Parent $PSScriptRoot
$projectCaches = @(
    "$projectRoot\.pytest_cache",
    "$projectRoot\.ruff_cache",
    "$projectRoot\.mypy_cache",
    "$projectRoot\htmlcov",
    "$projectRoot\build"
)

foreach ($cache in $projectCaches) {
    if (Test-Path $cache) {
        Write-Host "  Cleaning $(Split-Path -Leaf $cache)..." -ForegroundColor Cyan
        Remove-Item -Path $cache -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "    ✓ Cleaned" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "=" * 60

# Check space after
$afterSpace = (Get-PSDrive C).Free / 1GB
$freed = $afterSpace - $beforeSpace

Write-Host "Cleanup complete!" -ForegroundColor Green
Write-Host "  Before: $([math]::Round($beforeSpace, 2)) GB free" -ForegroundColor Cyan
Write-Host "  After:  $([math]::Round($afterSpace, 2)) GB free" -ForegroundColor Cyan
Write-Host "  Freed:  $([math]::Round($freed, 2)) GB" -ForegroundColor Green
Write-Host ""

if ($afterSpace -ge 3) {
    Write-Host "✅ Ready for BGE-M3 migration! (~2 GB needed)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next step: Run BGE-M3 re-embed script" -ForegroundColor Yellow
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\reembed_bge_m3.ps1" -ForegroundColor Cyan
} else {
    Write-Host "⚠️  Still tight on space. Consider:" -ForegroundColor Yellow
    Write-Host "  - Clear browser cache" -ForegroundColor Cyan
    Write-Host "  - Remove old downloads" -ForegroundColor Cyan
    Write-Host "  - Run Windows Disk Cleanup" -ForegroundColor Cyan
    Write-Host "  - Move some files to another drive" -ForegroundColor Cyan
}
