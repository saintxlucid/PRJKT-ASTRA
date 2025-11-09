# ASTRA Privacy Protection - Windows Firewall Rules
# ==================================================
# PowerShell script to block outbound Python network access
# Implements network isolation at OS level
#
# REQUIRES: Administrator privileges
# USE WITH CAUTION: This will block ALL Python network access
#
# Author: Saint Lucid
# Date: 2025-10-18

#Requires -RunAsAdministrator

Write-Host "=" -ForegroundColor Cyan
Write-Host "🔒 ASTRA PRIVACY FIREWALL - Windows Network Isolation" -ForegroundColor Cyan
Write-Host "=" -ForegroundColor Cyan
Write-Host ""

# Configuration
$PythonPaths = @(
    "C:\Python*\python.exe",
    "C:\Users\*\AppData\Local\Programs\Python\Python*\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe",
    "C:\ProgramData\Anaconda3\python.exe",
    "C:\Users\*\Anaconda3\python.exe",
    "C:\Users\*\Miniconda3\python.exe"
)

$RuleName = "ASTRA_Privacy_Block_Python_Outbound"
$RuleDescription = "Blocks outbound Python network access for ASTRA privacy protection"

# Function to find Python executables
function Find-PythonExecutables {
    Write-Host "[INFO] Scanning for Python executables..." -ForegroundColor Yellow
    
    $found = @()
    foreach ($pattern in $PythonPaths) {
        $matches = Get-Item $pattern -ErrorAction SilentlyContinue
        if ($matches) {
            $found += $matches
        }
    }
    
    # Remove duplicates
    $found = $found | Select-Object -Unique
    
    Write-Host "[INFO] Found $($found.Count) Python executable(s)" -ForegroundColor Green
    foreach ($exe in $found) {
        Write-Host "  - $($exe.FullName)" -ForegroundColor Gray
    }
    
    return $found
}

# Function to create firewall rule
function New-AstraFirewallRule {
    param(
        [string]$ExePath
    )
    
    $ruleName = "${RuleName}_$(Split-Path $ExePath -Leaf)"
    
    # Check if rule already exists
    $existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    
    if ($existing) {
        Write-Host "[WARN] Rule already exists: $ruleName" -ForegroundColor Yellow
        Write-Host "       Removing old rule..." -ForegroundColor Yellow
        Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    }
    
    # Create new blocking rule
    try {
        New-NetFirewallRule `
            -DisplayName $ruleName `
            -Description $RuleDescription `
            -Direction Outbound `
            -Action Block `
            -Program $ExePath `
            -Enabled True `
            -Profile Any `
            | Out-Null
        
        Write-Host "[OK] Created blocking rule for: $ExePath" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "[ERROR] Failed to create rule: $_" -ForegroundColor Red
        return $false
    }
}

