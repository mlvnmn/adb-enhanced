@echo off
setlocal enabledelayedexpansion
title ADB Forensic Monitor - Starting...
color 0A

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║   Enhanced ADB Forensic Monitor                 ║
echo  ║   Unauthorized Mobile Device Detection Tool      ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python is not installed or not in PATH.
    echo Please install Python from https://www.python.org/
    pause
    exit /b
)

:: 2. Check Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Node.js is not installed or not in PATH.
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b
)

:: 3. Cleanup existing processes on ports 5000 (Backend) and 5173 (Frontend)
echo [*] Cleaning up old processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5000 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1
timeout /t 1 >nul

:: 4. Check for ADB
echo [*] Checking for ADB...
where adb >nul 2>&1
if %errorlevel% neq 0 (
    if not exist "backend\adb.exe" (
        if not exist "backend\platform-tools\adb.exe" (
            echo [!] ADB (Android Debug Bridge) not found.
            echo [!] Please place adb.exe in the 'backend' folder.
            echo [!] Or install it and add to PATH.
            pause
            :: We won't exit, maybe the user wants to see the dashboard anyway
        )
    )
)

:: 5. Setup Backend
echo [*] Checking Backend...
cd /d "%~dp0backend"
if not exist "venv" (
    echo [*] Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate
    echo [*] Installing backend dependencies...
    pip install -r requirements.txt
) else (
    if not exist "venv\Scripts\python.exe" (
        echo [!] Virtual environment seems broken. Re-creating...
        rmdir /s /q venv
        python -m venv venv
        call venv\Scripts\activate
        pip install -r requirements.txt
    )
)

echo [*] Starting Backend Server...
start /B "" "venv\Scripts\python.exe" app.py

:: 6. Setup Frontend
echo [*] Checking Frontend...
cd /d "%~dp0frontend"
if not exist "node_modules" (
    echo [*] Installing frontend dependencies (this may take a minute)...
    call npm install
)

echo [*] Starting Frontend Dashboard...
start /B "" cmd /c "npm run dev"

:: 7. Wait for services
echo [*] Waiting for services to initialize...
timeout /t 10 /nobreak >nul

:: 8. Open browser
echo [*] Opening Dashboard...
start http://localhost:5173

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║   Dashboard running at: http://localhost:5173    ║
echo  ║   Backend API running at: http://localhost:5000  ║
echo  ║                                                  ║
echo  ║   Connect your Android phone via USB             ║
echo  ║   Ensure USB Debugging is enabled on the phone   ║
echo  ║   Press Ctrl+C to stop                           ║
echo  ╚══════════════════════════════════════════════════╝
echo.
pause
