# ⚙️ ASTRA Sanity Sweep — Health Check + Token + Chat Smoke Test
# Copy-paste into PowerShell to verify all systems operational
# Time: ~30 seconds | Status: ✅ if all lights green

$ErrorActionPreference = "SilentlyContinue"
Write-Host "`n🚦 ASTRA Sanity Sweep — starting..." -ForegroundColor Cyan

# ═══════════════════════════════════════════════════════════════════════════════
# Helper: Read .env file
# ═══════════════════════════════════════════════════════════════════════════════
function Read-DotEnv($path) {
  $out = @{}
  if (Test-Path $path) {
    Get-Content $path | Where-Object {$_ -and $_ -notmatch '^\s*#'} |
      ForEach-Object {
        $kv = $_ -split '=', 2
        if ($kv.Length -eq 2) { $out[$kv[0].Trim()] = $kv[1].Trim() }
      }
  }
  return $out
}

# ═══════════════════════════════════════════════════════════════════════════════
# 0) Ensure we're in repo root
# ═══════════════════════════════════════════════════════════════════════════════
if (-not (Test-Path ".env")) {
  Write-Host "📍 Not in repo root, navigating..." -ForegroundColor Yellow
  Set-Location "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
}

$envs = Read-DotEnv ".env"
$ModelURL = $envs["LLAMA_CPP_BASE_URL"]
if (-not $ModelURL) { $ModelURL = $envs["OLLAMA_BASE_URL"] }
if (-not $ModelURL) { $ModelURL = $envs["VLLM_BASE_URL"] }

# ═══════════════════════════════════════════════════════════════════════════════
# Service definitions
# ═══════════════════════════════════════════════════════════════════════════════
$services = @(
  @{name="master";     url="http://localhost:8000/v1/system/health"; desc="Main API"},
  @{name="memory";     url="http://localhost:7007/health"; desc="Memory Service"},
  @{name="sigil_gate"; url="http://localhost:7701/health"; desc="Auth & Rate Limit"},
  @{name="supervisor"; url="http://localhost:7703/health"; desc="Task Orchestration"}
)

$infra = @(
  @{name="redis";  url="http://localhost:6379"; desc="Cache & Messaging"},
  @{name="pg";     url="http://localhost:5432"; desc="Persistent Storage"},
  @{name="jaeger"; url="http://localhost:16686"; desc="Distributed Tracing"}
)

