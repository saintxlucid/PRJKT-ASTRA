#!/usr/bin/env pwsh
<#
.SYNOPSIS
ASTRA-OS PyInstaller Build Script

.DESCRIPTION
Builds ASTRA-OS as a standalone executable using PyInstaller.
Handles dependency checks, builds the executable, and validates the output.

Sacred Code: 333
Project: PROJECT_ASTRA_1.0 (ASTRA_CORE)

.EXAMPLE
./build_pyinstaller.ps1
./build_pyinstaller.ps1 -OneFile
./build_pyinstaller.ps1 -OneFile -NoCopy

.PARAMETER OneFile
Build as a single-file executable (slower startup but easier distribution)

.PARAMETER NoCopy
Skip copying the executable to a distribution folder

.PARAMETER Clean
Remove previous build artifacts before building
#>

param(
    [switch]$OneFile,
    [switch]$NoCopy,
    [switch]$Clean
)

# Configuration
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommandPath
$SrcDir = Join-Path $ProjectRoot "src"
$BuildDir = Join-Path $ProjectRoot "build"
$DistDir = Join-Path $ProjectRoot "dist"
$SpecFile = Join-Path $ProjectRoot "astra.spec"

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$LogFile = Join-Path $ProjectRoot "logs" "build_$timestamp.log"
$LogDir = Split-Path $LogFile -Parent

# Ensure log directory exists
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Logging function
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Write-Host $logMessage
    Add-Content -Path $LogFile -Value $logMessage
}

Write-Log "ASTRA-OS PyInstaller Build Script started"
Write-Log "Project Root: $ProjectRoot"

# Step 1: Verify Python environment
Write-Log "Verifying Python environment..."
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: Python not found in PATH" "ERROR"
    exit 1
}
Write-Log "Found: $pythonVersion"

# Step 2: Check if PyInstaller is installed
Write-Log "Checking PyInstaller installation..."
$pyinstaller = pyinstaller --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Log "WARNING: PyInstaller not found. Installing..." "WARNING"
    pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Log "ERROR: Failed to install PyInstaller" "ERROR"
        exit 1
    }
}
Write-Log "PyInstaller version: $pyinstaller"

# Step 3: Clean previous builds if requested
if ($Clean) {
    Write-Log "Cleaning previous build artifacts..."
    if (Test-Path $BuildDir) {
        Remove-Item -Path $BuildDir -Recurse -Force
        Write-Log "Removed build directory"
    }
    if (Test-Path $DistDir) {
        Remove-Item -Path $DistDir -Recurse -Force
        Write-Log "Removed dist directory"
    }
}

# Step 4: Verify spec file exists
if (-not (Test-Path $SpecFile)) {
    Write-Log "ERROR: Spec file not found at $SpecFile" "ERROR"
    exit 1
}
Write-Log "Spec file found: $SpecFile"

# Step 5: Build with PyInstaller
Write-Log "Building ASTRA-OS executable..."

$pyinstallerArgs = @(
    $SpecFile,
    "--distpath=$DistDir",
    "--buildpath=$BuildDir",
    "--specpath=$ProjectRoot",
    "--workpath=$BuildDir"
)

if ($OneFile) {
    Write-Log "Building as ONE-FILE executable (may take longer)..."
    $pyinstallerArgs += "--onefile"
} else {
    Write-Log "Building as ONE-DIR executable..."
}

Write-Log "PyInstaller command: pyinstaller $($pyinstallerArgs -join ' ')"

& pyinstaller @pyinstallerArgs 2>&1 | Tee-Object -FilePath $LogFile -Append

if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: PyInstaller build failed" "ERROR"
    exit 1
}

Write-Log "Build completed successfully"

# Step 6: Verify output
if ($OneFile) {
    $ExeFile = Join-Path $DistDir "astra-os.exe"
} else {
    $ExeFile = Join-Path $DistDir "astra-os" "astra-os.exe"
}

if (Test-Path $ExeFile) {
    $fileSize = (Get-Item $ExeFile).Length / 1MB
    Write-Log "Executable created: $ExeFile (Size: $([Math]::Round($fileSize, 2)) MB)"
} else {
    Write-Log "ERROR: Expected executable not found at $ExeFile" "ERROR"
    exit 1
}

