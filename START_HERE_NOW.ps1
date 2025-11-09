# ⚡ ASTRA Emergency Start Script
# Run this FIRST to get your system operational

Write-Host "🚀 ASTRA Emergency Start - Choose LLM Option" -ForegroundColor Cyan
Write-Host ""

Write-Host "Option 1: OpenAI (Fastest - Requires API Key)" -ForegroundColor Yellow
Write-Host "Option 2: Ollama (Free - Requires Install)" -ForegroundColor Yellow
Write-Host "Option 3: Your llama.cpp (Local)" -ForegroundColor Yellow
Write-Host ""

$choice = Read-Host "Enter choice (1, 2, or 3)"

switch ($choice) {
    "1" {
        Write-Host "🔑 OpenAI Setup" -ForegroundColor Green
        $apiKey = Read-Host "Enter your OpenAI API key (sk-...)"
        
        $env:ASTRA_LLM_BASE_URL = "https://api.openai.com/v1"
        $env:ASTRA_LLM_MODEL_NAME = "gpt-4o"
        $env:ASTRA_LLM_API_KEY = $apiKey
        
        Write-Host "✅ Environment configured" -ForegroundColor Green
        Write-Host "Running ASTRA demo..." -ForegroundColor Cyan
        
        python quick_start_unified.py demo
    }
    
    "2" {
        Write-Host "🦙 Ollama Setup" -ForegroundColor Green
        Write-Host "Checking if Ollama is installed..." -ForegroundColor Yellow
        
        $ollamaInstalled = Get-Command ollama -ErrorAction SilentlyContinue
        
        if (-not $ollamaInstalled) {
            Write-Host "❌ Ollama not found" -ForegroundColor Red
            Write-Host "Install with: winget install Ollama.Ollama" -ForegroundColor Yellow
            Write-Host "Then run this script again" -ForegroundColor Yellow
            exit 1
        }
        
        Write-Host "✅ Ollama found" -ForegroundColor Green
        Write-Host "Starting Ollama server..." -ForegroundColor Yellow
        
        Start-Process -NoNewWindow -FilePath "ollama" -ArgumentList "serve"
        
        Start-Sleep -Seconds 3
        
        Write-Host "Pulling llama3.1:70b model..." -ForegroundColor Yellow
        Write-Host "(This may take 5-10 minutes on first run)" -ForegroundColor Gray
        
        ollama pull llama3.1:70b
        
        $env:ASTRA_LLM_BASE_URL = "http://localhost:11434/v1"
        $env:ASTRA_LLM_MODEL_NAME = "llama3.1:70b"
        $env:ASTRA_LLM_API_KEY = "ollama"
        
        Write-Host "✅ Environment configured" -ForegroundColor Green
        Write-Host "Running ASTRA demo..." -ForegroundColor Cyan
        
        python quick_start_unified.py demo
    }
    
    "3" {
        Write-Host "🧠 Local llama.cpp Setup" -ForegroundColor Green
        
        $modelPath = Read-Host "Enter model path (or press Enter for default)"
        
        if (-not $modelPath) {
            $modelPath = "X:\MODELS\gpt-oss-20b\gpt-oss-20b.Q4_K_M.gguf"
        }
        
        if (-not (Test-Path $modelPath)) {
            Write-Host "❌ Model not found at: $modelPath" -ForegroundColor Red
            exit 1
        }
        
        Write-Host "Starting llama.cpp server..." -ForegroundColor Yellow
        Write-Host "This will open a new window - do NOT close it" -ForegroundColor Yellow
        
        Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "& '.\start_local_llm.ps1' -ModelPath '$modelPath'"
        
        Write-Host "Waiting for server to load (30 seconds)..." -ForegroundColor Gray
        Start-Sleep -Seconds 30
        
        $env:ASTRA_LLM_BASE_URL = "http://localhost:9010/v1"
        $env:ASTRA_LLM_MODEL_NAME = "gpt-oss-20b"
        $env:ASTRA_LLM_API_KEY = "dummy"
        
        Write-Host "✅ Environment configured" -ForegroundColor Green
        Write-Host "Running ASTRA demo..." -ForegroundColor Cyan
        
        python quick_start_unified.py demo
    }
    
    default {
        Write-Host "❌ Invalid choice" -ForegroundColor Red
        exit 1
    }
}
