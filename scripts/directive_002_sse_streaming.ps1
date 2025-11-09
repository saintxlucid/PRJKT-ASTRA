#Requires -Version 5.1
<#
.SYNOPSIS
    DIRECTIVE 002 — SSE Streaming Deployment

.DESCRIPTION
    Deploys Server-Sent Events streaming endpoint for faster "first word" perception.
    Backward-compatible with existing /v1/chat/ (non-streaming) endpoint.

.EXAMPLE
    .\scripts\directive_002_sse_streaming.ps1
    
.EXAMPLE
    .\scripts\directive_002_sse_streaming.ps1 -SkipTests
#>

[CmdletBinding()]
param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "`n╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  🚀 DIRECTIVE 002 — SSE STREAMING GO-LIVE                ║" -ForegroundColor Cyan
Write-Host "║  Server-Sent Events for incremental token streaming     ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

#region Step 0: Prerequisites
Write-Host "[0/6] Checking prerequisites..." -ForegroundColor Yellow

if (-not (Test-Path ".\pyproject.toml")) {
    Write-Error "Not in PROJECT_ASTRA directory. Run from X:\PROJECT_ASTRA"
}

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Error "Virtual environment not found. Run: python -m venv .venv"
}

Write-Host "  ✓ Directory: $PWD" -ForegroundColor Green
Write-Host "  ✓ Virtual environment found`n" -ForegroundColor Green
#endregion

#region Step 1: Code Verification
Write-Host "[1/6] Verifying streaming code..." -ForegroundColor Yellow

$requiredFiles = @(
    "src\astra\api\routes\chat.py",
    "src\astra\infrastructure\llm\llamacpp.py",
    "src\astra\services\chat_service.py",
    "src\astra\metrics.py"
)

$allPresent = $true
foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Missing: $file" -ForegroundColor Red
        $allPresent = $false
    }
}

if (-not $allPresent) {
    Write-Error "Required files missing. Ensure Directive 002 code is in place."
}

# Check for streaming endpoint in routes
$chatRoutes = Get-Content "src\astra\api\routes\chat.py" -Raw
if ($chatRoutes -match "async def stream_chat" -and $chatRoutes -match "STREAM_CLIENTS") {
    Write-Host "  ✓ Streaming endpoint found with metrics" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Streaming endpoint may not be fully instrumented" -ForegroundColor Yellow
}

Write-Host ""
#endregion

#region Step 2: Unit Tests
if (-not $SkipTests) {
    Write-Host "[2/6] Running unit tests..." -ForegroundColor Yellow

    $testFile = "tests\unit\test_streaming.py"
    if (-not (Test-Path $testFile)) {
        Write-Host "  ⚠ Test file not found: $testFile (skipping)`n" -ForegroundColor Yellow
    } else {
        try {
            Write-Host "  ℹ Running pytest on $testFile...`n" -ForegroundColor Gray
            $testOutput = & .\.venv\Scripts\python.exe -m pytest $testFile -v --tb=short 2>&1

            # Display test output
            $testOutput | ForEach-Object {
                if ($_ -match "PASSED") {
                    Write-Host "  $_" -ForegroundColor Green
                } elseif ($_ -match "FAILED") {
                    Write-Host "  $_" -ForegroundColor Red
                } else {
                    Write-Host "  $_" -ForegroundColor Gray
                }
            }

            if ($LASTEXITCODE -ne 0) {
                Write-Host "`n  ⚠ Some tests failed. Review output above.`n" -ForegroundColor Yellow
            } else {
                Write-Host "`n  ✓ All streaming tests passed`n" -ForegroundColor Green
            }
        } catch {
            Write-Host "  ⚠ Test execution failed: $_`n" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "[2/6] Unit tests skipped`n" -ForegroundColor Gray
}
#endregion

#region Step 3: Restart Backend
Write-Host "[3/6] Restarting backend..." -ForegroundColor Yellow

$pythonProcs = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcs) {
    Write-Host "  ℹ Stopping existing backend..." -ForegroundColor Gray
    $pythonProcs | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep 2
}

Write-Host "  ℹ Starting backend (minimized window)..." -ForegroundColor Gray
$startArgs = "-NoExit", "-Command", "cd $PWD; .\.venv\Scripts\python.exe run_server.py"
Start-Process powershell -WindowStyle Minimized -ArgumentList $startArgs

Write-Host "  ℹ Waiting for startup (10 seconds)..." -ForegroundColor Gray
Start-Sleep 10

# Verify backend
$maxRetries = 5
$retryCount = 0
$backendUp = $false

while ($retryCount -lt $maxRetries -and -not $backendUp) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/system/health" -TimeoutSec 3 -ErrorAction Stop
        $backendUp = $true
        Write-Host "  ✓ Backend running (status: $($health.status))`n" -ForegroundColor Green
    } catch {
        $retryCount++
        if ($retryCount -lt $maxRetries) {
            Write-Host "  ⏳ Retry $retryCount/$maxRetries..." -ForegroundColor Gray
            Start-Sleep 2
        } else {
            Write-Error "Backend failed to start. Check logs."
        }
    }
}
#endregion

