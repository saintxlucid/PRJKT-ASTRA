@echo off
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   ASTRA OS - Development Mode
echo ========================================
echo.

:: Check if Node.js is installed
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed!
    echo Please install Node.js from: https://nodejs.org/
    pause
    exit /b 1
)

:: Check if npm is installed
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] npm is not installed!
    pause
    exit /b 1
)

echo [INFO] Node.js and npm found
node --version
npm --version
echo.

:: Check if node_modules exists
if not exist "node_modules\" (
    echo [SETUP] Installing dependencies...
    echo This may take a few minutes on first run...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
    echo [SUCCESS] Dependencies installed
    echo.
) else (
    echo [INFO] Dependencies already installed
    echo.
)

:: Check for icon (warning only)
if not exist "electron\icon.ico" (
    echo [WARNING] No icon.ico found in electron/ folder
    echo The app will use the default Electron icon.
    echo See electron\ICON_README.md for instructions.
    echo.
)

echo [STARTING] Launching development mode...
echo.
echo - Vite dev server will start on http://localhost:5173
echo - Electron window will open automatically
echo - Hot reload is enabled (changes appear instantly)
echo - DevTools will be open for debugging
echo.
echo Press Ctrl+C in this window to stop the dev server
echo.
call npm run dev
