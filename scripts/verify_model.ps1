# ═══════════════════════════════════════════════════════════════
#  ASTRA Model Integrity Verifier
# ═══════════════════════════════════════════════════════════════
#
#  Verifies model file integrity using SHA-256 checksums.
#
#  Usage:
#    # Verify all models in models/ directory
#    .\scripts\verify_model.ps1
#
#    # Verify specific model
#    .\scripts\verify_model.ps1 -ModelPath "X:\path\to\model.gguf"
#
#    # Generate checksum for new model (add to checksums.txt)
#    .\scripts\verify_model.ps1 -ModelPath "X:\path\to\model.gguf" -GenerateChecksum
#
# ═══════════════════════════════════════════════════════════════

[CmdletBinding()]
param(
    [Parameter(HelpMessage="Path to specific model file to verify")]
    [string]$ModelPath = $null,
    
    [Parameter(HelpMessage="Generate checksum instead of verifying")]
    [switch]$GenerateChecksum,
    
    [Parameter(HelpMessage="Path to checksums.txt file")]
    [string]$ChecksumFile = $null
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

if (-not $ChecksumFile) {
    $ChecksumFile = Join-Path $RepoRoot "models\checksums.txt"
}

# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

function Get-ModelChecksum {
    param([string]$Path)
    
    Write-Host "  🔐 Computing SHA-256 for $(Split-Path -Leaf $Path)..." -ForegroundColor Gray
    $hash = (Get-FileHash -Path $Path -Algorithm SHA256).Hash
    return $hash.ToUpper()
}

function Get-ExpectedChecksum {
    param([string]$ModelName)
    
    if (!(Test-Path $ChecksumFile)) {
        return $null
    }
    
    $checksumLines = Get-Content $ChecksumFile | Where-Object { $_ -notmatch '^#' -and $_.Trim() -ne '' }
    $matchingLine = $checksumLines | Where-Object { $_ -match [regex]::Escape($ModelName) }
    
    if ($matchingLine) {
        # Extract hash from line (first token before whitespace)
        $expectedHash = ($matchingLine -split '\s+')[0]
        return $expectedHash.ToUpper()
    }
    
    return $null
}

function Verify-ModelFile {
    param([string]$Path)
    
    if (!(Test-Path $Path)) {
        Write-Host "  ❌ File not found: $Path" -ForegroundColor Red
        return $false
    }
    
    $modelName = Split-Path -Leaf $Path
    $fileSize = (Get-Item $Path).Length / 1GB
    
    Write-Host "`n📦 Verifying: $modelName" -ForegroundColor Cyan
    Write-Host "   Size: $($fileSize.ToString('F2')) GB" -ForegroundColor Gray
    
    $expectedHash = Get-ExpectedChecksum $modelName
    
    if (-not $expectedHash) {
        Write-Host "   ⚠️  No checksum entry in checksums.txt" -ForegroundColor Yellow
        Write-Host "   💡 Generate with: -GenerateChecksum" -ForegroundColor Gray
        return $null
    }
    
    $actualHash = Get-ModelChecksum $Path
    
    if ($actualHash -eq $expectedHash) {
        Write-Host "   ✅ VERIFIED - Checksum matches" -ForegroundColor Green
        Write-Host "      $actualHash" -ForegroundColor Gray
        return $true
    } else {
        Write-Host "   ❌ FAILED - Checksum mismatch!" -ForegroundColor Red
        Write-Host "      Expected: $expectedHash" -ForegroundColor Red
        Write-Host "      Actual:   $actualHash" -ForegroundColor Red
        Write-Host "   ⚠️  Model may be corrupted or tampered with!" -ForegroundColor Yellow
        return $false
    }
}

function Generate-ChecksumEntry {
    param([string]$Path)
    
    if (!(Test-Path $Path)) {
        Write-Host "❌ File not found: $Path" -ForegroundColor Red
        exit 1
    }
    
    $modelName = Split-Path -Leaf $Path
    $fileSize = (Get-Item $Path).Length / 1GB
    
    Write-Host "`n📦 Generating checksum for: $modelName" -ForegroundColor Cyan
    Write-Host "   Size: $($fileSize.ToString('F2')) GB" -ForegroundColor Gray
    Write-Host "   This may take a few minutes..." -ForegroundColor Gray
    
    $hash = Get-ModelChecksum $Path
    
    Write-Host "`n✅ Checksum generated:" -ForegroundColor Green
    Write-Host "$hash  $modelName" -ForegroundColor White
    
    Write-Host "`n💡 Add this line to models\checksums.txt:" -ForegroundColor Cyan
    Write-Host "$hash  $modelName" -ForegroundColor Yellow
    
    # Optionally append to checksums.txt
    if (Test-Path $ChecksumFile) {
        $response = Read-Host "`nAppend to checksums.txt? (y/n)"
        if ($response -eq 'y' -or $response -eq 'Y') {
            Add-Content -Path $ChecksumFile -Value "$hash  $modelName"
            Write-Host "✅ Added to checksums.txt" -ForegroundColor Green
        }
    }
}

# ═══════════════════════════════════════════════════════════════
# MAIN LOGIC
# ═══════════════════════════════════════════════════════════════

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║               ASTRA Model Integrity Verifier                  ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

if ($GenerateChecksum) {
    # Generate mode
    if (-not $ModelPath) {
        Write-Host "❌ -ModelPath required with -GenerateChecksum" -ForegroundColor Red
        exit 1
    }
    
    Generate-ChecksumEntry $ModelPath
    exit 0
}

# Verify mode
if ($ModelPath) {
    # Verify specific model
    $result = Verify-ModelFile $ModelPath
    
    if ($result -eq $true) {
        Write-Host "`n✅ Model verification passed!" -ForegroundColor Green
        exit 0
    } elseif ($result -eq $false) {
        Write-Host "`n❌ Model verification FAILED!" -ForegroundColor Red
        Write-Host "⚠️  DO NOT USE THIS MODEL - Re-download from trusted source" -ForegroundColor Yellow
        exit 1
    } else {
        Write-Host "`n⚠️  No checksum available for verification" -ForegroundColor Yellow
        exit 2
    }
} else {
    # Verify all models in models/ directory
    $modelsDir = Join-Path $RepoRoot "models"
    
    if (!(Test-Path $modelsDir)) {
        Write-Host "⚠️  models/ directory not found at: $modelsDir" -ForegroundColor Yellow
        Write-Host "💡 Specify a model with -ModelPath" -ForegroundColor Gray
        exit 2
    }
    
    $modelFiles = Get-ChildItem -Path $modelsDir -Filter "*.gguf" -File
    
    if ($modelFiles.Count -eq 0) {
        Write-Host "⚠️  No .gguf files found in models/" -ForegroundColor Yellow
        exit 2
    }
    
    Write-Host "`n🔍 Found $($modelFiles.Count) model(s) to verify`n" -ForegroundColor Cyan
    
    $results = @{
        Passed = 0
        Failed = 0
        NoChecksum = 0
    }
    
    foreach ($modelFile in $modelFiles) {
        $result = Verify-ModelFile $modelFile.FullName
        
        if ($result -eq $true) {
            $results.Passed++
        } elseif ($result -eq $false) {
            $results.Failed++
        } else {
            $results.NoChecksum++
        }
    }
    
    # Summary
    Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║                      VERIFICATION SUMMARY                      ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host "✅ Passed:       $($results.Passed)" -ForegroundColor Green
    Write-Host "❌ Failed:       $($results.Failed)" -ForegroundColor $(if ($results.Failed -gt 0) { "Red" } else { "Gray" })
    Write-Host "⚠️  No Checksum: $($results.NoChecksum)" -ForegroundColor $(if ($results.NoChecksum -gt 0) { "Yellow" } else { "Gray" })
    Write-Host ""
    
    if ($results.Failed -gt 0) {
        Write-Host "⚠️  CRITICAL: $($results.Failed) model(s) failed verification!" -ForegroundColor Red
        Write-Host "   DO NOT USE failed models - re-download from trusted source" -ForegroundColor Red
        exit 1
    } elseif ($results.Passed -gt 0) {
        Write-Host "✅ All verified models passed integrity checks!" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "⚠️  No models could be verified (missing checksums)" -ForegroundColor Yellow
        Write-Host "💡 Generate checksums with: -ModelPath <path> -GenerateChecksum" -ForegroundColor Gray
        exit 2
    }
}
