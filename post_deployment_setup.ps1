# post_deployment_setup.ps1
# Post-deployment validation and scheduled task setup

[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Step([string]$msg) { Write-Host "==> $msg" -ForegroundColor Cyan }

# --- Paths ---
$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ROOT) { $ROOT = (Get-Location).Path }
$PY = Join-Path $ROOT ".venv\Scripts\python.exe"
$CHROMA = Join-Path $ROOT "data\chromadb"

# --- Step 1: Verify python-dotenv installed ---
Step "Verifying python-dotenv installation"
& $PY -m pip show python-dotenv | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "    ✓ python-dotenv is installed" -ForegroundColor Green
} else {
    Write-Host "    Installing python-dotenv..." -ForegroundColor Yellow
    & $PY -m pip install --quiet python-dotenv
    if ($LASTEXITCODE -ne 0) { throw "Failed to install python-dotenv" }
    Write-Host "    ✓ Installed" -ForegroundColor Green
}

# --- Step 2: Test server imports ---
Step "Testing server imports"
$importTest = @"
from dotenv import load_dotenv
load_dotenv()
from astra.api.app import app
from astra.metrics import MetricsMiddleware, track_tokens
from astra.security import RateLimitMiddleware
print('✓ All imports successful')
print(f'✓ Middleware count: {len(app.user_middleware)}')
routes = [r.path for r in app.routes if hasattr(r, 'path')]
if '/metrics' in routes:
    print('✓ /metrics endpoint registered')
else:
    print('⚠ /metrics endpoint NOT found')
"@

$importTest | & $PY
if ($LASTEXITCODE -ne 0) { throw "Server import test failed" }

# --- Step 3: Check ChromaDB collections ---
Step "Checking ChromaDB collections"
$chromaTest = @"
import chromadb
client = chromadb.PersistentClient(path='$($CHROMA -replace '\\','/')')
collections = client.list_collections()
print(f'Found {len(collections)} collections:')
for coll in collections:
    count = coll.count()
    print(f'  - {coll.name}: {count} items')
    if coll.name == 'astra_memories_m3' and count > 0:
        print('    ✓ BGE-M3 collection has embeddings!')
"@

$chromaTest | & $PY
if ($LASTEXITCODE -ne 0) { Write-Warning "ChromaDB check failed (non-fatal)" }

# --- Step 4: Create scheduled task for memory consolidation ---
Step "Setting up scheduled task for nightly memory consolidation"

$taskName = "ASTRA_MemoryConsolidation"
$taskExists = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($taskExists) {
    Write-Host "    Task already exists. Removing old task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

$action = New-ScheduledTaskAction `
    -Execute $PY `
    -Argument "`"$ROOT\scripts\consolidate_memories.py`" --threshold 0.95" `
    -WorkingDirectory $ROOT

$trigger = New-ScheduledTaskTrigger -Daily -At 3:00AM

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "ASTRA memory consolidation - deduplicates similar memories" `
    -User $env:USERNAME | Out-Null

if ($?) {
    Write-Host "    ✓ Scheduled task created: $taskName" -ForegroundColor Green
    Write-Host "    ✓ Runs daily at 3:00 AM" -ForegroundColor Green
} else {
    Write-Warning "Failed to create scheduled task (requires admin privileges)"
}

# --- Step 5: Token tracking integration instructions ---
Step "Token tracking integration"

Write-Host @"

To enable token metrics in your chat service:

1. Find your chat completion method in: src\astra\services\chat_service.py

2. Add import at top:
   from astra.metrics import track_tokens

3. After LLM response, add:
   track_tokens(
       prompt_tokens=response.usage.prompt_tokens,
       completion_tokens=response.usage.completion_tokens
   )

4. Restart server and check /metrics endpoint for:
   astra_tokens_total{type="prompt"}
   astra_tokens_total{type="completion"}

"@ -ForegroundColor Yellow

# --- Summary ---
Write-Host "`n✅ Post-deployment setup complete!" -ForegroundColor Green
Write-Host @"

Next steps:
1. Start server: $PY $ROOT\run_server.py
2. Test health: curl http://localhost:8080/v1/system/health
3. Check metrics: curl http://localhost:8080/metrics
4. Test rate limiting: 
   for (`$i=1; `$i -le 35; `$i++) { 
     curl http://localhost:8080/ 
     Start-Sleep -Milliseconds 100
   }
5. Run load test:
   `$env:ASTRA_LOAD_CONC=24
   `$env:ASTRA_LOAD_SECS=45
   $PY $ROOT\scripts\load_test.py

"@ -ForegroundColor Cyan
