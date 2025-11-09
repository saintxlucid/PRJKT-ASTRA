#!/usr/bin/env pwsh
# scripts/ship.ps1
# Unified launcher: starts llama.cpp + ASTRA API, waits for readiness, runs smoke tests

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$ErrorActionPreference = "Stop"

# --- CONFIG ---
$RepoRoot   = "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
$LlmPort    = 8001
$ApiPort    = 8080
$LlamaExe   = "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\astra-local\backend\bin\llama.cpp\build\bin\Release\llama-server.exe"
$ModelPath  = "X:\PROJECT_ASTRA_1.0 (ASTRA_CORE)\astra-local\data\models\gpt-oss-20b.Q4_K_M.gguf"
$Ctx        = 131072                                         # if OOM, try 65536
$GpuLayers  = 0                                               # set >0 if using CUDA
$HostBind   = "127.0.0.1"                                    # use 0.0.0.0 only if LAN access needed
$AstraCmd   = "python -m uvicorn src.astra.api.app:app --host $HostBind --port $ApiPort --log-level info"
$Smoke      = Join-Path $RepoRoot "scripts\smoke_test.ps1"

function Test-Url {
  param($Url, [int]$Tries = 30, [int]$Sleep = 2, $Name = $Url)
  for ($i=0; $i -lt $Tries; $i++) {
    try { Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null; return $true }
    catch { Start-Sleep -Seconds $Sleep }
  }
  Write-Host "$Name NOT READY after $Tries tries" -ForegroundColor Red
  return $false
}

function Start-Llama {
  param($Exe, $Model, $Port, $Ctx, $GpuLayers, $HostBind)
  if (-not (Test-Path $Exe))  { throw "llama-server not found at $Exe" }
  if (-not (Test-Path $Model)) { throw "Model not found at $Model" }
  $llamaArgs = @(
    "--model", "`"$Model`"",
    "--host",  "$HostBind",
    "--port",  "$Port",
    "--ctx-size", "$Ctx"
  )
  if ($GpuLayers -gt 0) { $llamaArgs += @("--n-gpu-layers", "$GpuLayers") }
  Start-Process -FilePath $Exe -ArgumentList $llamaArgs -WindowStyle Minimized
}

function Start-Astra {
  param($Repo, $Cmd)
  Push-Location $Repo
  Start-Process -FilePath "powershell.exe" -ArgumentList "-NoLogo","-NoExit","-Command",$Cmd -WindowStyle Minimized
  Pop-Location
}

Write-Host "== ASTRA CORE SHIP ==" -ForegroundColor Cyan

# 1) LLM server
if (Test-Url "http://${HostBind}:${LlmPort}/v1/models" 1 1 "LLM") {
  Write-Host "LLM already running on :$LlmPort" -ForegroundColor Green
} else {
  Write-Host "Starting llama.cpp server..." -ForegroundColor Yellow
  Start-Llama -Exe $LlamaExe -Model $ModelPath -Port $LlmPort -Ctx $Ctx -GpuLayers $GpuLayers -HostBind $HostBind
  if (-not (Test-Url "http://${HostBind}:${LlmPort}/v1/models" 40 2 "LLM")) { exit 1 }
  Write-Host "LLM_OK" -ForegroundColor Green
}

# 2) ASTRA API
if (Test-Url "http://${HostBind}:${ApiPort}/v1/system/health" 1 1 "API") {
  Write-Host "API already running on :$ApiPort" -ForegroundColor Green
} else {
  Write-Host "Starting ASTRA API..." -ForegroundColor Yellow
  Start-Astra -Repo $RepoRoot -Cmd $AstraCmd
  if (-not (Test-Url "http://${HostBind}:${ApiPort}/v1/system/health" 40 2 "API")) { exit 1 }
  Write-Host "API_OK" -ForegroundColor Green
}

# 3) Bridge health
if (-not (Test-Url "http://${HostBind}:${ApiPort}/v1/bridge/healthz" 20 2 "BRIDGE")) { exit 1 }
Write-Host "BRIDGE_OK" -ForegroundColor Green

# 4) Smoke tests
if (-not (Test-Path $Smoke)) { Write-Host "Smoke test not found at $Smoke" -ForegroundColor Yellow }
else {
  Write-Host "Running smoke test..." -ForegroundColor Cyan
  Push-Location $RepoRoot
  powershell -ExecutionPolicy Bypass -File $Smoke
  Pop-Location
}

Write-Host "`n=== SUMMARY ===" -ForegroundColor Cyan
Write-Host "LLM:    ONLINE on :$LlmPort" -ForegroundColor Green
Write-Host "API:    ONLINE on :$ApiPort" -ForegroundColor Green
Write-Host "BRIDGE: MOUNTED" -ForegroundColor Green
Write-Host "SMOKE:  CHECK OUTPUT ABOVE" -ForegroundColor Green
Write-Host "READY TO TAG: v1.0.0" -ForegroundColor Magenta
