$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Banner($t){ Write-Host "`n=== $t ===" -ForegroundColor Cyan }

Banner "Test"

$required = @(
  "ASTRA_BRIDGE_ENABLED=true",
  "ASTRA_BRIDGE_INTERPRET_CONF_THRESHOLD=0.65"
)

Write-Host "Required count: $($required.Count)"

foreach($line in $required){
  Write-Host "Line: $line"
}

Write-Host "Done"
