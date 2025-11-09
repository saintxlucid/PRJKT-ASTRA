# ASTRA Bridge Key Rotation Script (PowerShell)
# Rotates API keys and updates Kubernetes secret + reloads bridge

Param(
    [string]$Namespace = "astra",
    [string]$AdminKey = $env:ADMIN_KEY,
    [string]$BridgeUrl = "https://bridge.example.com"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ASTRA Bridge Key Rotation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Namespace: $Namespace"
Write-Host "Bridge URL: $BridgeUrl"
Write-Host ""

if (-not $AdminKey) {
    Write-Host "[ERROR] ADMIN_KEY not set" -ForegroundColor Red
    Write-Host "Usage: `$env:ADMIN_KEY='xxx'; .\rotate_bridge_key.ps1"
    exit 1
}

# Generate new keys
Write-Host "[1/5] Generating new keys..." -ForegroundColor Cyan
$NewAdminKey = -join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
$NewAgentKey = -join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })

Write-Host "  New Admin Key: $($NewAdminKey.Substring(0,16))..." -ForegroundColor Gray
Write-Host "  New Agent Key: $($NewAgentKey.Substring(0,16))..." -ForegroundColor Gray

# Create new keys JSON
Write-Host "`n[2/5] Creating keys file..." -ForegroundColor Cyan
$date = Get-Date -Format "yyyy-MM-dd"
$keysJson = @{
    $NewAdminKey = @{
        name = "Admin Key (rotated $date)"
        scopes = @("bridge:admin", "bridge:call", "docs:ingest", "docs:search")
        rpm = 120
        daily = 10000
    }
    $NewAgentKey = @{
        name = "Agent Key (rotated $date)"
        scopes = @("bridge:call", "docs:search")
        rpm = 60
        daily = 5000
    }
} | ConvertTo-Json -Depth 3

$keysJson | Out-File -FilePath "bridge_keys_new.json" -Encoding UTF8
Write-Host "  Keys file created: bridge_keys_new.json" -ForegroundColor Gray

# Backup old keys
Write-Host "`n[3/5] Backing up old keys..." -ForegroundColor Cyan
try {
    $oldKeys = kubectl -n $Namespace get secret bridge-keys -o jsonpath='{.data.bridge_keys}' 2>$null
    if ($oldKeys) {
        [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($oldKeys)) | Out-File -FilePath "bridge_keys_backup.json" -Encoding UTF8
        Write-Host "  Old keys backed up to: bridge_keys_backup.json" -ForegroundColor Gray
    }
}
catch {
    Write-Host "  No existing keys to backup" -ForegroundColor Yellow
}

# Update K8s secret
Write-Host "`n[4/5] Updating Kubernetes secret..." -ForegroundColor Cyan
$secretYaml = kubectl -n $Namespace create secret generic bridge-keys `
    --from-file=bridge_keys=bridge_keys_new.json `
    --dry-run=client -o yaml | kubectl apply -f -

Write-Host "  Secret updated successfully" -ForegroundColor Green

# Trigger reload on bridge admin endpoint
Write-Host "`n[5/5] Triggering key reload on bridge..." -ForegroundColor Cyan
try {
    $reloadResponse = Invoke-WebRequest -Uri "$BridgeUrl/admin/reload-keys" `
        -Method Post `
        -Headers @{ 'x-api-key' = $AdminKey } `
        -UseBasicParsing `
        -TimeoutSec 10
    
    if ($reloadResponse.StatusCode -eq 200) {
        Write-Host "  ✅ Keys reloaded successfully" -ForegroundColor Green
    }
}
catch {
    Write-Host "  ⚠️  Reload failed or not available: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "  Bridge pods will pick up new keys on next restart" -ForegroundColor Yellow
    Write-Host "  Consider: kubectl -n $Namespace rollout restart deployment/bridge" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✅ Key Rotation Complete" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 NEW CREDENTIALS:" -ForegroundColor Yellow
Write-Host "-------------------"
Write-Host "Admin Key: $NewAdminKey"
Write-Host "Agent Key: $NewAgentKey"
Write-Host ""
Write-Host "🔐 BACKUP:" -ForegroundColor Yellow
Write-Host "----------"
Write-Host "Old keys backed up to: bridge_keys_backup.json"
Write-Host "New keys saved to: bridge_keys_new.json"
Write-Host ""
Write-Host "⚠️  IMPORTANT:" -ForegroundColor Yellow
Write-Host "-------------"
Write-Host "1. Update your environment variables:"
Write-Host "   `$env:ADMIN_KEY = `"$NewAdminKey`""
Write-Host "   `$env:AGENT_KEY = `"$NewAgentKey`""
Write-Host ""
Write-Host "2. Distribute new AGENT_KEY to clients securely"
Write-Host ""
Write-Host "3. Keep old keys active for 24h grace period, then remove from keys file"
Write-Host ""
Write-Host "4. Store these keys in your password manager!"
Write-Host ""
