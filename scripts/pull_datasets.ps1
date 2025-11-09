$ErrorActionPreference = "Stop"

# Activate venv
& .\.venv\Scripts\Activate.ps1

# OPTIONAL: Temporarily relax outbound block if your privacy layer is strict
# $env:ASTRA_ALLOW_NETWORK = "1"

# Pull / save datasets
python tools\bootstrap_datasets.py

# Verify
python scripts\verify_downloads.py
Write-Host "`n[ASTRA] Done. Datasets cached in ./data and ./cache."
