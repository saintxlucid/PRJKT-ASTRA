# ⚡ TERMINAL 1: Start llama.cpp server
# Copy and paste this entire block into PowerShell

Write-Host "🧠 Starting llama.cpp server (GPT-OSS 20B)..." -ForegroundColor Cyan
Write-Host "Port: 9010 | Context: 131072 tokens" -ForegroundColor Gray
Write-Host ""
Write-Host "⚠️  KEEP THIS WINDOW OPEN" -ForegroundColor Yellow
Write-Host ""

# Start server (adjust paths if needed)
.\server.exe -m .\gpt-oss-20b.Q4_K_M.gguf -c 131072 --host 0.0.0.0 --port 9010 --chat-template openai
