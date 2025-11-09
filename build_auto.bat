@echo off
REM ASTRA OS - Quick Build (No Pause)
title ASTRA OS - Building...

echo.
echo ============================================================
echo   ASTRA OS - Executable Builder
echo ============================================================
echo.

echo [1/3] Cleaning previous builds...
if exist "dist" rmdir /s /q "dist" 2>nul
if exist "build" rmdir /s /q "build" 2>nul
if exist "ASTRA_OS.spec" del /q "ASTRA_OS.spec" 2>nul

echo [2/3] Building executable (this may take 2-5 minutes)...
echo.

.\.venv\Scripts\python.exe -m PyInstaller ^
    --name=ASTRA_OS ^
    --onefile ^
    --console ^
    --add-data="app/static;app/static" ^
    --hidden-import=uvicorn.logging ^
    --hidden-import=uvicorn.loops.auto ^
    --hidden-import=uvicorn.protocols.http.auto ^
    --hidden-import=uvicorn.protocols.websockets.auto ^
    --hidden-import=uvicorn.lifespan.on ^
    --hidden-import=src.astra.core.identity.astra_roles ^
    --hidden-import=src.astra.core.identity.role_context ^
    --hidden-import=src.astra.core.identity.memory_tags ^
    --hidden-import=src.astra.core.functions.registry ^
    --hidden-import=src.astra.core.functions.simple_registry ^
    --hidden-import=src.astra.core.functions.modules_v2 ^
    --hidden-import=app.main ^
    --hidden-import=app.identity_state ^
    --hidden-import=app.models ^
    --hidden-import=app.traces ^
    --hidden-import=boot ^
    --exclude-module=matplotlib ^
    --exclude-module=numpy ^
    --exclude-module=pandas ^
    --exclude-module=scipy ^
    --noconfirm ^
    launch_server.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    echo.
    exit /b 1
)

echo.
echo [3/3] Creating launcher...

echo @echo off > dist\Launch_ASTRA.bat
echo title ASTRA OS >> dist\Launch_ASTRA.bat
echo echo. >> dist\Launch_ASTRA.bat
echo echo Starting ASTRA OS... >> dist\Launch_ASTRA.bat
echo echo Dashboard: http://localhost:8787 >> dist\Launch_ASTRA.bat
echo echo. >> dist\Launch_ASTRA.bat
echo "%%~dp0ASTRA_OS.exe" >> dist\Launch_ASTRA.bat

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
