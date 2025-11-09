@echo off
setlocal enabledelayedexpansion

echo.
echo ========================================
echo   ASTRA OS - Desktop Build Script
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
    echo [STEP 1/4] Installing dependencies...
    echo This may take a few minutes on first run...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
    echo [SUCCESS] Dependencies installed
) else (
    echo [STEP 1/4] Dependencies already installed
)

echo.
echo [STEP 2/4] Building React UI with Vite...
call npm run build:ui
if %errorlevel% neq 0 (
    echo [ERROR] Failed to build UI
    pause
    exit /b 1
)
echo [SUCCESS] UI built successfully

echo.
echo [STEP 3/4] Compiling Electron TypeScript...
call npm run build:electron
if %errorlevel% neq 0 (
    echo [ERROR] Failed to compile Electron
    pause
    exit /b 1
)
echo [SUCCESS] Electron compiled successfully

echo.
echo [STEP 4/4] Creating Windows installer...
echo This will create a .exe installer in the dist/ folder
call npm run dist
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create installer
    pause
    exit /b 1
)

echo.
echo ========================================
echo   BUILD COMPLETE!
echo ========================================
echo.
echo Your installer is ready:
echo   dist\ASTRA OS Setup 1.0.0.exe
echo.
echo Double-click the installer to test!
echo.
pause
