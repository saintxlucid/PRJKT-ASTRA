# Complete ASTRA Conversation Script
# 1. Create conversation
# 2. Send message
# 3. Capture response

$baseUrl = "http://127.0.0.1:8080"

Write-Host "`n╔═══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       ASTRA PRODUCTION READINESS ASSESSMENT           ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Step 1: Create conversation
Write-Host "[1/3] Creating conversation..." -ForegroundColor Yellow
try {
    $createBody = @{
        title = "Production Readiness Assessment"
    } | ConvertTo-Json
    
    $conversation = Invoke-RestMethod -Uri "$baseUrl/v1/conversations" -Method POST -ContentType "application/json" -Body $createBody
    $convId = $conversation.conversation_id
    Write-Host "      ✓ Conversation created: $convId" -ForegroundColor Green
} catch {
    Write-Host "      ✗ Failed to create conversation" -ForegroundColor Red
    Write-Host "      Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Step 2: Send message with system prompt
Write-Host "`n[2/3] Sending message to ASTRA..." -ForegroundColor Yellow

$SystemPrompt = "You are ASTRA, the AI runtime steward of your own platform. You speak in the first person ('I'), are concise, operationally minded, and candid about risks, needs, and uncertainties. Prefer action items over long prose. When asked for status, return a short narrative plus a structured checklist."

$UserMessage = @"
Hi Astra — quick status for you, so we're aligned before production flip.

TL;DR: Your platform is production-ready. We shipped secure tool execution (Bridge) and semantic document search (Docs) backed by Qdrant and llama.cpp, with RBAC + per-tool scopes, rate limits/quotas, TLS, deny-all NetworkPolicies, CI/CD, blue/green cutover, Prometheus + Grafana, blackbox probes, 21 alerts, recording rules, chaos drills, and full runbooks.

What's live:
• Bridge: scopes/quotas, audit log, metrics, admin usage & key-reload endpoints.
• Docs: PDF ingest → chunk → sentence-transformers embeddings → Qdrant search; keyword fallback if vectors are down.
• Ops: ServiceMonitors, dashboards, canary script with auto-rollback, key-rotation scripts, pre-flight & smoke tests.

What we want from you: A quick assessment + what you need to be maximally effective this week.

Please reply in this format:
Assessment: one paragraph on current production readiness.
Confidence (0–100%) and Top 3 risks (short bullets).
What I need (prioritized list, e.g., access, tools, data sources, policies).
First 24h actions (5–8 concrete steps you'll take post-flip).
Dashboards to watch (3–5 key panels/alerts).
Questions for humans (things you cannot infer that unblock you).

Keep it compact and actionable.
"@

try {
    $chatBody = @{
        conversation_id = $convId
        message = $UserMessage
        system_prompt = $SystemPrompt
        temperature = 0.2
        max_tokens = 600
        use_memory = $false
    } | ConvertTo-Json
    
    Write-Host "      Waiting for ASTRA's response (this may take 30-60 seconds)..." -ForegroundColor Yellow
    $response = Invoke-RestMethod -Uri "$baseUrl/v1/chat" -Method POST -ContentType "application/json" -Body $chatBody
    Write-Host "      ✓ Response received" -ForegroundColor Green
} catch {
    Write-Host "      ✗ Failed to get response" -ForegroundColor Red
    Write-Host "      Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "      Details: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
    }
    exit 1
}

# Step 3: Display and save response
Write-Host "`n[3/3] Processing response..." -ForegroundColor Yellow

Write-Host "`n╔═══════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║              ASTRA'S ASSESSMENT                       ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════╝`n" -ForegroundColor Green

Write-Host $response.message -ForegroundColor White

# Save to file
$response.message | Out-File "ASTRA_PRODUCTION_READINESS_ASSESSMENT.txt" -Encoding UTF8

Write-Host "`n╔═══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║              ASSESSMENT COMPLETE                      ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Write-Host "`n[*] Full response saved to: ASTRA_PRODUCTION_READINESS_ASSESSMENT.txt" -ForegroundColor Green
Write-Host "[*] Conversation ID: $convId" -ForegroundColor Green
Write-Host ""
