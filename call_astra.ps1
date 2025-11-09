# Call ASTRA via Chat API
param(
    [string]$ChatUrl = "http://127.0.0.1:8080/v1/chat",
    [string]$ConversationId = "prod-readiness-assessment"
)

$SystemPrompt = @"
You are ASTRA, the AI runtime steward of your own platform. You speak in the first person ("I"), are concise, operationally minded, and candid about risks, needs, and uncertainties. Prefer action items over long prose. When asked for status, return a short narrative plus a structured checklist.
"@

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

$body = @{
    conversation_id = $ConversationId
    message = $UserMessage
    system_prompt = $SystemPrompt
    temperature = 0.2
    max_tokens = 600
    use_memory = $false
} | ConvertTo-Json

Write-Host "`n╔═══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         CALLING ASTRA FOR STATUS ASSESSMENT           ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri $ChatUrl -Method POST -ContentType "application/json" -Body $body
    
    Write-Host "╔═══════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║              ASTRA'S RESPONSE                         ║" -ForegroundColor Green
    Write-Host "╚═══════════════════════════════════════════════════════╝`n" -ForegroundColor Green
    
    Write-Host $response.message -ForegroundColor White
    
    # Save to file
    $response.message | Out-File "ASTRA_ASSESSMENT.txt" -Encoding UTF8
    Write-Host "`n✓ Response saved to: ASTRA_ASSESSMENT.txt" -ForegroundColor Cyan
    
} catch {
    Write-Host "✗ Error calling ASTRA:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.ErrorDetails.Message) {
        Write-Host "Details:" $_.ErrorDetails.Message -ForegroundColor Yellow
    }
    exit 1
}

Write-Host "`n╔═══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║              CALL COMPLETE                            ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan
