@echo off
title Log Analyzer — Setup & Launch
color 0A
echo.
echo  ====================================================
echo   Local AI Security Log Analyzer — Setup Script
echo  ====================================================
echo.

REM ── Step 1: Check Ollama ──────────────────────────────────────────────────
where ollama >nul 2>&1
if %errorlevel% NEQ 0 (
    echo  [!] Ollama is NOT installed.
    echo.
    echo  Please download and install Ollama from:
    echo  https://ollama.com/download
    echo.
    echo  After installing, run this script again.
    echo.
    start https://ollama.com/download
    pause
    exit /b 1
)

echo  [OK] Ollama found.

REM ── Step 2: Start Ollama service ─────────────────────────────────────────
echo  [*] Starting Ollama service...
start "" ollama serve
timeout /t 3 /nobreak >nul

REM ── Step 3: Pull model if needed ─────────────────────────────────────────
echo  [*] Checking model qwen3.5:0.8b...
ollama list | findstr /i "qwen3.5" >nul 2>&1
if %errorlevel% NEQ 0 (
    echo  [*] Pulling qwen3.5:0.8b (brief-recommended model, ~600 MB)...
    ollama pull qwen3.5:0.8b
    if %errorlevel% NEQ 0 (
        echo  [!] Model pull failed. Check your internet connection.
        pause
        exit /b 1
    )
)
echo  [OK] Model ready.

REM ── Step 4: Install Python deps ───────────────────────────────────────────
echo  [*] Installing Python dependencies...
cd /d "%~dp0backend"
pip install -r requirements.txt -q
if %errorlevel% NEQ 0 (
    echo  [!] pip install failed. Make sure Python 3.9+ is installed.
    pause
    exit /b 1
)
echo  [OK] Dependencies installed.

REM ── Step 5: Start backend ─────────────────────────────────────────────────
echo  [*] Starting Flask backend on http://localhost:5000 ...
start "Log Analyzer Backend" python app.py
timeout /t 2 /nobreak >nul

REM ── Step 6: Open frontend ─────────────────────────────────────────────────
echo  [*] Opening frontend in browser...
start "" "%~dp0frontend\index.html"

echo.
echo  ====================================================
echo   App is running!
echo   Backend: http://localhost:5000
echo   Frontend: file:///%~dp0frontend/index.html
echo  ====================================================
echo.
echo  Press any key to close this window (server keeps running)
pause >nul

