@echo off
title ASTRA Desktop Launcher
color 0A

echo.
echo ================================================
echo           ASTRA Desktop Launcher
echo ================================================
echo.

:: Check if backend is running
echo [1/3] Checking backend status...
powershell -Command "$response = try { Invoke-WebRequest -Uri 'http://127.0.0.1:8080/health' -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop; $true } catch { $false }; if ($response) { Write-Host '      Backend is already running' -ForegroundColor Green } else { Write-Host '      Backend is not running, starting...' -ForegroundColor Yellow; exit 1 }"

if %errorlevel% neq 0 (
    echo.
    echo [2/3] Starting ASTRA backend...
    start "ASTRA Backend" /MIN powershell -NoProfile -ExecutionPolicy Bypass -Command "cd X:\PROJECT_ASTRA\astra-local; & .venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8080"
    
    :: Wait for backend to start
    echo       Waiting for backend to initialize...
    timeout /t 5 /nobreak >nul
    
    :checkbackend
    powershell -Command "$response = try { Invoke-WebRequest -Uri 'http://127.0.0.1:8080/health' -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop; $true } catch { $false }; if (-not $response) { exit 1 }"
    if %errorlevel% neq 0 (
        timeout /t 2 /nobreak >nul
        goto checkbackend
    )
    echo       Backend started successfully!
) else (
    echo [2/3] Backend already running - skipping startup
)

echo.
echo [3/3] Launching ASTRA Desktop...
cd X:\PROJECT_ASTRA\astra-local\desktop_app
start "ASTRA Desktop" pythonw.exe main.py

echo.
echo ================================================
echo   ASTRA Desktop launched successfully!
echo ================================================
echo.
echo - Backend running at: http://127.0.0.1:8080
echo - Desktop app is now open
echo - You can close this window
echo.
pause
