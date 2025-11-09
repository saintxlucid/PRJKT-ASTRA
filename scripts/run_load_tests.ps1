# Create conversation
$convBody = '{"title":"GPT-OSS Baseline Load Test"}'
$conv = Invoke-RestMethod -Method POST -Uri http://127.0.0.1:8080/v1/conversations/ -ContentType application/json -Body $convBody
$convId = $conv.id
Write-Output "Conversation ID: $convId"

# Create payload file
$payload = @{
    conversation_id = $convId
    message = "One-line greeting, please."
    use_memory = $false
    temperature = 0.2
    max_tokens = 32
} | ConvertTo-Json

$payload | Set-Content X:\PROJECT_ASTRA\data\load_test_payload.json
Write-Output "Payload created"

# Set env vars for baseline test
$env:ASTRA_LOAD_URL = "http://127.0.0.1:8080/v1/chat/"
$env:ASTRA_LOAD_METHOD = "POST"
$env:ASTRA_LOAD_CONC = "24"
$env:ASTRA_LOAD_SECS = "45"
$env:ASTRA_LOAD_RPS = "24"
$env:ASTRA_LOAD_PAYLOAD = "X:\PROJECT_ASTRA\data\load_test_payload.json"

Write-Output "`n=== BASELINE LOAD TEST (24 RPS, 45 seconds) ===`n"
.\.venv\Scripts\python.exe .\scripts\load_test.py | Tee-Object X:\PROJECT_ASTRA\data\baseline_out.txt

# Save baseline metrics
(Invoke-WebRequest http://127.0.0.1:8080/metrics).Content | Set-Content X:\PROJECT_ASTRA\data\baseline_metrics.prom
Write-Output "`nBaseline metrics saved"

# Run saturation test
$env:ASTRA_LOAD_CONC = "60"
$env:ASTRA_LOAD_SECS = "20"
$env:ASTRA_LOAD_RPS = "60"

Write-Output "`n=== SATURATION LOAD TEST (60 RPS, 20 seconds) ===`n"
.\.venv\Scripts\python.exe .\scripts\load_test.py | Tee-Object X:\PROJECT_ASTRA\data\saturation_out.txt

# Save saturation metrics
(Invoke-WebRequest http://127.0.0.1:8080/metrics).Content | Set-Content X:\PROJECT_ASTRA\data\saturation_metrics.prom
Write-Output "`nSaturation metrics saved"

# Append to DEPLOYMENT_STATUS.md
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$baseline = Get-Content X:\PROJECT_ASTRA\data\baseline_out.txt -Raw
$saturation = Get-Content X:\PROJECT_ASTRA\data\saturation_out.txt -Raw

Add-Content DEPLOYMENT_STATUS.md "`n"
Add-Content DEPLOYMENT_STATUS.md "========================================"
Add-Content DEPLOYMENT_STATUS.md "`n## Validation Run - $stamp"
Add-Content DEPLOYMENT_STATUS.md "`n### Baseline Load Test - 24 concurrent, 24 RPS, 45 seconds"
Add-Content DEPLOYMENT_STATUS.md "`n``````"
Add-Content DEPLOYMENT_STATUS.md $baseline
Add-Content DEPLOYMENT_STATUS.md "``````"
Add-Content DEPLOYMENT_STATUS.md "`n### Saturation Load Test - 60 concurrent, 60 RPS, 20 seconds"
Add-Content DEPLOYMENT_STATUS.md "`n``````"
Add-Content DEPLOYMENT_STATUS.md $saturation
Add-Content DEPLOYMENT_STATUS.md "``````"
Add-Content DEPLOYMENT_STATUS.md "`n### Go/No-Go Decision: PENDING REVIEW"
Add-Content DEPLOYMENT_STATUS.md "`n========================================"

Write-Output "`n✓ Results appended to DEPLOYMENT_STATUS.md"
Write-Output "✓ Load testing complete!"
