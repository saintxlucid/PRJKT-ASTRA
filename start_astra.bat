@echo off
REM ASTRA 3.0 Quick Start - Windows Batch
echo.
echo ======================================================================
echo   🌌 ASTRA 3.0 - Quick Start
echo ======================================================================
echo.

REM Set environment variables
set ASTRA_LLM_PROVIDER=ollama
set OLLAMA_BASE_URL=http://localhost:11434
set ASTRA_LLM_MODEL_NAME=qwen2.5:1.5b
set DATABASE_URL=postgresql://astra:astra@localhost:5432/astra
set REDIS_URL=redis://localhost:6379/0
set JWT_SECRET=dev-secret-key-change-in-production
set OPENAI_API_KEY=dummy
set PYTHONPATH=%CD%\src;%CD%

echo Configuration:
echo   • Model: %ASTRA_LLM_MODEL_NAME%
echo   • Provider: %ASTRA_LLM_PROVIDER%
echo   • Ollama: %OLLAMA_BASE_URL%
echo.
echo Starting ASTRA Master on port 8000...
echo ======================================================================
echo.

python astra_master.py

echo.
echo ======================================================================
echo   ASTRA stopped
echo ======================================================================
pause
