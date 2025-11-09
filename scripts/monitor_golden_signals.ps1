#!/usr/bin/env pwsh
# ASTRA v1.0.0 - Golden Signals Monitoring (30-minute watch)
# Monitors key metrics after deployment

param(
    [int]$DurationMinutes = 30,
    [int]$CheckIntervalSeconds = 60
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       ASTRA CORE v1.0.0 - GOLDEN SIGNALS MONITORING        ║" -ForegroundColor Cyan
Write-Host "║              30-Minute Post-Deployment Watch                ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "Duration: $DurationMinutes minutes | Check Interval: $CheckIntervalSeconds seconds" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop monitoring" -ForegroundColor Gray
Write-Host ""

$startTime = Get-Date
$endTime = $startTime.AddMinutes($DurationMinutes)
$checkCount = 0

# Alert thresholds
$thresholds = @{
    ApiLatencyP95Warn = 1.2
    ApiLatencyP95Critical = 2.0
    LlmLatencyP95Warn = 1.5
    LlmLatencyP95Critical = 2.0
    CacheHitRateWarn = 0.20
    CacheHitRateTarget = 0.25
    QueueDepthWarn = 50
    QueueDepthCritical = 100
    LlmFailureRate = 5  # per 5 minutes
}

function Get-MetricValue {
    param($metricsText, $metricName)
    
    $pattern = "$metricName\s+(\d+\.?\d*)"
    if ($metricsText -match $pattern) {
        return [double]$matches[1]
    }
    return $null
}

function Get-HistogramPercentile {
    param($metricsText, $metricName, $percentile)
    
    # Look for histogram bucket with quantile label
    $pattern = "$metricName\{.*quantile=`"0\.$percentile`".*\}\s+(\d+\.?\d*)"
    if ($metricsText -match $pattern) {
        return [double]$matches[1]
    }
    return $null
}

function Format-Status {
    param($value, $threshold, [switch]$HigherIsBetter)
    
    if ($null -eq $value) { return "N/A" }
    
    $status = if ($HigherIsBetter) {
        if ($value -ge $threshold) { "✓" } else { "⚠" }
    } else {
        if ($value -le $threshold) { "✓" } else { "⚠" }
    }
    
    return "$status $value"
}

Write-Host "TARGETS:" -ForegroundColor Cyan
Write-Host "  • API Latency (p95):     ≤ $($thresholds.ApiLatencyP95Warn)s" -ForegroundColor Gray
Write-Host "  • LLM Latency (p95):     ≤ $($thresholds.LlmLatencyP95Warn)s" -ForegroundColor Gray
Write-Host "  • Cache Hit Rate:        ≥ $($thresholds.CacheHitRateTarget * 100)%" -ForegroundColor Gray
Write-Host "  • Queue Depth:           < $($thresholds.QueueDepthWarn)" -ForegroundColor Gray
Write-Host "  • LLM Failures:          Steady (no spikes)" -ForegroundColor Gray
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$previousFailures = $null

while ((Get-Date) -lt $endTime) {
    $checkCount++
    $now = Get-Date
    $elapsed = $now - $startTime
    $remaining = $endTime - $now
    
    Write-Host "[$($now.ToString('HH:mm:ss'))] Check $checkCount | Elapsed: $($elapsed.ToString('mm\:ss')) | Remaining: $($remaining.ToString('mm\:ss'))" -ForegroundColor Yellow
    
    try {
        # Fetch metrics
        $metricsResponse = Invoke-WebRequest -Uri "http://localhost:8080/metrics" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        $metricsText = $metricsResponse.Content
        
        # Extract metrics
        $requestsTotal = Get-MetricValue $metricsText "astra_requests_total"
        $llmFailures = Get-MetricValue $metricsText "astra_llm_failures_total"
        $cacheHits = Get-MetricValue $metricsText "astra_cache_hits_total"
        $cacheMisses = Get-MetricValue $metricsText "astra_cache_misses_total"
        
        # Calculate derived metrics
        $cacheTotal = $cacheHits + $cacheMisses
        $cacheHitRate = if ($cacheTotal -gt 0) { $cacheHits / $cacheTotal } else { 0 }
        
        # Check for failure spikes
        $failureSpike = $false
        if ($null -ne $previousFailures -and $null -ne $llmFailures) {
            $failureDelta = $llmFailures - $previousFailures
            if ($failureDelta -ge $thresholds.LlmFailureRate) {
                $failureSpike = $true
            }
        }
        $previousFailures = $llmFailures
        
        # Display metrics
        Write-Host "  Requests Total:     $requestsTotal" -ForegroundColor White
        Write-Host "  LLM Failures:       $llmFailures $(if ($failureSpike) { '⚠ SPIKE' } else { '✓ Stable' })" -ForegroundColor $(if ($failureSpike) { "Red" } else { "Green" })
        Write-Host "  Cache Hits:         $cacheHits" -ForegroundColor White
        Write-Host "  Cache Misses:       $cacheMisses" -ForegroundColor White
        Write-Host "  Cache Hit Rate:     $([math]::Round($cacheHitRate * 100, 1))% $(if ($cacheHitRate -ge $thresholds.CacheHitRateTarget) { '✓ Target' } elseif ($cacheHitRate -ge $thresholds.CacheHitRateWarn) { '⚠ Low' } else { '✗ Very Low' })" -ForegroundColor $(if ($cacheHitRate -ge $thresholds.CacheHitRateTarget) { "Green" } elseif ($cacheHitRate -ge $thresholds.CacheHitRateWarn) { "Yellow" } else { "Red" })
        
        # Health check
        $healthResponse = Invoke-WebRequest -Uri "http://localhost:8080/v1/system/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        $health = $healthResponse.Content | ConvertFrom-Json
        
        Write-Host "  Health Status:      $($health.status) ✓" -ForegroundColor Green
        
        # Check for errors in recent logs (if log file exists)
        $logPath = "data\logs\astra.log"
        if (Test-Path $logPath) {
            $recentErrors = Get-Content $logPath -Tail 100 | Select-String -Pattern "ERROR|CRITICAL" | Measure-Object
            if ($recentErrors.Count -gt 0) {
                Write-Host "  Recent Errors:      $($recentErrors.Count) ⚠ Check logs" -ForegroundColor Yellow
            } else {
                Write-Host "  Recent Errors:      0 ✓" -ForegroundColor Green
            }
        }
        
    } catch {
        Write-Host "  ✗ Error fetching metrics: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host ""
    
    # Wait for next check
    if ((Get-Date) -lt $endTime) {
        Start-Sleep -Seconds $CheckIntervalSeconds
    }
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "✓ Monitoring Complete - $DurationMinutes minutes elapsed" -ForegroundColor Green
Write-Host ""
Write-Host "NEXT ACTIONS:" -ForegroundColor Cyan
Write-Host "  1. Review metrics for anomalies" -ForegroundColor White
Write-Host "  2. Check Prometheus AlertManager for triggered alerts" -ForegroundColor White
Write-Host "  3. Review logs at data\logs\astra.log" -ForegroundColor White
Write-Host "  4. If all nominal, proceed with Phase-2 enhancements" -ForegroundColor White
Write-Host ""
Write-Host "See ops/RUNBOOK.md for detailed troubleshooting." -ForegroundColor Yellow
Write-Host ""
