@echo off
:: H1 Light Worker — Install Windows Scheduled Task
:: Run as Administrator

echo ============================================================
echo  H1 Light Worker — Service Installation
echo ============================================================

set H1_DIR=C:\H1_Node
set PYTHON=C:\Python\python.exe

if not exist "%PYTHON%" (
    echo ERROR: Python not found at %PYTHON%
    pause
    exit /b 1
)

:: Install H1_Worker scheduled task
echo [1] Installing H1_Worker task...
schtasks /create /tn "H1_Worker" /tr "\"%PYTHON%\" \"%H1_DIR%\worker_playwright.py\"" /sc onstart /ru SYSTEM /f
if %errorlevel% neq 0 (
    echo WARNING: Could not create H1_Worker task (may need admin rights)
) else (
    echo H1_Worker task created successfully
)

:: Start worker
echo [2] Starting H1_Worker...
schtasks /run /tn "H1_Worker"

echo ============================================================
echo  Installation complete!
echo  Check status: schtasks /query /tn "H1_Worker"
echo  Check logs:   type %H1_DIR%\logs\worker.log
echo ============================================================
pause
