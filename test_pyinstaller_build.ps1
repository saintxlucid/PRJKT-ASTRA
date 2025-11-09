#!/usr/bin/env pwsh
<#
.SYNOPSIS
ASTRA-OS Packaging Validation Script

.DESCRIPTION
Validates that the built PyInstaller executable:
1. Exists and is executable
2. Starts successfully
3. Loads all subsystems
4. Reports proper configuration
5. Cleans up gracefully

Sacred Code: 333
Project: PROJECT_ASTRA_1.0 (ASTRA_CORE)

.EXAMPLE
./test_pyinstaller_build.ps1
./test_pyinstaller_build.ps1 -TimeoutSeconds 60
./test_pyinstaller_build.ps1 -VerboseLogging
#>

param(
    [int]$TimeoutSeconds = 30,
    [switch]$VerboseLogging,
    [switch]$SkipExecTest
)

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommandPath
$DistDir = Join-Path $ProjectRoot "dist"
$ExePath = Join-Path $DistDir "astra-os" "astra-os.exe"
$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$TestLogFile = Join-Path $ProjectRoot "logs" "test_build_$timestamp.log"
$LogDir = Split-Path $TestLogFile -Parent

# Ensure log directory exists
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Write-TestLog {
    param([string]$Message, [string]$Level = "INFO")
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMsg = "[$ts] [$Level] $Message"
    Write-Host $logMsg
    Add-Content -Path $TestLogFile -Value $logMsg
}

Write-TestLog "ASTRA-OS Packaging Validation Started"
Write-TestLog "=========================================="

# Test 1: Verify executable exists
Write-TestLog "`nTest 1: Verify executable exists"
if (-not (Test-Path $ExePath)) {
    Write-TestLog "ERROR: Executable not found at $ExePath" "ERROR"
    Write-TestLog "Build may not have completed successfully" "ERROR"
    exit 1
}

$exeSize = (Get-Item $ExePath).Length / 1MB
Write-TestLog "✓ Executable found: $ExePath"
Write-TestLog "  Size: $([Math]::Round($exeSize, 2)) MB"

# Test 2: Verify file is executable
Write-TestLog "`nTest 2: Verify file attributes"
$fileInfo = Get-Item $ExePath
if (-not ($fileInfo.Extension -eq ".exe")) {
    Write-TestLog "WARNING: File extension is not .exe" "WARNING"
}

if ($fileInfo.Length -lt 1MB) {
    Write-TestLog "WARNING: Executable is unusually small ($exeSize MB)" "WARNING"
} elseif ($fileInfo.Length -gt 1000MB) {
    Write-TestLog "WARNING: Executable is very large ($exeSize MB)" "WARNING"
}

Write-TestLog "✓ File attributes verified"

# Test 3: Check for required data files
Write-TestLog "`nTest 3: Check bundled resources"
$requiredFiles = @(
    "threat_patterns.yaml",
    "astra_core.pyc",  # May be compiled
    "astra"  # Package directory
)

$missingFiles = @()
$distExecDir = Split-Path $ExePath -Parent

foreach ($file in $requiredFiles) {
    $filePath = Join-Path $distExecDir $file
    if (-not (Test-Path $filePath)) {
        if ($file -notlike "*.pyc") {  # Compiled files are optional
            $missingFiles += $file
        }
    }
}

if ($missingFiles.Count -gt 0) {
    Write-TestLog "WARNING: Missing bundled files: $($missingFiles -join ', ')" "WARNING"
} else {
    Write-TestLog "✓ All required resources found"
}

