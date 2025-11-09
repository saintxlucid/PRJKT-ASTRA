@echo off
echo LLM GGUF Reverse Engineering Toolkit - Test Script
echo =================================================

echo Testing Python availability...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

echo Testing toolkit imports...
python test_toolkit.py
if %errorlevel% neq 0 (
    echo Error: Toolkit import test failed.
    pause
    exit /b 1
)

echo.
echo Toolkit is ready for use!
echo Refer to the documentation for detailed usage instructions.
echo.
pause