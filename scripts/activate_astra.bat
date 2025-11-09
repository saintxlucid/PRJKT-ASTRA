@echo off
REM ASTRA Environment Activation Script (Windows Batch)
REM This script activates the local Python virtual environment
REM Usage: scripts\activate_astra.bat

echo ================================================
echo    ASTRA - AI Assistant System
echo    Activating Local Environment...
echo ================================================
echo.

cd /d "X:\PROJECT_ASTRA"

REM Activate Python virtual environment
call ".venv\Scripts\activate.bat"

REM Set Python path
set PYTHONPATH=X:\PROJECT_ASTRA\src;X:\PROJECT_ASTRA

echo.
echo ================================================
echo    Environment Ready!
echo ================================================
echo.
echo Available Commands:
echo   poetry run python run_server.py  - Start ASTRA server
echo   poetry run pytest                 - Run tests
echo   poetry show                       - Show installed packages
echo.
