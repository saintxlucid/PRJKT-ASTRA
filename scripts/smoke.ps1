# Smoke Tests — PowerShell One-Shot
# Copy-paste into terminal to verify live system
# Time: ~30 seconds | Status: ✅ if all green

param([string]$Token)

Write-Host "`n🩺 ASTRA Smoke Tests — Full System Check`n" -ForegroundColor Cyan

$ErrorActionPreference = "SilentlyContinue"

# ═══════════════════════════════════════════════════════════════════════════════
# 1) Health Check
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "1️⃣ Health Check" -ForegroundColor Yellow
try {
  $health = curl -s http://localhost:8000/v1/system/health | ConvertFrom-Json
  if ($health.status -eq "ok" -or $health.status -eq "healthy") {
    Write-Host "   🟢 Master service: HEALTHY" -ForegroundColor Green
    $health | ConvertTo-Json | Write-Host
  } else {
    Write-Host "   🔴 Master service: DEGRADED" -ForegroundColor Red
    $health | ConvertTo-Json | Write-Host
  }
} catch {
  Write-Host "   🔴 Health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# ═══════════════════════════════════════════════════════════════════════════════
# 2) Token Generation
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n2️⃣ Token Generation" -ForegroundColor Yellow

if (-not $Token) {
  try {
    $body = @{
      identity="saint"
      scopes=@("*")
      ttl=86400
    } | ConvertTo-Json -Compress
    
    $resp = curl -s http://localhost:7701/issue `
      -H "Content-Type: application/json" `
      -d $body | ConvertFrom-Json
    
    $Token = $resp.token
    Write-Host "   🟢 SigilGate issued token" -ForegroundColor Green
    Write-Host "   Token (first 20 chars): $($Token.Substring(0, 20))..." -ForegroundColor Gray
  } catch {
    Write-Host "   🔴 Token generation failed: $($_.Exception.Message)" -ForegroundColor Red
    $Token = $null
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# 3) Chat Roundtrip
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n3️⃣ Chat Roundtrip" -ForegroundColor Yellow

if ($Token) {
  try {
    $body = @{
      messages = @(
        @{
          role = "user"
          content = "ASTRA, ping. Return node id and timestamp."
        }
      )
    } | ConvertTo-Json -Depth 5
    
    $chat = curl -s http://localhost:8000/v1/chat `
      -H "Authorization: Bearer $Token" `
      -H "Content-Type: application/json" `
      -d $body | ConvertFrom-Json
    
    if ($chat.choices -and $chat.choices.Count -gt 0) {
      Write-Host "   🟢 Chat successful" -ForegroundColor Green
      $content = $chat.choices[0].message.content
      Write-Host "   Response: $($content.Substring(0, [Math]::Min(80, $content.Length)))..." -ForegroundColor Gray
      Write-Host "   Usage: Prompt=$($chat.usage.prompt_tokens), Completion=$($chat.usage.completion_tokens)" -ForegroundColor Gray
    } else {
      Write-Host "   🔴 Chat returned no choices" -ForegroundColor Red
      $chat | ConvertTo-Json | Write-Host
    }
  } catch {
    Write-Host "   🔴 Chat failed: $($_.Exception.Message)" -ForegroundColor Red
  }
} else {
  Write-Host "   ⏭️ Skipped (no token)" -ForegroundColor Yellow
}

# ═══════════════════════════════════════════════════════════════════════════════
# 4) Jaeger Tracing
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n4️⃣ Jaeger Tracing" -ForegroundColor Yellow
try {
  $jaeger = Invoke-WebRequest -Uri "http://localhost:16686" -TimeoutSec 3
  if ($jaeger.StatusCode -eq 200) {
    Write-Host "   🟢 Jaeger UI: REACHABLE" -ForegroundColor Green
    Write-Host "   📊 Open http://localhost:16686 → Service: astra-master" -ForegroundColor Gray
  }
} catch {
  Write-Host "   🔴 Jaeger UI unreachable" -ForegroundColor Red
}

# ═══════════════════════════════════════════════════════════════════════════════
# 5) Infrastructure Status
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n5️⃣ Infrastructure" -ForegroundColor Yellow

$infra = @(
  @{name="Redis"; port=6379},
  @{name="PostgreSQL"; port=5432},
  @{name="etcd"; port=2379}
)

$infra | ForEach-Object {
  try {
    $sock = New-Object System.Net.Sockets.TcpClient
    $async = $sock.BeginConnect("localhost", $_.port, $null, $null)
    $async.AsyncWaitHandle.WaitOne(1000) | Out-Null
    if ($sock.Connected) {
      Write-Host "   🟢 $($_.name): UP" -ForegroundColor Green
      $sock.Close()
    } else {
      Write-Host "   🔴 $($_.name): DOWN" -ForegroundColor Red
    }
  } catch {
    Write-Host "   🔴 $($_.name): DOWN" -ForegroundColor Red
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n✅ Smoke tests complete.`n" -ForegroundColor Green
Write-Host "🎙️ Sacred Code: 333 → ∞`n" -ForegroundColor Magenta