# Function to create localhost exception rule
function New-AstraLocalhostException {
    param(
        [string]$ExePath
    )
    
    $ruleName = "${RuleName}_Localhost_Exception_$(Split-Path $ExePath -Leaf)"
    
    # Check if rule already exists
    $existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    
    if ($existing) {
        Remove-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    }
    
    # Create allow rule for localhost (higher priority)
    try {
        New-NetFirewallRule `
            -DisplayName $ruleName `
            -Description "Allow localhost for ASTRA Python" `
            -Direction Outbound `
            -Action Allow `
            -Program $ExePath `
            -RemoteAddress 127.0.0.1,::1 `
            -Enabled True `
            -Profile Any `
            | Out-Null
        
        Write-Host "[OK] Created localhost exception for: $ExePath" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "[ERROR] Failed to create localhost exception: $_" -ForegroundColor Red
        return $false
    }
}

# Function to remove ASTRA firewall rules
function Remove-AstraFirewallRules {
    Write-Host "[INFO] Removing existing ASTRA firewall rules..." -ForegroundColor Yellow
    
    $rules = Get-NetFirewallRule -DisplayName "$RuleName*" -ErrorAction SilentlyContinue
    
    if ($rules) {
        foreach ($rule in $rules) {
            Write-Host "  Removing: $($rule.DisplayName)" -ForegroundColor Gray
            Remove-NetFirewallRule -DisplayName $rule.DisplayName
        }
        Write-Host "[OK] Removed $($rules.Count) rule(s)" -ForegroundColor Green
    }
    else {
        Write-Host "[INFO] No existing rules found" -ForegroundColor Gray
    }
}

# Function to list current ASTRA rules
function Get-AstraFirewallRules {
    $rules = Get-NetFirewallRule -DisplayName "$RuleName*" -ErrorAction SilentlyContinue
    
    if ($rules) {
        Write-Host ""
        Write-Host "Current ASTRA Firewall Rules:" -ForegroundColor Cyan
        Write-Host "=" -ForegroundColor Cyan
        
        foreach ($rule in $rules) {
            Write-Host ""
            Write-Host "Rule: $($rule.DisplayName)" -ForegroundColor Yellow
            Write-Host "  Action: $($rule.Action)" -ForegroundColor Gray
            Write-Host "  Direction: $($rule.Direction)" -ForegroundColor Gray
            Write-Host "  Enabled: $($rule.Enabled)" -ForegroundColor Gray
        }
    }
    else {
        Write-Host "[INFO] No ASTRA firewall rules found" -ForegroundColor Gray
    }
}

# Function to test firewall
function Test-AstraFirewall {
    Write-Host ""
    Write-Host "[TEST] Testing network isolation..." -ForegroundColor Yellow
    
    # Try to make a network request with Python
    $testScript = @"
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    s.connect(('example.com', 80))
    s.close()
    print('FAIL: Network access allowed')
except Exception as e:
    print(f'PASS: Network blocked - {type(e).__name__}')
"@
    
    $testFile = "$env:TEMP\astra_firewall_test.py"
    $testScript | Out-File -FilePath $testFile -Encoding UTF8
    
    Write-Host "[TEST] Running Python network test..." -ForegroundColor Gray
    python $testFile
    
    Remove-Item $testFile -ErrorAction SilentlyContinue
}

# Main menu
function Show-Menu {
    Write-Host ""
    Write-Host "Choose an action:" -ForegroundColor Cyan
    Write-Host "  [1] Install firewall rules (BLOCK Python network)" -ForegroundColor White
    Write-Host "  [2] Remove firewall rules (RESTORE Python network)" -ForegroundColor White
    Write-Host "  [3] List current rules" -ForegroundColor White
    Write-Host "  [4] Test firewall" -ForegroundColor White
    Write-Host "  [5] Exit" -ForegroundColor White
    Write-Host ""
    
    $choice = Read-Host "Enter choice (1-5)"
    return $choice
}

# Main execution
Write-Host ""
Write-Host "⚠️  WARNING: This script will block ALL outbound Python network access" -ForegroundColor Red
Write-Host "    except localhost (127.0.0.1). Use for ASTRA privacy enforcement." -ForegroundColor Yellow
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[ERROR] This script requires Administrator privileges!" -ForegroundColor Red
    Write-Host "        Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Main loop
do {
    $choice = Show-Menu
    
    switch ($choice) {
        "1" {
            Write-Host ""
            Write-Host "[ACTION] Installing ASTRA firewall rules..." -ForegroundColor Cyan
            Write-Host ""
            
            # Find Python executables
            $pythonExes = Find-PythonExecutables
            
            if ($pythonExes.Count -eq 0) {
                Write-Host "[ERROR] No Python executables found!" -ForegroundColor Red
                Write-Host "        Install Python or update `$PythonPaths in script" -ForegroundColor Yellow
                continue
            }
            
            # Create rules for each Python
            $successCount = 0
            foreach ($exe in $pythonExes) {
                # Create localhost exception first (higher priority)
                $localhostOk = New-AstraLocalhostException -ExePath $exe.FullName
                
                # Create blocking rule
                $blockOk = New-AstraFirewallRule -ExePath $exe.FullName
                
                if ($blockOk -and $localhostOk) {
                    $successCount++
                }
            }
            
            Write-Host ""
            Write-Host "[DONE] Created rules for $successCount/$($pythonExes.Count) Python executable(s)" -ForegroundColor Green
            Write-Host ""
        }
        
        "2" {
            Write-Host ""
            Write-Host "[ACTION] Removing ASTRA firewall rules..." -ForegroundColor Cyan
            Write-Host ""
            
            Remove-AstraFirewallRules
            
            Write-Host ""
            Write-Host "[DONE] Python network access restored" -ForegroundColor Green
            Write-Host ""
        }
        
        "3" {
            Get-AstraFirewallRules
        }
        
        "4" {
            Test-AstraFirewall
        }
        
        "5" {
            Write-Host ""
            Write-Host "Exiting..." -ForegroundColor Gray
            break
        }
        
        default {
            Write-Host "[ERROR] Invalid choice" -ForegroundColor Red
        }
    }
    
} while ($choice -ne "5")

Write-Host ""
Write-Host "🔒 ASTRA Privacy Firewall - Complete" -ForegroundColor Cyan
Write-Host ""
