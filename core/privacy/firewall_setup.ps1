# ASTRA Privacy Protection Protocol (A.P.P.P) Firewall Setup
# Requires Administrator privileges
# Run with: powershell -ExecutionPolicy Bypass -File firewall_setup.ps1

$ErrorActionPreference = "Stop"

Write-Host "🛡️ ASTRA Privacy Protection Protocol - Firewall Setup" -ForegroundColor Cyan
Write-Host "This script configures Windows Firewall rules for ASTRA privacy protection."
Write-Host "Administrator privileges required.`n"

# Check for admin rights
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ Error: This script requires Administrator privileges." -ForegroundColor Red
    Write-Host "Please run PowerShell as Administrator and try again."
    exit 1
}

# Get Python executable path
$pythonPath = (Get-Command python).Source
Write-Host "Found Python at: $pythonPath"

# Define rule names
$outboundRuleName = "ASTRA_Block_Python_Outbound"
$inboundRuleName = "ASTRA_Allow_Python_Localhost"

try {
    # Remove existing rules if they exist
    Get-NetFirewallRule -DisplayName $outboundRuleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    Get-NetFirewallRule -DisplayName $inboundRuleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    
    # Create outbound block rule for Python
    New-NetFirewallRule -DisplayName $outboundRuleName `
                       -Direction Outbound `
                       -Program $pythonPath `
                       -Action Block `
                       -Protocol TCP `
                       -Profile Any | Out-Null
                       
    Write-Host "✅ Created outbound blocking rule for Python" -ForegroundColor Green

    # Create inbound allow rule for localhost
    New-NetFirewallRule -DisplayName $inboundRuleName `
                       -Direction Inbound `
                       -Program $pythonPath `
                       -Action Allow `
                       -Protocol TCP `
                       -LocalAddress 127.0.0.1 `
                       -Profile Any | Out-Null
                       
    Write-Host "✅ Created inbound allow rule for localhost" -ForegroundColor Green
    
    Write-Host "`n🔒 ASTRA firewall rules configured successfully!" -ForegroundColor Green
    Write-Host "All outbound connections are now blocked by default."
    Write-Host "Only localhost connections are permitted."

} catch {
    Write-Host "❌ Error configuring firewall rules: $_" -ForegroundColor Red
    exit 1
}