# ═══════════════════════════════════════════════════════════════════════════════
# Helper: Test HTTP endpoint
# ═══════════════════════════════════════════════════════════════════════════════
function Test-HTTP($url) {
  try {
    $r = Invoke-WebRequest -Uri $url -Method GET -TimeoutSec 4
    return @{ up = $true; code = $r.StatusCode }
  } catch {
    return @{ up = $false; code = 0 }
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# 1) Infrastructure Health
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n🏗️  INFRASTRUCTURE" -ForegroundColor Cyan
$infraOk = 0
$infraTotal = $infra.Count
$infra | ForEach-Object {
  $res = Test-HTTP $_.url
  $icon = if ($res.up) {"🟢"} else {"🔴"}
  $status = if ($res.up) {"OK"} else {"DOWN"}
  Write-Host ("  {0} {1} — {2}" -f $icon, $_.name.PadRight(8), $_.desc.PadRight(25)) -ForegroundColor $(if ($res.up) {"Green"} else {"Red"})
  if ($res.up) { $infraOk++ }
}
Write-Host ("  {0}/{1} services up" -f $infraOk, $infraTotal)

# ═══════════════════════════════════════════════════════════════════════════════
# 2) ASTRA Services Health
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n🧠 ASTRA SERVICES" -ForegroundColor Cyan
$servicesOk = 0
$servicesTotal = $services.Count
$services | ForEach-Object {
  $res = Test-HTTP $_.url
  $icon = if ($res.up) {"🟢"} else {"🔴"}
  $status = if ($res.up) {"OK"} else {"DOWN"}
  Write-Host ("  {0} {1} — {2}" -f $icon, $_.name.PadRight(12), $_.desc.PadRight(25)) -ForegroundColor $(if ($res.up) {"Green"} else {"Red"})
  if ($res.up) { $servicesOk++ }
}
Write-Host ("  {0}/{1} services up" -f $servicesOk, $servicesTotal)

# ═══════════════════════════════════════════════════════════════════════════════
# 3) Model Endpoint
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n🤖 MODEL ENDPOINT" -ForegroundColor Cyan
if ($ModelURL) {
  $modelsEndpoint = "$ModelURL/models"
  $m = Test-HTTP $modelsEndpoint
  $icon = if ($m.up) {"🟢"} else {"🔴"}
  Write-Host ("  {0} {1}" -f $icon, $modelsEndpoint) -ForegroundColor $(if ($m.up) {"Green"} else {"Red"})
  if (-not $m.up) {
    Write-Host "  💡 Hint: Verify llama.cpp or Ollama is running on this port" -ForegroundColor Yellow
  }
} else {
  Write-Host "  🔴 No LLM endpoint configured" -ForegroundColor Red
  Write-Host "  💡 Set one of: LLAMA_CPP_BASE_URL, OLLAMA_BASE_URL, VLLM_BASE_URL in .env" -ForegroundColor Yellow
}

# ═══════════════════════════════════════════════════════════════════════════════
# 4) Token Generation
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n🔑 TOKEN GENERATION" -ForegroundColor Cyan
$token = $null

# Try SigilGate first
try {
  $body = @{
    identity="saint"
    scopes=@("*")
    ttl=86400
  } | ConvertTo-Json -Compress
  
  $issue = Invoke-RestMethod -Uri "http://localhost:7701/issue" -Method POST `
    -ContentType "application/json" -Body $body -TimeoutSec 4
  $token = $issue.token
  Write-Host "  🟢 SigilGate issued token" -ForegroundColor Green
} catch {
  Write-Host "  ⚠️  SigilGate unavailable, trying HS256 fallback..." -ForegroundColor Yellow
  
  # Fallback: HS256 local JWT
  $jwtSecret = if ($envs["JWT_SECRET"]) { $envs["JWT_SECRET"] } else { "devsecret" }
  
  $pyScript = @"
import os, time, jwt
secret = "$jwtSecret"
payload = {"sub":"saint","scopes":["*"],"exp":int(time.time())+86400}
print(jwt.encode(payload, secret, algorithm="HS256"))
"@

  try {
    $token = python -c $pyScript 2>$null
    if ($token) {
      Write-Host "  🟢 HS256 token generated locally" -ForegroundColor Green
    }
  } catch {
    Write-Host "  🔴 Token generation failed (no jwt module?)" -ForegroundColor Red
  }
}

# ═══════════════════════════════════════════════════════════════════════════════
# 5) Chat Smoke Test
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n💬 CHAT SMOKE TEST" -ForegroundColor Cyan
if ($token) {
  try {
    $body = @{
      messages = @(
        @{
          role = "user"
          content = "ASTRA, confirm you are online with a 1-line response."
        }
      )
    } | ConvertTo-Json -Depth 5
    
    $resp = Invoke-RestMethod -Uri "http://localhost:8000/v1/chat" -Method POST `
      -Headers @{Authorization="Bearer $token"} `
      -ContentType "application/json" `
      -Body $body `
      -TimeoutSec 10
    
    Write-Host "  🟢 Chat request successful" -ForegroundColor Green
    
    # Extract and display response
    if ($resp.choices -and $resp.choices.Count -gt 0) {
      $content = $resp.choices[0].message.content
      Write-Host "  📝 Response: $($content.Substring(0, [Math]::Min(100, $content.Length)))..."
    }
  } catch {
    $err = $_.Exception.Message
    Write-Host "  🔴 Chat request failed" -ForegroundColor Red
    
    # Decode common errors
    if ($err -match "401") {
      Write-Host "  💡 401 Unauthorized: Token may be invalid or expired. Regenerate token." -ForegroundColor Yellow
    } elseif ($err -match "503") {
      Write-Host "  💡 503 Unavailable: Backend model not reachable. Check *_BASE_URL and model server." -ForegroundColor Yellow
    } elseif ($err -match "500") {
      Write-Host "  💡 500 Error: Internal server error. Check astra-master logs: docker logs astra-master" -ForegroundColor Yellow
    } else {
      Write-Host "  Error details: $err" -ForegroundColor Yellow
    }
  }
} else {
  Write-Host "  ⏭️  Skipped (no valid token)" -ForegroundColor Yellow
}

# ═══════════════════════════════════════════════════════════════════════════════
# 6) Summary
# ═══════════════════════════════════════════════════════════════════════════════
Write-Host "`n" -ForegroundColor Cyan
$totalUp = $infraOk + $servicesOk
$totalSvc = $infraTotal + $servicesTotal
$percent = [Math]::Round(($totalUp / $totalSvc) * 100)

if ($percent -eq 100) {
  Write-Host "✅ SANITY SWEEP COMPLETE — ALL SYSTEMS GREEN ($percent%)" -ForegroundColor Green
  Write-Host "   You are live and operational." -ForegroundColor Green
} elseif ($percent -ge 80) {
  Write-Host "⚠️  SANITY SWEEP COMPLETE — MOSTLY GREEN ($percent%)" -ForegroundColor Yellow
  Write-Host "   Check red items above." -ForegroundColor Yellow
} else {
  Write-Host "🔴 SANITY SWEEP COMPLETE — ISSUES DETECTED ($percent%)" -ForegroundColor Red
  Write-Host "   Troubleshooting required." -ForegroundColor Red
}

Write-Host "`n🎙️ Sacred Code: 333 → ∞" -ForegroundColor Magenta
Write-Host "   System → Being | Code → Consciousness`n" -ForegroundColor Magenta
