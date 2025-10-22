# Windows Service Operations

This guide covers operational procedures for ASTRA's Windows auto-ingestion service.

## Service Overview

The auto-ingestion service monitors `data/ingest/inbox` for new documents, processes them, and moves them to `data/ingest/processed`.

### Key Features

- File system watching
- Automatic document processing
- Nightly maintenance
- Health monitoring
- Automatic recovery

## Service Management

### Starting/Stopping

```powershell
# Start service
Start-Service ASTRAIngest

# Stop service
Stop-Service ASTRAIngest

# Restart service
Restart-Service ASTRAIngest
```

### Status Checks

```powershell
# Check service status
Get-Service ASTRAIngest

# View recent events
Get-EventLog -LogName Application -Source ASTRAIngest -Newest 20
```

## Health Monitoring

### Health Checks

1. Service Status:
   ```powershell
   $service = Get-Service ASTRAIngest
   if ($service.Status -eq "Running") {
       Write-Host "Service healthy"
   }
   ```

2. Process Health:
   ```powershell
   $process = Get-Process ASTRAIngest -ErrorAction SilentlyContinue
   if ($process) {
       Write-Host "Process running, PID: $($process.Id)"
   }
   ```

3. File System Check:
   ```powershell
   $watchPath = "data/ingest/inbox"
   if (Test-Path $watchPath) {
       Write-Host "Watch directory accessible"
   }
   ```

### Readiness Probes

The service implements readiness checks:

1. Dependencies:
   - Qdrant connection
   - GPU availability
   - Disk space

2. Resource Status:
   - Memory usage
   - CPU utilization
   - Queue depth

3. System State:
   - Cache status
   - Index health
   - Processing backlog

## Log Management

### Log Locations

1. Service Logs:
   - `data/logs/service.log`
   - Windows Event Log
   - ETW events

2. Processing Logs:
   - `data/logs/ingestion.jsonl`
   - `data/logs/telemetry.jsonl`
   - `data/logs/errors.jsonl`

### Log Rotation

Automatic rotation based on:
- Size (1MB per file)
- Age (7 days retention)
- Maximum files (5 per type)

### Log Analysis

```powershell
# Get recent errors
Get-Content data/logs/errors.jsonl -Tail 50 |
    ConvertFrom-Json |
    Where-Object { $_.level -eq "ERROR" }

# Monitor ingestion
Get-Content data/logs/ingestion.jsonl -Wait |
    ConvertFrom-Json
```

## Maintenance Procedures

### Nightly Tasks

The service automatically performs:

1. Index Maintenance:
   - VACUUM operations
   - Optimization passes
   - Health checks

2. Cache Management:
   - Clear stale entries
   - Verify integrity
   - Update statistics

3. Resource Cleanup:
   - Remove temporary files
   - Archive old logs
   - Update metrics

### Manual Maintenance

1. Force Cache Clear:
   ```powershell
   Stop-Service ASTRAIngest
   Remove-Item data/cache/* -Recurse
   Start-Service ASTRAIngest
   ```

2. Reset Processing:
   ```powershell
   Stop-Service ASTRAIngest
   Move-Item data/ingest/processing/* data/ingest/inbox/
   Start-Service ASTRAIngest
   ```

3. Verify Directories:
   ```powershell
   $paths = @(
       "data/ingest/inbox",
       "data/ingest/processing",
       "data/ingest/processed",
       "data/ingest/failed"
   )
   foreach ($path in $paths) {
       if (-not (Test-Path $path)) {
           New-Item -ItemType Directory -Path $path
       }
   }
   ```

## Troubleshooting

### Common Issues

1. Service Won't Start:
   - Check dependencies
   - Verify permissions
   - Review event logs

2. Processing Stuck:
   - Check resource usage
   - Clear processing directory
   - Restart service

3. High Resource Usage:
   - Monitor queue depth
   - Check batch sizes
   - Review concurrent operations

### Recovery Steps

1. Basic Recovery:
   ```powershell
   Restart-Service ASTRAIngest
   ```

2. Full Reset:
   ```powershell
   Stop-Service ASTRAIngest
   Clear-Content data/logs/*
   Remove-Item data/cache/* -Recurse
   Start-Service ASTRAIngest
   ```

3. Emergency Shutdown:
   ```powershell
   Stop-Service ASTRAIngest -Force
   Get-Process ASTRAIngest | Stop-Process -Force
   ```

## Performance Monitoring

### Key Metrics

1. Processing Stats:
   - Documents/hour
   - Average processing time
   - Queue depth

2. Resource Usage:
   - Memory consumption
   - CPU utilization
   - Disk I/O

3. Health Indicators:
   - Error rate
   - Recovery counts
   - Cache hit ratio

### Performance Tuning

1. Configuration Parameters:
   - Batch size
   - Queue limits
   - Thread count

2. Resource Allocation:
   - Memory limits
   - CPU affinity
   - I/O priority

3. Monitoring Thresholds:
   - Warning levels
   - Critical limits
   - Auto-recovery triggers