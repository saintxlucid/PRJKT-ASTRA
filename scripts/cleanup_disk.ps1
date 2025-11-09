# scripts/cleanup_disk.ps1
# Disk space cleanup and inspection for ASTRA

param(
    [switch]$Inspect,
    [switch]$CleanTemp,
    [switch]$CleanPython,
    [switch]$CleanDocker,
    [switch]$CleanLogs,
    [switch]$All
)

$ErrorActionPreference = "Continue"

Write-Host "`n=== ASTRA Disk Space Management ===" -ForegroundColor Cyan

# --- INSPECTION ---
if ($Inspect -or $All) {
    Write-Host "`n[1/5] Inspecting largest files on C:..." -ForegroundColor Yellow
    Write-Host "This may take a few minutes..." -ForegroundColor Gray
    
    try {
        $largeFiles = Get-ChildItem -Path C:\ -Recurse -ErrorAction SilentlyContinue |
            Where-Object { -not $_.PSIsContainer } |
            Sort-Object Length -Descending |
            Select-Object -First 30 FullName, @{Name='MB';Expression={[math]::Round($_.Length/1MB,2)}}
        
        Write-Host "  Top 30 largest files:" -ForegroundColor Green
        $largeFiles | Format-Table -AutoSize
        
        # Calculate total
        $totalMB = ($largeFiles | Measure-Object -Property MB -Sum).Sum
        Write-Host "  Total size of top 30: $([math]::Round($totalMB/1024,2)) GB" -ForegroundColor Cyan
        
    } catch {
        Write-Host "  ✗ Inspection failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# --- TEMP FILES CLEANUP ---
if ($CleanTemp -or $All) {
    Write-Host "`n[2/5] Cleaning temp files..." -ForegroundColor Yellow
    
    $tempPaths = @(
        "$env:TEMP\*",
        "C:\Windows\Temp\*",
        "$env:LOCALAPPDATA\Temp\*"
    )
    
    $freedMB = 0
    foreach ($path in $tempPaths) {
        try {
            $before = (Get-ChildItem -Path $path -Recurse -ErrorAction SilentlyContinue | 
                       Measure-Object -Property Length -Sum).Sum / 1MB
            
            Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
            
            Write-Host "  ✓ Cleaned: $path (~$([math]::Round($before,2)) MB)" -ForegroundColor Green
            $freedMB += $before
        } catch {
            Write-Host "  ⚠ Could not clean: $path" -ForegroundColor Yellow
        }
    }
    
    Write-Host "  Total freed: $([math]::Round($freedMB,2)) MB" -ForegroundColor Cyan
}

# --- PYTHON CACHE CLEANUP ---
if ($CleanPython -or $All) {
    Write-Host "`n[3/5] Cleaning Python caches..." -ForegroundColor Yellow
    
    try {
        # __pycache__ directories
        $pycache = Get-ChildItem -Path "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)" -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue
        $count = ($pycache | Measure-Object).Count
        $pycache | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  ✓ Removed $count __pycache__ directories" -ForegroundColor Green
        
        # .pyc files
        $pyc = Get-ChildItem -Path "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)" -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue
        $count = ($pyc | Measure-Object).Count
        $pyc | Remove-Item -Force -ErrorAction SilentlyContinue
        Write-Host "  ✓ Removed $count .pyc files" -ForegroundColor Green
        
        # pip cache
        if (Get-Command pip -ErrorAction SilentlyContinue) {
            & pip cache purge 2>&1 | Out-Null
            Write-Host "  ✓ Purged pip cache" -ForegroundColor Green
        }
        
    } catch {
        Write-Host "  ✗ Python cleanup failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# --- DOCKER CLEANUP ---
if ($CleanDocker -or $All) {
    Write-Host "`n[4/5] Cleaning Docker resources..." -ForegroundColor Yellow
    
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        try {
            Write-Host "  Pruning Docker system (this may take a while)..." -ForegroundColor Gray
            docker system prune -a --volumes --force 2>&1 | Out-Null
            Write-Host "  ✓ Docker cleanup complete" -ForegroundColor Green
        } catch {
            Write-Host "  ✗ Docker cleanup failed: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "  ⚠ Docker not installed, skipping" -ForegroundColor Yellow
    }
}

# --- LOG FILES CLEANUP ---
if ($CleanLogs -or $All) {
    Write-Host "`n[5/5] Cleaning old logs..." -ForegroundColor Yellow
    
    $logDir = "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\data\logs"
    
    if (Test-Path $logDir) {
        try {
            # Archive logs older than 7 days
            $oldLogs = Get-ChildItem -Path $logDir -File -Recurse | 
                       Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) }
            
            if ($oldLogs) {
                $archivePath = "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\data\logs_archive_$(Get-Date -Format 'yyyy-MM-dd').zip"
                Compress-Archive -Path $oldLogs.FullName -DestinationPath $archivePath -Force
                $oldLogs | Remove-Item -Force
                Write-Host "  ✓ Archived and removed $(($oldLogs | Measure-Object).Count) old log files" -ForegroundColor Green
            } else {
                Write-Host "  ✓ No old logs to clean" -ForegroundColor Green
            }
            
        } catch {
            Write-Host "  ✗ Log cleanup failed: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "  ⚠ Log directory not found" -ForegroundColor Yellow
    }
}

# --- SUMMARY ---
Write-Host "`n=== Summary ===" -ForegroundColor Cyan

$drive = Get-PSDrive C
$freeMB = [math]::Round($drive.Free / 1GB, 2)
$totalMB = [math]::Round(($drive.Free + $drive.Used) / 1GB, 2)
$usedMB = [math]::Round($drive.Used / 1GB, 2)

Write-Host "C: Drive Status:" -ForegroundColor Green
Write-Host "  Free: $freeMB GB" -ForegroundColor White
Write-Host "  Used: $usedMB GB" -ForegroundColor White
Write-Host "  Total: $totalMB GB" -ForegroundColor White

if ($freeMB -lt 2) {
    Write-Host "`n⚠ WARNING: Less than 2GB free! BGE-M3 migration blocked." -ForegroundColor Red
    Write-Host "Recommended: Move large model files to external storage" -ForegroundColor Yellow
} elseif ($freeMB -lt 5) {
    Write-Host "`n⚠ WARNING: Less than 5GB free. Consider cleanup." -ForegroundColor Yellow
} else {
    Write-Host "`n✓ Sufficient disk space available" -ForegroundColor Green
}

Write-Host "`nUsage:" -ForegroundColor Cyan
Write-Host "  .\scripts\cleanup_disk.ps1 -Inspect        # Inspect only" -ForegroundColor Gray
Write-Host "  .\scripts\cleanup_disk.ps1 -CleanTemp      # Clean temp files" -ForegroundColor Gray
Write-Host "  .\scripts\cleanup_disk.ps1 -CleanPython    # Clean Python caches" -ForegroundColor Gray
Write-Host "  .\scripts\cleanup_disk.ps1 -CleanDocker    # Clean Docker" -ForegroundColor Gray
Write-Host "  .\scripts\cleanup_disk.ps1 -CleanLogs      # Clean old logs" -ForegroundColor Gray
Write-Host "  .\scripts\cleanup_disk.ps1 -All            # Do everything" -ForegroundColor Gray
