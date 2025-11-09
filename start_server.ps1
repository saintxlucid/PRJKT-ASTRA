$pythonPath = "X:/PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0 (ASTRA_CORE)/.venv/Scripts/python.exe"

Write-Host "Starting FastAPI server..."
Write-Host "Using Python from: $pythonPath"

try {
    # Activate virtual environment
    & "X:/PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0 (ASTRA_CORE)/.venv/Scripts/Activate.ps1"
    
    # Run the server
    & $pythonPath -c @"
import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get('/')
async def root():
    return {'message': 'Hello World'}

uvicorn.run(app, host='127.0.0.1', port=8088)
"@
} catch {
    Write-Error $_.Exception.Message
}