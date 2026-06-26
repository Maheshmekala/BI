@echo off
title Instant BI
echo ============================================
echo        📊 Instant BI — Chat with your data
echo ============================================
echo.

:: Check if virtual env exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment activated
) else (
    echo [..] Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment created
)

:: Install/update dependencies
echo [..] Installing dependencies...
pip install -r requirements.txt -q
echo [OK] Dependencies installed

:: Create uploads directory
if not exist "uploads" mkdir uploads

:: Launch the app
echo.
echo [OK] Starting Instant BI...
echo      Open http://localhost:8501 in your browser
echo.
streamlit run app.py --server.port 8501 --server.headless true

pause
