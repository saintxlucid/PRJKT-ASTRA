$ErrorActionPreference = "Stop"

# Create venv
if (!(Test-Path -Path ".venv")) {
  python -m venv .venv
}
# Activate
& .\.venv\Scripts\Activate.ps1

# Upgrade pip + install deps
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "`n[ASTRA] Virtual env ready."
