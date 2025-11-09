@echo off
title ASTRA OS - Building Executable...

echo.
echo ============================================================
echo   ASTRA OS - Executable Builder
echo ============================================================
echo.
echo This will create a standalone ASTRA_OS.exe file
echo.
echo Estimated time: 2-5 minutes
echo Estimated size: 50-100 MB
echo.
pause

echo.
echo [1/3] Cleaning previous builds...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "astra_os.spec" del /q "astra_os.spec"

echo [2/3] Building executable with PyInstaller...
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
    launch_server.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    echo Check the output above for details
    echo.
    pause
    exit /b 1
)

echo.
echo [3/3] Creating distribution package...

REM Create launch script
echo @echo off > dist\Launch_ASTRA.bat
echo title ASTRA OS - Server Starting... >> dist\Launch_ASTRA.bat
echo. >> dist\Launch_ASTRA.bat
echo echo. >> dist\Launch_ASTRA.bat
echo echo ======================================== >> dist\Launch_ASTRA.bat
echo echo   ASTRA OS - Celestial Intelligence >> dist\Launch_ASTRA.bat
echo echo ======================================== >> dist\Launch_ASTRA.bat
echo echo. >> dist\Launch_ASTRA.bat
echo echo Starting server on http://localhost:8000... >> dist\Launch_ASTRA.bat
echo echo Dashboard: http://localhost:8787... >> dist\Launch_ASTRA.bat
echo echo. >> dist\Launch_ASTRA.bat
echo. >> dist\Launch_ASTRA.bat
echo "%%~dp0ASTRA_OS.exe" >> dist\Launch_ASTRA.bat
echo. >> dist\Launch_ASTRA.bat
echo if errorlevel 1 ( >> dist\Launch_ASTRA.bat
echo     echo. >> dist\Launch_ASTRA.bat
echo     echo [ERROR] Server crashed or failed to start >> dist\Launch_ASTRA.bat
echo     echo Check the logs above for details >> dist\Launch_ASTRA.bat
echo     echo. >> dist\Launch_ASTRA.bat
echo     pause >> dist\Launch_ASTRA.bat
echo ) >> dist\Launch_ASTRA.bat

REM Copy documentation
if exist "🚀_60_SECOND_LAUNCH.md" copy "🚀_60_SECOND_LAUNCH.md" "dist\" >nul
if exist "✅_API_DASHBOARD_INTEGRATED.md" copy "✅_API_DASHBOARD_INTEGRATED.md" "dist\" >nul
if exist "README.md" copy "README.md" "dist\" >nul

echo.
echo ============================================================
echo   BUILD COMPLETE!
echo ============================================================
echo.
echo Executable location: dist\ASTRA_OS.exe
echo Launcher script:      dist\Launch_ASTRA.bat
echo.
echo To run ASTRA OS:
echo   1. Navigate to the dist\ folder
echo   2. Double-click Launch_ASTRA.bat
echo   3. Open browser to http://localhost:8000
echo.
echo Package size:
dir "dist\ASTRA_OS.exe" | findstr "ASTRA_OS.exe"
echo.
pause