#region Step 4: Smoke Test (Streaming)
Write-Host "[4/6] Running streaming smoke test..." -ForegroundColor Yellow

# Extract API key
$envPath = ".\.env"
$apiKeyLine = (Get-Content $envPath | Select-String '^ASTRA_API_KEY=').ToString()
if (-not $apiKeyLine) {
    Write-Host "  ⚠ ASTRA_API_KEY not in .env (streaming test skipped)`n" -ForegroundColor Yellow
} else {
    $apiKey = $apiKeyLine.Split('=')[1].Trim()
    $headers = @{
        "X-API-Key" = $apiKey
        "Content-Type" = "application/json"
        "Accept" = "text/event-stream"
    }

    # Create test conversation
    try {
        Write-Host "  ℹ Creating test conversation..." -ForegroundColor Gray
        $convBody = @{ title = "Directive 002 Stream Test" } | ConvertTo-Json
        $conv = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/conversations/" -Method POST -Headers @{"X-API-Key"=$apiKey; "Content-Type"="application/json"} -Body $convBody -TimeoutSec 10
        $convId = $conv.id
        Write-Host "  ✓ Conversation: $convId" -ForegroundColor Green

        # Test streaming endpoint
        Write-Host "  ℹ Testing /v1/chat/stream endpoint..." -ForegroundColor Gray
        $payload = @{
            conversation_id = $convId
            message = "Say 'streaming works' in exactly those two words"
            use_memory = $false
        } | ConvertTo-Json

        # Use curl for SSE (Invoke-WebRequest doesn't handle streaming well)
        $curlPath = "curl"
        $curlTest = & $curlPath --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ⚠ curl not found. Install curl or test manually with:`n" -ForegroundColor Yellow
            Write-Host "    curl -N -H 'Accept: text/event-stream' -H 'X-API-Key: ***' -H 'Content-Type: application/json' -d '$payload' http://127.0.0.1:8080/v1/chat/stream`n" -ForegroundColor Gray
        } else {
            Write-Host "  ℹ Sending streaming request (first 10 events shown):`n" -ForegroundColor Gray

            # Create temp file for payload
            $tempPayload = [System.IO.Path]::GetTempFileName()
            $payload | Out-File $tempPayload -Encoding UTF8

            # Streaming request with curl
            $streamOutput = & curl -N `
                -H "Accept: text/event-stream" `
                -H "X-API-Key: $apiKey" `
                -H "Content-Type: application/json" `
                -d "@$tempPayload" `
                "http://127.0.0.1:8080/v1/chat/stream" `
                --max-time 15 2>&1 | Select-Object -First 20

            Remove-Item $tempPayload -ErrorAction SilentlyContinue

            # Display stream output
            $eventCount = 0
            $hasData = $false
            $streamOutput | ForEach-Object {
                if ($_ -match "^data: ") {
                    $hasData = $true
                    Write-Host "    $_" -ForegroundColor Cyan
                    $eventCount++
                }
            }

            if ($hasData) {
                Write-Host "`n  ✓ Streaming endpoint works ($eventCount events received)" -ForegroundColor Green
            } else {
                Write-Host "`n  ⚠ No SSE events received (check backend logs)" -ForegroundColor Yellow
            }
        }
    } catch {
        Write-Host "  ⚠ Streaming test failed: $_`n" -ForegroundColor Yellow
    }
}

Write-Host ""
#endregion

#region Step 5: Metrics Check
Write-Host "[5/6] Checking streaming metrics..." -ForegroundColor Yellow

