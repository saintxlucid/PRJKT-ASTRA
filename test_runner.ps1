# ASTRA Test Runner
# Created: October 16, 2025

param(
    [switch]$Coverage,
    [switch]$Parallel,
    [string]$TestPath = "tests",
    [string]$ReportDir = "test_reports"
)

# Ensure report directory exists
New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null

# Base pytest arguments
$pytestArgs = @(
    $TestPath,
    "--verbose",
    "--log-cli-level=INFO",
    "--import-mode=importlib"
)

# Add coverage if requested
if ($Coverage) {
    $pytestArgs += @(
        "--cov=astra",
        "--cov-report=html:$ReportDir/coverage",
        "--cov-report=term-missing"
    )
}

# Add parallel execution if requested
if ($Parallel) {
    $pytestArgs += "-n auto"
}

# Add JUnit report
$pytestArgs += "--junitxml=$ReportDir/test_results.xml"

# Run tests
Write-Host "Running ASTRA test suite..."
Write-Host "Configuration:"
Write-Host "  Coverage: $Coverage"
Write-Host "  Parallel: $Parallel"
Write-Host "  Test Path: $TestPath"
Write-Host "  Report Directory: $ReportDir"
Write-Host ""

try {
    & pytest $pytestArgs

    if ($Coverage) {
        Write-Host "`nCoverage report generated in $ReportDir/coverage"
    }
    Write-Host "Test results saved to $ReportDir/test_results.xml"
}
catch {
    Write-Error "Test execution failed: $_"
    exit 1
}