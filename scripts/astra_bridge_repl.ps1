# ASTRA Communication Bridge REPL
# Interactive prompt for sending messages to ASTRA via Bridge module

param(
    [string]$BaseUrl = "http://127.0.0.1:8765"
)

$ErrorActionPreference = 'Continue'
$IngestUrl = "$BaseUrl/v1/bridge/ingest"
$HealthUrl = "$BaseUrl/v1/bridge/healthz"
$Headers = @{ 'Content-Type' = 'application/json' }

function Show-Banner {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "        ASTRA COMMUNICATION BRIDGE - ACTIVE" -ForegroundColor Cyan
    Write-Host "        Sacred Code: 333 | 'I only obey God'" -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Test-BridgeHealth {
    try {
        $health = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 5
        Write-Host "[OK] Bridge Health: $($health.status) | Enabled: $($health.enabled)" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "[FAIL] Bridge Health Check" -ForegroundColor Red
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Send-ToAstra {
    param(
        [string]$Message,
        [bool]$QuoteRaw = $true
    )
    
    $body = @{ text = $Message; quote_raw = $QuoteRaw } | ConvertTo-Json -Compress
    
    try {
        $response = Invoke-RestMethod -Uri $IngestUrl -Method POST -Headers $Headers -Body $body -TimeoutSec 30
        
        Write-Host ""
        Write-Host "[SUCCESS] Response received" -ForegroundColor Green
        Write-Host "  RID: $($response.rid)" -ForegroundColor DarkCyan
        Write-Host "  Intents: $($response.intents.Count) | Facts: $($response.facts.Count) | Redactions: $($response.redactions)" -ForegroundColor DarkCyan
        
        if ($response.route_result.reply) {
            Write-Host ""
            Write-Host "  Reply:" -ForegroundColor Yellow
            Write-Host "  $($response.route_result.reply)" -ForegroundColor White
        }
        
        if ($response.facts.Count -gt 0) {
            Write-Host ""
            Write-Host "  Facts:" -ForegroundColor Yellow
            foreach ($fact in $response.facts) {
                Write-Host "    - $fact" -ForegroundColor White
            }
        }
        
        return $response
    }
    catch {
        $statusCode = $null
        $errorBody = $null
        
        try {
            $statusCode = $_.Exception.Response.StatusCode.value__
            $stream = $_.Exception.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($stream)
            $errorBody = $reader.ReadToEnd()
        }
        catch { }
        
        Write-Host ""
        Write-Host "[FAIL] Ingest error (HTTP $statusCode)" -ForegroundColor Red
        if ($errorBody) {
            Write-Host "  Server: $errorBody" -ForegroundColor Red
        }
        else {
            Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
        }
        
        # Fallback: Log to file
        $ts = Get-Date -Format 'yyyyMMdd_HHmmss'
        $logDir = Join-Path (Split-Path $PSScriptRoot -Parent) "runtime\logs"
        if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
        $logPath = Join-Path $logDir "bridge_fallback_$ts.txt"
        $logEntry = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')]`nMessage: $Message`nStatus: HTTP $statusCode`nError: $($_.Exception.Message)`nErrorBody: $errorBody`n`n"
        $logEntry | Out-File -FilePath $logPath -Append -Encoding utf8
        Write-Host "  -> Logged to: runtime\logs\bridge_fallback_$ts.txt" -ForegroundColor DarkYellow
        
        return $null
    }
}

function Show-Help {
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Yellow
    Write-Host "  ASK: <question>       - Ask ASTRA a question" -ForegroundColor White
    Write-Host "  FACT: <statement>     - Register a fact" -ForegroundColor White
    Write-Host "  ACT: <action>         - Propose an action" -ForegroundColor White
    Write-Host "  health                - Check Bridge health" -ForegroundColor White
    Write-Host "  help                  - Show this help" -ForegroundColor White
    Write-Host "  exit                  - Close bridge" -ForegroundColor White
    Write-Host ""
}

# Main
Show-Banner

Write-Host "Initializing bridge..." -ForegroundColor DarkCyan
$healthOk = Test-BridgeHealth

if (-not $healthOk) {
    Write-Host ""
    Write-Host "Warning: Bridge health check failed. Messages will be logged locally." -ForegroundColor Yellow
    Write-Host "Check if Ascension Stack is running on $BaseUrl" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Type 'help' for commands, 'exit' to quit" -ForegroundColor DarkCyan
Write-Host ""

# Interactive loop
while ($true) {
    Write-Host "ASTRA> " -NoNewline -ForegroundColor Yellow
    $userInput = Read-Host
    
    if ([string]::IsNullOrWhiteSpace($userInput)) {
        continue
    }
    
    $userInput = $userInput.Trim()
    
    # Commands
    if ($userInput -match '^(exit|quit|q)$') {
        Write-Host ""
        Write-Host "Closing communication bridge..." -ForegroundColor DarkCyan
        Write-Host "Sacred Code: 333" -ForegroundColor Cyan
        Write-Host ""
        break
    }
    elseif ($userInput -match '^(help|\?)$') {
        Show-Help
    }
    elseif ($userInput -eq 'health') {
        Test-BridgeHealth | Out-Null
        Write-Host ""
    }
    elseif ($userInput -match '^(ASK|FACT|ACT):?\s+(.+)$') {
        $prefix = $Matches[1]
        $content = $Matches[2]
        $message = "${prefix}: $content"
        Send-ToAstra -Message $message | Out-Null
        Write-Host ""
    }
    else {
        # Assume it's an ASK if no prefix
        $message = "ASK: $userInput"
        Send-ToAstra -Message $message | Out-Null
        Write-Host ""
    }
}
