@echo off
echo.
echo ============================================================
echo   ASTRA OS - Minimal Executable Builder
echo   (Excludes ML libraries for faster build)
echo ============================================================
echo.

REM Clean previous builds
echo [1/3] Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist ASTRA_OS.spec del /q ASTRA_OS.spec

REM Build executable with minimal dependencies
echo [2/3] Building executable (optimized, 1-2 minutes)...
.\.venv\Scripts\python.exe -m PyInstaller ^
    --name=ASTRA_OS ^
    --onefile ^
    --console ^
    --add-data="app/static;app/static" ^
    --hidden-import=uvicorn.logging ^
    --hidden-import=uvicorn.loops.auto ^
    --hidden-import=uvicorn.protocols.http.auto ^
    --hidden-import=src.astra.core.identity.astra_roles ^
    --hidden-import=src.astra.core.functions.modules_v2 ^
    --hidden-import=src.astra.core.functions.simple_registry ^
    --hidden-import=src.astra.core.boot.astra_os ^
    --hidden-import=fastapi ^
    --hidden-import=pydantic ^
    --hidden-import=starlette ^
    --hidden-import=httpx ^
    --hidden-import=anyio ^
    --hidden-import=sniffio ^
    --exclude-module=torch ^
    --exclude-module=sklearn ^
    --exclude-module=transformers ^
    --exclude-module=datasets ^
    --exclude-module=spacy ^
    --exclude-module=thinc ^
    --exclude-module=PIL ^
    --exclude-module=matplotlib ^
    --exclude-module=numpy ^
    --exclude-module=pandas ^
    --exclude-module=scipy ^
    --exclude-module=pytest ^
    --exclude-module=tensorboard ^
    --exclude-module=onnxruntime ^
    --exclude-module=tensorflow ^
    --noconfirm ^
    launch_server.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    exit /b 1
)

REM Create launcher script
echo [3/3] Creating launcher...
(
echo @echo off
echo echo Starting ASTRA OS...
echo ASTRA_OS.exe
echo if errorlevel 1 ^(
echo     echo.
echo     echo [ERROR] ASTRA OS failed to start!
echo     echo Check the error messages above.
echo     echo.
echo     pause
echo     exit /b 1
echo ^)
) > dist\Launch_ASTRA.bat

echo.
echo ============================================================
echo   BUILD COMPLETE!
echo ============================================================
echo.
echo   Location: dist\ASTRA_OS.exe
echo   Launcher: dist\Launch_ASTRA.bat
echo.
echo To run: cd dist; .\Launch_ASTRA.bat
echo.
