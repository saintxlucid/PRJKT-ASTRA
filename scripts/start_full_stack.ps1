param(
    [switch]$Rebuild
)

Write-Host "`n[*] Starting ASTRA Full Stack (Bridge + Llama + Qdrant + Docs + Prometheus + Grafana)" -ForegroundColor Cyan

Push-Location "src/astra/bridge"

if ($Rebuild) {
    docker-compose -f docker-compose.full.yml up -d --build
} else {
    docker-compose -f docker-compose.full.yml up -d
}

Write-Host "\nServices:" -ForegroundColor Green
Write-Host "  Bridge:     http://localhost:8765" -ForegroundColor Gray
Write-Host "  Llama:      http://localhost:8001" -ForegroundColor Gray
Write-Host "  Qdrant:     http://localhost:6333/dashboard" -ForegroundColor Gray
Write-Host "  Prometheus: http://localhost:9090" -ForegroundColor Gray
Write-Host "  Grafana:    http://localhost:3000 (admin/admin)" -ForegroundColor Gray

Pop-Location
