# Install and manage the ASTRA ingestion service
param(
    [Parameter()]
    [ValidateSet('install', 'uninstall', 'start', 'stop', 'restart')]
    [string]$Action = 'install'
)

$ErrorActionPreference = 'Stop'
$serviceName = 'ASTRAIngest'
$pythonExe = (Get-Command python).Source
$scriptPath = Join-Path $PSScriptRoot 'src\astra\service\ingest.py'

function Install-Service {
    Write-Host "Installing $serviceName service..."
    & $pythonExe $scriptPath --startup auto install
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Service installed successfully"
        Start-Service $serviceName
    } else {
        throw "Service installation failed"
    }
}

function Uninstall-Service {
    Write-Host "Uninstalling $serviceName service..."
    Stop-Service $serviceName -ErrorAction SilentlyContinue
    & $pythonExe $scriptPath remove
    Write-Host "Service uninstalled"
}

function Restart-ASTRAService {
    Write-Host "Restarting $serviceName service..."
    Restart-Service $serviceName
    Write-Host "Service restarted"
}

# Execute requested action
switch ($Action) {
    'install' { Install-Service }
    'uninstall' { Uninstall-Service }
    'start' { Start-Service $serviceName }
    'stop' { Stop-Service $serviceName }
    'restart' { Restart-ASTRAService }
}