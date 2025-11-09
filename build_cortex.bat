@echo off
REM ASTRA Cortex - One-Click Build Script
REM ======================================

echo.
echo ============================================
echo  ASTRA CORTEX - Cython Build System
echo ============================================
echo.

REM Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found in PATH
    echo Please install Python 3.9+ and add it to PATH
    exit /b 1
)

echo [1/5] Checking dependencies...
python -c "import numpy; import setuptools; import wheel" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing required packages...
    python -m pip install --upgrade pip setuptools wheel numpy
)

python -c "import Cython" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Installing Cython...
    python -m pip install cython>=3.0
)

echo [2/5] Cleaning previous builds...
if exist "build\" rd /s /q "build"
if exist "astra_core\cortex\*.c" del /q "astra_core\cortex\*.c"
if exist "astra_core\cortex\*.pyd" del /q "astra_core\cortex\*.pyd"
if exist "astra_core\cortex\*.so" del /q "astra_core\cortex\*.so"

echo [3/5] Building Cython extensions...
python setup_cortex.py build_ext --inplace
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Build failed!
    echo.
    echo Common issues:
    echo   - Missing Microsoft C++ Build Tools
    echo     Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo   - OpenMP not available
    echo     Build will still work but without parallelization
    exit /b 1
)

echo [4/5] Verifying build...
python -c "from astra_core.cortex import CORTEX_AVAILABLE; assert CORTEX_AVAILABLE, 'Import failed'" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Cython extensions built but import failed
    echo This may indicate a dependency issue
) else (
    echo [SUCCESS] Cython extensions ready!
)

echo [5/5] Generating performance reports...
if exist "astra_core\cortex\*.html" (
    echo HTML annotation files generated in astra_core\cortex\
    echo Open them in browser to see performance analysis
)

echo.
echo ============================================
echo  BUILD COMPLETE!
echo ============================================
echo.
echo Next steps:
echo   1. Run tests:    pytest tests\cortex\ -v
echo   2. Quick test:   python -c "from astra_core.cortex import cosine; print('OK')"
echo   3. See README_CORTEX.md for integration guide
echo.

pause
