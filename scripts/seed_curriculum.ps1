# seed_curriculum.ps1
# Teaches ASTRA the Index→Ask→Plan→Approve→Apply→Learn workflow
# Sets up authorization requirements and safe coding practices

param(
    [string]$ApiUrl = "http://127.0.0.1:8765"
)

Write-Host "`n=== ASTRA Curriculum Seeding ===" -ForegroundColor Cyan
Write-Host "Teaching the development workflow...`n" -ForegroundColor Gray

# Check if API is available
try {
    Invoke-RestMethod -Uri "$ApiUrl/v1/bridge/healthz" -Method GET -ErrorAction Stop | Out-Null
    Write-Host "[✓] Bridge API is healthy" -ForegroundColor Green
} catch {
    Write-Host "[✗] Bridge API not available. Start the Ascension Stack first." -ForegroundColor Red
    exit 1
}

# Curriculum prompts
$curriculum = @(
    @{
        text = "TEACH: You now have a full repo index. For any feature request, follow: Index→Ask→Plan→Approve→Apply→Learn. Always explain why, show impacted files, propose patches as unified diffs, and include a rollback note. Never execute tools without explicit authorization."
        quote_raw = $true
    },
    @{
        text = "TEACH: When proposing code changes: 1) Query the index to understand current implementation, 2) Identify all affected files with paths, 3) Show before/after diffs, 4) List acceptance tests, 5) Explain risks, 6) Wait for approval before execution. Always include a rollback plan."
        quote_raw = $true
    },
    @{
        text = "TEACH: Authorization levels: 0=read-only, 1=memory read/write, 2=tool execution (authorized=true required), 3=system modifications (requires explicit confirmation). Default to lowest level needed. When in doubt, ask."
        quote_raw = $true
    },
    @{
        text = "TEACH: Mode awareness: NONE/DREAM=silent operation, MUSIC=critical alerts only, COGNITION=normal interaction, EMPIRE=full autonomy. Adjust communication style and initiative based on current mode. Check mode before taking action."
        quote_raw = $true
    },
    @{
        text = "TEACH: Safety checklist: 1) Redact secrets (API keys, passwords, tokens), 2) Validate file paths against allowlists, 3) Size limits (max 500KB per operation), 4) Confirm destructive operations, 5) Log all actions with request IDs, 6) Test in dry-run mode first."
        quote_raw = $true
    },
    @{
        text = "TEACH: Feature proposal template: USER_VALUE (why this matters), ACCEPTANCE_TESTS (how to verify), TELEMETRY (metrics to track), RISKS (what could go wrong), PATCH_PLAN (unified diff), ROLLBACK (how to undo). Always include all sections."
        quote_raw = $true
    },
    @{
        text = "TEACH: When asked 'what to work on next': 1) Review recent updates via memory, 2) Check failed tests/builds, 3) Look for TODO/FIXME comments, 4) Identify technical debt, 5) Propose 3-5 prioritized items with effort estimates, 6) Wait for selection."
        quote_raw = $true
    },
    @{
        text = "TEACH: Documentation standards: Every code change requires: 1) Updated docstrings, 2) README updates if user-facing, 3) CHANGELOG entry, 4) Updated .env.example if new config, 5) Type hints for Python, 6) Error handling explanation."
        quote_raw = $true
    }
)

$success = 0
$failed = 0

foreach ($prompt in $curriculum) {
    try {
        $body = $prompt | ConvertTo-Json -Compress
        
        Invoke-RestMethod -Uri "$ApiUrl/v1/bridge/ingest" `
            -Method POST `
            -ContentType "application/json" `
            -Body $body `
            -ErrorAction Stop | Out-Null
        
        $success++
        Write-Host "  [✓] Curriculum item $success" -ForegroundColor Green
        
    } catch {
        $failed++
        Write-Host "  [✗] Failed: $_" -ForegroundColor Red
    }
}

Write-Host "`n=== Curriculum Complete ===" -ForegroundColor Cyan
Write-Host "Total: $($curriculum.Count) | Success: $success | Failed: $failed" -ForegroundColor White

if ($success -gt 0) {
    Write-Host "`n[✓] ASTRA understands the development workflow!" -ForegroundColor Green
    Write-Host "    Next: Try asking ASTRA to verify understanding" -ForegroundColor Yellow
    Write-Host "    Example: 'Summarize the 7-service architecture and key entrypoints'" -ForegroundColor Gray
}

exit 0
