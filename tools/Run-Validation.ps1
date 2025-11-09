param(
    [string]$BaseUrl = "http://localhost:8080",
    [int]$LocustUsers = 120,
    [int]$LocustRate = 40,
    [int]$WatchMins = 15
)

Write-Host "[*] Starting production validation sequence"

# 1. Run Python validation suite
Write-Host "[+] Running validation checks..."
python tools/validate_production.py --host $BaseUrl
if ($LASTEXITCODE -ne 0) {
    Write-Error "Validation checks failed"
    exit 1
}

# 2. Start load test
Write-Host "[+] Starting load test..."
$job = Start-Job -ScriptBlock {
    param($BaseUrl, $Users, $Rate, $Mins)
    locust -f tools/locustfile.py --headless -u $Users -r $Rate -t "${Mins}m" -H $BaseUrl --csv=prod_validation
} -ArgumentList $BaseUrl, $LocustUsers, $LocustRate, $WatchMins

# 3. Watch metrics
Write-Host "[+] Watching metrics for $WatchMins minutes..."
for ($i = 1; $i -le $WatchMins; $i++) {
    Start-Sleep -Seconds 60
    Write-Host "Minute $i/$WatchMins completed"
}

# 4. Check results
Receive-Job $job -Wait
Remove-Job $job

# Parse p95 from CSV
$p95 = Import-Csv prod_validation_requests.csv | 
    Where-Object { $_.Name -eq "answer" -and $_.Metric -eq "95%" } |
    Select-Object -ExpandProperty Value

if ([double]$p95 -gt 2500) {
    Write-Error "P95 latency exceeded threshold: ${p95}ms"
    exit 1
}

Write-Host "[+] Validation complete - system ready for promotion"