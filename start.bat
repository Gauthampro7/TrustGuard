@echo off
setlocal enabledelayedexpansion
title TrustGuard Platform Launcher

echo ======================================================================
echo           TRUSTGUARD : DEFENSE-IN-DEPTH DEEPFAKE FORENSICS
echo ======================================================================
echo.
echo [*] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python is not found on PATH. Please install Python 3.10+ to run TrustGuard.
    pause
    exit /b 1
)

echo [*] Running TrustGuard System Diagnostics...
python scripts/diagnostics.py
if %errorlevel% neq 0 (
    echo [!] System diagnostics reported warnings or failures.
)

echo [*] Launching TrustGuard in default browser...
start "" "http://127.0.0.1:8000/"

echo [*] Starting FastAPI ASGI Server on http://127.0.0.1:8000 ...
echo [*] Press Ctrl+C in this console window to stop the server anytime.
echo.
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