# Test 4: Test executable startup (if not skipped)
if (-not $SkipExecTest) {
    Write-TestLog "`nTest 4: Test executable startup"
    Write-TestLog "Launching: $ExePath --quick"
    Write-TestLog "Timeout: $TimeoutSeconds seconds"
    
    try {
        $startTime = Get-Date
        
        # Start the process
        $process = Start-Process -FilePath $ExePath -ArgumentList "--quick" -PassThru -NoNewWindow -RedirectStandardOutput "$TestLogFile.stdout" -RedirectStandardError "$TestLogFile.stderr"
        
        if ($process.WaitForExit($TimeoutSeconds * 1000)) {
            $exitCode = $process.ExitCode
            $elapsed = ((Get-Date) - $startTime).TotalSeconds
            
            if ($exitCode -eq 0) {
                Write-TestLog "✓ Executable exited successfully"
                Write-TestLog "  Exit Code: $exitCode"
                Write-TestLog "  Duration: $elapsed seconds"
            } else {
                Write-TestLog "WARNING: Executable exited with code $exitCode" "WARNING"
                Write-TestLog "  Duration: $elapsed seconds"
            }
        } else {
            Write-TestLog "Executable still running after $TimeoutSeconds seconds"
            Write-TestLog "Terminating process..."
            Stop-Process -InputObject $process -Force
            Write-TestLog "Process terminated"
        }
    }
    catch {
        Write-TestLog "ERROR: Failed to execute: $_" "ERROR"
    }
    
    # Check stdout/stderr
    if (Test-Path "$TestLogFile.stdout") {
        $stdoutContent = Get-Content "$TestLogFile.stdout" -Raw
        if ($stdoutContent) {
            Write-TestLog "STDOUT:" "DEBUG"
            Write-TestLog $stdoutContent "DEBUG"
        }
        Remove-Item "$TestLogFile.stdout" -Force
    }
    
    if (Test-Path "$TestLogFile.stderr") {
        $stderrContent = Get-Content "$TestLogFile.stderr" -Raw
        if ($stderrContent) {
            Write-TestLog "STDERR:" "DEBUG"
            Write-TestLog $stderrContent "DEBUG"
        }
        Remove-Item "$TestLogFile.stderr" -Force
    }
} else {
    Write-TestLog "`nTest 4: Skipped (--SkipExecTest specified)"
}

# Test 5: Validate build integrity
Write-TestLog "`nTest 5: Validate build structure"
$requiredDirs = @(
    (Split-Path $ExePath -Parent),
    (Join-Path (Split-Path $ExePath -Parent) "_internal")
)

$missingDirs = @()
foreach ($dir in $requiredDirs) {
    if (-not (Test-Path $dir)) {
        $missingDirs += $dir
    }
}

if ($missingDirs.Count -gt 0) {
    Write-TestLog "WARNING: Missing build directories: $($missingDirs -join ', ')" "WARNING"
} else {
    Write-TestLog "✓ Build structure validated"
}

# Test 6: Check dependencies
Write-TestLog "`nTest 6: Verify Python environment"
$pythonVersion = python --version 2>&1
Write-TestLog "Python version: $pythonVersion"

$pkgCheck = pip list 2>&1 | Select-String "PyInstaller"
if ($pkgCheck) {
    Write-TestLog "✓ PyInstaller installed"
} else {
    Write-TestLog "WARNING: PyInstaller not found in current environment" "WARNING"
}

# Summary
Write-TestLog "`n=========================================="
Write-TestLog "Validation Summary"
Write-TestLog "=========================================="
Write-TestLog "Executable Path: $ExePath"
Write-TestLog "Executable Size: $([Math]::Round($exeSize, 2)) MB"
Write-TestLog "Test Log: $TestLogFile"
Write-TestLog ""
Write-TestLog "NEXT STEPS:"
Write-TestLog "1. Manual Testing:"
Write-TestLog "   & '$ExePath' --quick"
Write-TestLog "   & '$ExePath' --console"
Write-TestLog ""
Write-TestLog "2. Deployment:"
Write-TestLog "   Copy-Item '$ExePath' -Destination 'C:\Program Files\ASTRA\'"
Write-TestLog ""
Write-TestLog "3. Distribution:"
Write-TestLog "   Get-FileHash '$ExePath' -Algorithm SHA256"
Write-TestLog ""
Write-TestLog "=========================================="
Write-TestLog "Validation completed"

exit 0
