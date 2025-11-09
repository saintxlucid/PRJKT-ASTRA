Write-Host "Running ASTRA OS P1 smoke..."
python -m pytest -q
if ($LASTEXITCODE -ne 0) { Write-Error "Tests failed."; exit 1 }
python demo\demo_dayflow.py
