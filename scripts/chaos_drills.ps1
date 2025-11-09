# ASTRA Chaos Engineering Drills
# Safe, controlled failure injection to validate fallbacks and alerting

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("qdrant-down", "bridge-restart", "docs-restart", "network-partition", "all")]
    [string]$Drill = "all",
    
    [Parameter(Mandatory=$false)]
    [string]$Namespace = "astra",
    
    [Parameter(Mandatory=$false)]
    [int]$WaitSeconds = 30
)

$ErrorActionPreference = "Stop"

function Write-Status {
    param($Message, $Color = "Cyan")
    Write-Host "`n[*] $Message" -ForegroundColor $Color
}

function Write-Success {
    param($Message)
    Write-Host "    [OK] $Message" -ForegroundColor Green
}

function Write-Failure {
    param($Message)
    Write-Host "    [FAIL] $Message" -ForegroundColor Red
}

function Write-Info {
    param($Message)
    Write-Host "    [INFO] $Message" -ForegroundColor Yellow
}

# Pre-flight check
Write-Status "ASTRA Chaos Drills - Pre-Flight Check"
Write-Host "Namespace: $Namespace" -ForegroundColor White
Write-Host "Drill: $Drill" -ForegroundColor White
Write-Host "Wait time: $WaitSeconds seconds" -ForegroundColor White

