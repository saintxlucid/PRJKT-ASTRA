# Simple ASTRA Call Script
param(
    [string]$BridgeUrl = "http://127.0.0.1:8080/call",
    [string]$ApiKey = "dev-admin-key-12345"
)

$json = @'
{
  "tool_name": "llama",
  "args": {
    "messages": [
      {
        "role": "system",
        "content": "You are ASTRA, the AI runtime steward of your own platform. You speak in the first person (\"I\"), are concise, operationally minded, and candid about risks, needs, and uncertainties. Prefer action items over long prose. When asked for status, return a short narrative plus a structured checklist."
      },
      {
        "role": "user",
        "content": "Hi Astra — quick status for you, so we're aligned before production flip.\n\nTL;DR: Your platform is production-ready. We shipped secure tool execution (Bridge) and semantic document search (Docs) backed by Qdrant and llama.cpp, with RBAC + per-tool scopes, rate limits/quotas, TLS, deny-all NetworkPolicies, CI/CD, blue/green cutover, Prometheus + Grafana, blackbox probes, 21 alerts, recording rules, chaos drills, and full runbooks.\n\nWhat's live:\n• Bridge: scopes/quotas, audit log, metrics, admin usage & key-reload endpoints.\n• Docs: PDF ingest → chunk → sentence-transformers embeddings → Qdrant search; keyword fallback if vectors are down.\n• Ops: ServiceMonitors, dashboards, canary script with auto-rollback, key-rotation scripts, pre-flight & smoke tests.\n\nWhat we want from you: A quick assessment + what you need to be maximally effective this week.\n\nPlease reply in this format:\nAssessment: one paragraph on current production readiness.\nConfidence (0–100%) and Top 3 risks (short bullets).\nWhat I need (prioritized list, e.g., access, tools, data sources, policies).\nFirst 24h actions (5–8 concrete steps you'll take post-flip).\nDashboards to watch (3–5 key panels/alerts).\nQuestions for humans (things you cannot infer that unblock you).\n\nKeep it compact and actionable."
      }
    ],
    "max_tokens": 600,
    "temperature": 0.2
  }
}
'@

Write-Host "`n=== CALLING ASTRA ===" -ForegroundColor Cyan

$response = Invoke-RestMethod -Uri $BridgeUrl -Method POST -ContentType "application/json" -Headers @{"x-api-key"=$ApiKey} -Body $json

Write-Host "`n=== ASTRA'S RESPONSE ===" -ForegroundColor Green
Write-Host $response.result

# Save to file
$response.result | Out-File "ASTRA_ASSESSMENT.txt" -Encoding UTF8
Write-Host "`n[Saved to ASTRA_ASSESSMENT.txt]`n" -ForegroundColor Cyan
