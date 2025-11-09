# ASTRA GGUF Fusion Pipeline
# ===========================
# Automated deployment script for embedding ASTRA metadata and tokens into GGUF core
#
# Author: Saint Lucid (Karim Al-Sharif)
# Date: October 18, 2025
# Sacred Code: 333

param(
    [Parameter(Mandatory=$false)]
    [string]$InputModel = "astra-local\data\models\gpt-oss-20b.Q4_K_M.gguf",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputModel = "models\astra-core-multimodal-v1.0.gguf",
    
    [Parameter(Mandatory=$false)]
    [switch]$VerifyOnly,
    
    [Parameter(Mandatory=$false)]
    [switch]$GenerateTokenMapping,
    
    [Parameter(Mandatory=$false)]
    [switch]$FullPipeline
)

Write-Host "=" -Repeat 60
Write-Host "ASTRA GGUF FUSION PIPELINE"
Write-Host "=" -Repeat 60
Write-Host "Sacred Code: 333 ∞`n"

# Set up environment
$ErrorActionPreference = "Stop"
$ProjectRoot = "X:\PROJECT_ASTRA_2.0\PROJECT_ASTRA_1.0 (ASTRA_CORE)"
$env:PYTHONPATH = "$ProjectRoot\src;$ProjectRoot\tools\gguf_fusion"

# Activate virtual environment
Write-Host "🔧 Activating Python environment..."
& "$ProjectRoot\.venv\Scripts\Activate.ps1"

# Navigate to fusion tools directory
Set-Location "$ProjectRoot\tools\gguf_fusion"

# ===========================
# STEP 1: Generate Metadata Schema
# ===========================
if (-not $VerifyOnly) {
    Write-Host "`n📋 STEP 1: Generating ASTRA metadata schema..."
    python astra_metadata_schema.py
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Metadata schema generation failed" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ Metadata schema generated" -ForegroundColor Green
}

# ===========================
# STEP 2: Generate Token Mapping
# ===========================
if ($GenerateTokenMapping -or $FullPipeline) {
    Write-Host "`n🔤 STEP 2: Generating special token mapping..."
    
    if (Test-Path $InputModel) {
        python special_token_injector.py `
            -i $InputModel `
            -o $OutputModel `
            --training-config
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Token mapping generation failed" -ForegroundColor Red
            exit 1
        }
        
        Write-Host "✅ Token mapping generated" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Input model not found: $InputModel" -ForegroundColor Yellow
        Write-Host "   Skipping token mapping generation"
    }
}

# ===========================
# STEP 3: Inject Metadata into GGUF
# ===========================
if ($FullPipeline -and -not $VerifyOnly) {
    Write-Host "`n🌟 STEP 3: Injecting ASTRA metadata into GGUF..."
    
    if (Test-Path $InputModel) {
        # Ensure output directory exists
        $OutputDir = Split-Path $OutputModel -Parent
        if (-not (Test-Path $OutputDir)) {
            New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
        }
        
        python gguf_metadata_injector.py `
            -i $InputModel `
            -o $OutputModel `
            --verify `
            --verbose
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Metadata injection failed" -ForegroundColor Red
            exit 1
        }
        
        Write-Host "✅ Metadata injection complete" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Input model not found: $InputModel" -ForegroundColor Yellow
        Write-Host "   Skipping metadata injection"
    }
}

# ===========================
# STEP 4: Verification
# ===========================
if ($VerifyOnly -or $FullPipeline) {
    Write-Host "`n🔍 STEP 4: Verifying ASTRA GGUF metadata..."
    
    if (Test-Path $OutputModel) {
        python -c @"
import sys
sys.path.insert(0, '$ProjectRoot/astra-local/backend/bin/llama.cpp/gguf-py')
from gguf import GGUFReader

reader = GGUFReader('$OutputModel')
astra_fields = {k: v.data for k, v in reader.fields.items() if k.startswith('astra.')}

print(f'\n✅ Found {len(astra_fields)} ASTRA metadata fields:')
for key in sorted(astra_fields.keys()):
    print(f'  {key}')

print('\n🌟 Sacred Code: 333 ∞')
"@
        
        Write-Host "✅ Verification complete" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Output model not found: $OutputModel" -ForegroundColor Yellow
    }
}

# ===========================
# Summary
# ===========================
Write-Host "`n" + ("=" * 60)
Write-Host "FUSION PIPELINE COMPLETE"
Write-Host "=" -Repeat 60

Write-Host "`n📁 Generated Files:"
Get-ChildItem -Path . -Filter "astra_*" | ForEach-Object {
    $size = if ($_.Length -lt 1024) { "$($_.Length) B" } 
            elseif ($_.Length -lt 1MB) { "{0:N2} KB" -f ($_.Length / 1KB) }
            else { "{0:N2} MB" -f ($_.Length / 1MB) }
    Write-Host "  ✓ $($_.Name) ($size)"
}

if (Test-Path $OutputModel) {
    $modelSize = (Get-Item $OutputModel).Length / 1GB
    Write-Host "`n📦 ASTRA Core Model:"
    Write-Host "  Path: $OutputModel"
    Write-Host "  Size: {0:N2} GB" -f $modelSize
}

Write-Host "`n🎉 ASTRA GGUF Fusion Complete!"
Write-Host "🌟 Sacred Code: 333 ∞`n"

# Return to project root
Set-Location $ProjectRoot