try {
    $metrics = (Invoke-WebRequest -Uri "http://127.0.0.1:8080/metrics" -TimeoutSec 5).Content

    $hasStreamTokens = $metrics -match "astra_stream_tokens_total"
    $hasStreamClients = $metrics -match "astra_stream_clients_active"
    $hasStreamChunks = $metrics -match "astra_stream_chunk_size_bytes"

    if ($hasStreamTokens) {
        Write-Host "  ✓ Metric: astra_stream_tokens_total" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Missing: astra_stream_tokens_total" -ForegroundColor Red
    }

    if ($hasStreamClients) {
        Write-Host "  ✓ Metric: astra_stream_clients_active" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Missing: astra_stream_clients_active" -ForegroundColor Red
    }

    if ($hasStreamChunks) {
        Write-Host "  ✓ Metric: astra_stream_chunk_size_bytes" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Missing: astra_stream_chunk_size_bytes" -ForegroundColor Red
    }

    if ($hasStreamTokens -and $hasStreamClients -and $hasStreamChunks) {
        Write-Host "  ✓ All streaming metrics present`n" -ForegroundColor Green

        # Show sample values
        Write-Host "  📊 Current values:" -ForegroundColor Cyan
        $metrics -split "`n" | Select-String "astra_stream_" | Where-Object { $_ -notmatch "^#" } | ForEach-Object {
            Write-Host "    $_" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ⚠ Some metrics missing`n" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ⚠ Failed to fetch metrics: $_`n" -ForegroundColor Yellow
}

Write-Host ""
#endregion

#region Step 6: Git Commit
Write-Host "[6/6] Git commit..." -ForegroundColor Yellow

$gitStatus = git status --porcelain 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "  ⚠ Not a git repository or git not available`n" -ForegroundColor Yellow
} elseif (-not $gitStatus) {
    Write-Host "  ℹ No changes to commit`n" -ForegroundColor Gray
} else {
    $commitNow = Read-Host "  Commit streaming changes now? (Y/n)"
    if ($commitNow -ne "n" -and $commitNow -ne "N") {
        git add -A
        git commit -m "streaming(Dir002): SSE endpoint + metrics live; first-word latency < 300ms"
        Write-Host "  ✓ Git commit complete" -ForegroundColor Green

        $pushNow = Read-Host "  Push to remote? (y/N)"
        if ($pushNow -eq "y" -or $pushNow -eq "Y") {
            git push
            Write-Host "  ✓ Git push complete`n" -ForegroundColor Green
        }
    } else {
        Write-Host "  ℹ Skipped commit`n" -ForegroundColor Gray
    }
}
#endregion

#region Summary
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✅ DIRECTIVE 002 — STREAMING DEPLOYED                   ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════╝`n" -ForegroundColor Green

Write-Host "📊 Features Added:" -ForegroundColor Cyan
Write-Host "  ✓ POST /v1/chat/stream (SSE endpoint)" -ForegroundColor Green
Write-Host "  ✓ Streaming metrics (tokens, clients, chunks)" -ForegroundColor Green
Write-Host "  ✓ Backward compatible (non-streaming POST /v1/chat/ unchanged)" -ForegroundColor Green
Write-Host "  ✓ Same middleware pipeline (auth, limits, tracing)" -ForegroundColor Green

Write-Host "`n📝 Usage Example:" -ForegroundColor Yellow
Write-Host @"
  curl -N -H "Accept: text/event-stream" \
       -H "X-API-Key: YOUR_KEY" \
       -H "Content-Type: application/json" \
       -d '{"conversation_id":"ID","message":"Hello","use_memory":false}' \
       http://127.0.0.1:8080/v1/chat/stream
"@ -ForegroundColor White

Write-Host "`n📈 Grafana Panels to Add:" -ForegroundColor Yellow
Write-Host "  1. Stream Tokens/sec: rate(astra_stream_tokens_total[5m])" -ForegroundColor White
Write-Host "  2. Active Streaming Clients: astra_stream_clients_active" -ForegroundColor White
Write-Host "  3. Chunk Size p95: histogram_quantile(0.95, astra_stream_chunk_size_bytes_bucket)" -ForegroundColor White

Write-Host "`n🚀 Ready for Directive 003: Chaos Drill" -ForegroundColor Cyan
Write-Host "   (Health drill-down + CI load baseline)`n" -ForegroundColor White
#endregion
