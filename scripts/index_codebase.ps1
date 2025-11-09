# index_codebase.ps1
# Triggers full repository indexing via ASTRA Task Agent
# Builds a searchable symbol index for code navigation and understanding

param(
    [string]$ApiUrl = "http://127.0.0.1:8765",
    [string]$Root = "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
)

Write-Host "`n=== ASTRA Repository Indexing ===" -ForegroundColor Cyan
Write-Host "API: $ApiUrl" -ForegroundColor Gray
Write-Host "Root: $Root`n" -ForegroundColor Gray

# Check if API is available
try {
    $health = Invoke-RestMethod -Uri "$ApiUrl/api/system/health" -Method GET -ErrorAction Stop
    Write-Host "[✓] Ascension Stack is healthy" -ForegroundColor Green
} catch {
    Write-Host "[✗] Ascension Stack not available. Start it first." -ForegroundColor Red
    Write-Host "    Run: python launch_ascension_stack.py --port 8765" -ForegroundColor Yellow
    exit 1
}

# Build indexing request
$indexRequest = @{
    tool = "code"
    action = "index"
    authorized = $true
    args = @{
        root = $Root
        include = @(
            "src/**",
            "astra-local/**",
            "astra-launcher/**",
            "config/**",
            "persona/**",
            "scripts/**"
        )
        exclude = @(
            "**/.git/**",
            "**/node_modules/**",
            "**/.venv/**",
            "**/venv/**",
            "runtime/**",
            "models/**",
            "**/__pycache__/**",
            "**/*.pyc",
            "data/chroma/**"
        )
        languages = @(
            "py", "ts", "js", "ps1", "bat",
            "html", "css", "json", "yaml", "yml", "sql", "md"
        )
        symbols = $true
        max_files = 10000
    }
} | ConvertTo-Json -Compress -Depth 10

Write-Host "Starting repository index..." -ForegroundColor Yellow
Write-Host "This may take 30-60 seconds...`n" -ForegroundColor Gray

try {
    $response = Invoke-RestMethod -Uri "$ApiUrl/api/agent/execute" `
        -Method POST `
        -ContentType "application/json" `
        -Body $indexRequest `
        -TimeoutSec 120 `
        -ErrorAction Stop
    
    Write-Host "`n[✓] Index complete!" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Depth 5)" -ForegroundColor Gray
    
    # Post an update event
    $updateBody = @{
        kind = "index_refreshed"
        title = "Repository index refreshed"
        summary = "Full codebase indexed for ASTRA awareness"
        actor = "system"
        impact = "medium"
        details = @{
            root = $Root
            timestamp = (Get-Date).ToUniversalTime().ToString("o")
        }
    } | ConvertTo-Json -Compress
    
    try {
        Invoke-RestMethod -Uri "$ApiUrl/v1/updates/event" `
            -Method POST `
            -ContentType "application/json" `
            -Body $updateBody `
            -ErrorAction SilentlyContinue | Out-Null
    } catch {
        # Silent fail for update event
    }
    
    Write-Host "`n[✓] ASTRA can now navigate the codebase!" -ForegroundColor Green
    Write-Host "    Next: Run .\scripts\seed_curriculum.ps1 to teach the workflow" -ForegroundColor Yellow
    
} catch {
    Write-Host "`n[✗] Indexing failed: $_" -ForegroundColor Red
    Write-Host "    Note: If 'code' tool not found, this feature may not be implemented yet" -ForegroundColor Yellow
    Write-Host "    You can still use ASTRA with architecture facts only" -ForegroundColor Yellow
}

exit 0
