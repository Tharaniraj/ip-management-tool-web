@echo off
REM IP Management Tool - Web Edition Launcher
REM Auto-installs Flask, creates venv, opens browser, starts server.

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   IP MANAGEMENT TOOL  v1.0.0  (Web Edition)
echo ============================================================
echo.

cd /d "%~dp0"

REM ── Python check ─────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo  Install Python 3.8+ from https://www.python.org/
    echo  Tick "Add Python to PATH" during installation.
    echo.
    pause & exit /b 1
)
echo [OK] Python found
python --version

REM ── Create virtual environment ────────────────────────────────
if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo [*] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 ( echo [ERROR] venv creation failed. & pause & exit /b 1 )
    echo [OK] Virtual environment created
)

call .venv\Scripts\activate.bat

REM ── Install dependencies ──────────────────────────────────────
echo.
echo [*] Installing dependencies...
pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 ( echo [ERROR] pip install failed. & pause & exit /b 1 )
echo [OK] Flask ready

REM ── Directories ───────────────────────────────────────────────
if not exist "data"         mkdir data
if not exist "data\backups" mkdir data\backups
if not exist "logs"         mkdir logs

REM ── Open browser after delay ──────────────────────────────────
start "" /b cmd /c "timeout /t 3 >nul && start http://localhost:5000"

REM ── Start server ──────────────────────────────────────────────
echo [*] Starting web server at http://localhost:5000
echo     Press Ctrl+C to stop
echo.
python app.py

echo.
if errorlevel 1 (
    echo [ERROR] Server exited with an error. Check logs\app.log
)
pause