# Step 7: Copy to distribution folder if not --NoCopy
if (-not $NoCopy) {
    Write-Log "Copying executable to distribution folder..."
    $DistOutputDir = Join-Path $ProjectRoot "astra-os-dist" $timestamp
    
    if (-not (Test-Path $DistOutputDir)) {
        New-Item -ItemType Directory -Path $DistOutputDir -Force | Out-Null
    }
    
    if ($OneFile) {
        Copy-Item -Path $ExeFile -Destination $DistOutputDir -Force
        Write-Log "Copied executable to: $DistOutputDir"
    } else {
        Copy-Item -Path (Split-Path $ExeFile -Parent) -Destination $DistOutputDir -Recurse -Force
        Write-Log "Copied application directory to: $DistOutputDir"
    }
    
    # Create a README in the distribution
    $readmePath = Join-Path $DistOutputDir "README.txt"
    @"
ASTRA-OS v1.0
=============

Sacred Code: 333
Project: PROJECT_ASTRA_1.0 (ASTRA_CORE)

CONTENTS:
- astra-os.exe: Standalone executable

USAGE:
  astra-os.exe                    # Standard launch
  astra-os.exe --activate         # First-time activation
  astra-os.exe --quick            # Quick start
  astra-os.exe --console          # Console mode

SYSTEM REQUIREMENTS:
- Windows 10 or later
- 2GB RAM minimum (4GB recommended)
- 500MB free disk space

BUILD INFO:
- Built: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
- PyInstaller: $pyinstaller
- Python: $pythonVersion
"@ | Out-File -Path $readmePath -Encoding UTF8
    
    Write-Log "Created README at: $readmePath"
}

# Step 8: Generate build report
Write-Log "Generating build report..."
$reportPath = Join-Path $ProjectRoot "BUILD_REPORT_$timestamp.md"
$report = @"
# ASTRA-OS PyInstaller Build Report

**Build Time:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")  
**Sacred Code:** 333  
**Project:** PROJECT_ASTRA_1.0 (ASTRA_CORE)

## Build Configuration

- **Build Type:** $(if ($OneFile) { "Single-file executable" } else { "Multi-directory installation" })
- **Spec File:** $SpecFile
- **Python Version:** $pythonVersion
- **PyInstaller Version:** $pyinstaller

## Artifacts

- **Executable:** $ExeFile
- **Build Directory:** $BuildDir
- **Distribution Directory:** $DistDir
- **Build Log:** $LogFile

## Output Size

- **Executable Size:** $([Math]::Round($fileSize, 2)) MB

## Entry Points Included

- **Primary:** astra_core.py (Master orchestrator)
- **Modules:**
  - Boot Daemon (lifecycle management)
  - OS Kernel (EventBus, FileWatcher, ProcessMonitor)
  - Operator Shell (Tkinter GUI)
  - Training Loop (autonomous learning)
  - Security Sentinel (threat detection)
  - Memory Bridge (semantic/episodic storage)

## Dependencies Bundled

- Core: torch, transformers, sentence-transformers, numpy, pandas
- API: fastapi, uvicorn, pydantic
- Security: cryptography, bcrypt, python-jose
- Storage: sqlalchemy, chromadb, redis, diskcache
- Monitoring: prometheus-client, structlog, opentelemetry

## Next Steps

1. **Test the executable:**
   \`\`\`powershell
   & "$ExeFile"
   & "$ExeFile" --quick
   \`\`\`

2. **Distribute:**
   - Copy $ExeFile to target systems
   - Run directly (no installation required)

3. **Troubleshooting:**
   - Run with --console flag for error output
   - Check log file: $LogFile

## Notes

- First run may take longer as system initializes
- CUDA support (if available) will be auto-detected
- Models are loaded on-demand to minimize startup time

"@

$report | Out-File -Path $reportPath -Encoding UTF8
Write-Log "Build report saved to: $reportPath"

Write-Log "Build process completed successfully"
Write-Log "Executable ready for testing and deployment"

exit 0