Write-Host "`n⚠️  WARNING: These drills will temporarily disrupt services!" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to abort, or any key to continue..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Drill 1: Qdrant Down → Docs Fallback
if ($Drill -eq "qdrant-down" -or $Drill -eq "all") {
    Write-Status "DRILL 1: Qdrant Down → Docs Fallback" "Magenta"
    
    Write-Info "Deleting Qdrant pod to simulate outage..."
    kubectl -n $Namespace delete pod -l app=qdrant --wait=false
    
    Write-Info "Waiting 10 seconds for pod termination..."
    Start-Sleep -Seconds 10
    
    Write-Info "Testing docs search (should fallback to keyword)..."
    try {
        $response = Invoke-WebRequest `
            -Uri "http://localhost:8777/v1/documents/search?q=test" `
            -Method GET `
            -Headers @{"x-api-key"=$env:AGENT_KEY} `
            -UseBasicParsing `
            -TimeoutSec 5
        
        if ($response.StatusCode -eq 200) {
            Write-Success "Docs search returned 200 (keyword fallback working)"
        }
    } catch {
        Write-Failure "Docs search failed: $_"
    }
    
    Write-Info "Checking if QdrantDown alert fired..."
    Start-Sleep -Seconds 5
    
    # Check Prometheus alerts
    try {
        $alerts = Invoke-RestMethod -Uri "http://prometheus.example.com/api/v1/alerts" -TimeoutSec 5
        $qdrantAlert = $alerts.data.alerts | Where-Object { $_.labels.alertname -eq "QdrantDown" }
        
        if ($qdrantAlert) {
            Write-Success "QdrantDown alert is FIRING (expected)"
        } else {
            Write-Info "QdrantDown alert not yet firing (may take 2+ minutes)"
        }
    } catch {
        Write-Info "Could not check alerts: $_"
    }
    
    Write-Info "Waiting $WaitSeconds seconds for Qdrant to restart..."
    Start-Sleep -Seconds $WaitSeconds
    
    # Check Qdrant pod status
    $qdrantPod = kubectl -n $Namespace get pods -l app=qdrant -o json | ConvertFrom-Json
    if ($qdrantPod.items[0].status.phase -eq "Running") {
        Write-Success "Qdrant pod restarted and running"
    } else {
        Write-Failure "Qdrant pod not yet running: $($qdrantPod.items[0].status.phase)"
    }
    
    Write-Success "DRILL 1 COMPLETE"
}

# Drill 2: Bridge Pod Restart Detection
if ($Drill -eq "bridge-restart" -or $Drill -eq "all") {
    Write-Status "DRILL 2: Bridge Pod Restart Detection" "Magenta"
    
    Write-Info "Getting current bridge pod..."
    $bridgePodBefore = kubectl -n $Namespace get pods -l app=bridge -o jsonpath='{.items[0].metadata.name}'
    Write-Host "    Before: $bridgePodBefore" -ForegroundColor White
    
    Write-Info "Deleting bridge pod..."
    kubectl -n $Namespace delete pod $bridgePodBefore --wait=false
    
    Write-Info "Waiting 5 seconds for termination..."
    Start-Sleep -Seconds 5
    
    Write-Info "Checking if BridgeUnexpectedRestart alert fired..."
    try {
        $alerts = Invoke-RestMethod -Uri "http://prometheus.example.com/api/v1/alerts" -TimeoutSec 5
        $restartAlert = $alerts.data.alerts | Where-Object { $_.labels.alertname -eq "BridgeUnexpectedRestart" }
        
        if ($restartAlert) {
            Write-Success "BridgeUnexpectedRestart alert is FIRING (expected)"
        } else {
            Write-Info "BridgeUnexpectedRestart alert not yet firing"
        }
    } catch {
        Write-Info "Could not check alerts: $_"
    }
    
    Write-Info "Waiting for new pod to be ready..."
    Start-Sleep -Seconds $WaitSeconds
    
    $bridgePodAfter = kubectl -n $Namespace get pods -l app=bridge -o jsonpath='{.items[0].metadata.name}'
    Write-Host "    After: $bridgePodAfter" -ForegroundColor White
    
    # Test bridge health
    Write-Info "Testing bridge health endpoint..."
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8888/health" -TimeoutSec 5
        if ($health.status -eq "ok") {
            Write-Success "Bridge health check passed"
        }
    } catch {
        Write-Failure "Bridge health check failed: $_"
    }
    
    Write-Success "DRILL 2 COMPLETE"
}

# Drill 3: Docs Pod Restart
if ($Drill -eq "docs-restart" -or $Drill -eq "all") {
    Write-Status "DRILL 3: Docs Pod Restart Detection" "Magenta"
    
    Write-Info "Getting current docs pod..."
    $docsPodBefore = kubectl -n $Namespace get pods -l app=docs -o jsonpath='{.items[0].metadata.name}'
    Write-Host "    Before: $docsPodBefore" -ForegroundColor White
    
    Write-Info "Deleting docs pod..."
    kubectl -n $Namespace delete pod $docsPodBefore --wait=false
    
    Write-Info "Waiting for new pod to be ready..."
    Start-Sleep -Seconds $WaitSeconds
    
    $docsPodAfter = kubectl -n $Namespace get pods -l app=docs -o jsonpath='{.items[0].metadata.name}'
    Write-Host "    After: $docsPodAfter" -ForegroundColor White
    
    # Test docs health
    Write-Info "Testing docs health endpoint..."
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8777/health" -TimeoutSec 5
        if ($health.status -eq "ok") {
            Write-Success "Docs health check passed"
        }
    } catch {
        Write-Failure "Docs health check failed: $_"
    }
    
    Write-Success "DRILL 3 COMPLETE"
}

# Drill 4: Network Partition (NetworkPolicy)
if ($Drill -eq "network-partition" -or $Drill -eq "all") {
    Write-Status "DRILL 4: Network Partition Simulation" "Magenta"
    
    Write-Info "Creating restrictive NetworkPolicy to block bridge → llama..."
    
    $restrictivePolicy = @"
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: bridge-network-partition
  namespace: $Namespace
spec:
  podSelector:
    matchLabels:
      app: bridge
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: qdrant
    ports:
    - protocol: TCP
      port: 6333
"@
    
    $restrictivePolicy | kubectl apply -f -
    
    Write-Info "Waiting 10 seconds for policy to take effect..."
    Start-Sleep -Seconds 10
    
    Write-Info "Testing bridge call (should fail to reach LLM)..."
    try {
        $response = Invoke-WebRequest `
            -Uri "http://localhost:8888/call" `
            -Method POST `
            -Headers @{"x-api-key"=$env:AGENT_KEY; "Content-Type"="application/json"} `
            -Body '{"tool":"llama","params":{"prompt":"test"}}' `
            -UseBasicParsing `
            -TimeoutSec 10
        
        Write-Info "Call completed with status: $($response.StatusCode)"
    } catch {
        Write-Success "Call failed as expected (network partition working)"
    }
    
    Write-Info "Removing restrictive NetworkPolicy..."
    kubectl -n $Namespace delete networkpolicy bridge-network-partition
    
    Write-Info "Re-applying normal egress policy..."
    kubectl apply -f k8s/bridge-egress-policy.yaml
    
    Write-Info "Waiting 10 seconds for policy to restore..."
    Start-Sleep -Seconds 10
    
    Write-Info "Testing bridge call (should succeed now)..."
    try {
        $response = Invoke-WebRequest `
            -Uri "http://localhost:8888/call" `
            -Method POST `
            -Headers @{"x-api-key"=$env:AGENT_KEY; "Content-Type"="application/json"} `
            -Body '{"tool":"llama","params":{"prompt":"test"}}' `
            -UseBasicParsing `
            -TimeoutSec 10
        
        if ($response.StatusCode -eq 200) {
            Write-Success "Bridge call succeeded (network restored)"
        }
    } catch {
        Write-Failure "Bridge call still failing: $_"
    }
    
    Write-Success "DRILL 4 COMPLETE"
}

Write-Status "ALL CHAOS DRILLS COMPLETE" "Green"
Write-Host "`n✅ Results:" -ForegroundColor Green
Write-Host "   - Qdrant failover: Docs should have fallen back to keyword search" -ForegroundColor White
Write-Host "   - Pod restarts: HPA should have maintained traffic flow" -ForegroundColor White
Write-Host "   - Alerts: Should have fired for relevant failures" -ForegroundColor White
Write-Host "   - Network partition: Should have blocked then restored connectivity" -ForegroundColor White
Write-Host "`nCheck Grafana dashboard and Prometheus alerts for confirmation." -ForegroundColor Cyan
