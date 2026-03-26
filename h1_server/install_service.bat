@echo off
:: H1 Heavy Server — Install Windows Scheduled Tasks
:: Run as Administrator

echo ============================================================
echo  H1 Heavy Server — Service Installation
echo ============================================================

set H1_DIR=C:\H1_Server
set PYTHON=C:\Python\python.exe

:: Check Python
if not exist "%PYTHON%" (
    echo ERROR: Python not found at %PYTHON%
    echo Please install Python 3.10+ to C:\Python\
    pause
    exit /b 1
)

:: Install Python dependencies
echo [1] Installing Python dependencies...
%PYTHON% -m pip install -r "%H1_DIR%\requirements.txt"

:: Create logs directory
if not exist "%H1_DIR%\logs" mkdir "%H1_DIR%\logs"

:: Install NATS Server as scheduled task
echo [2] Installing H1_NATS task...
schtasks /create /tn "H1_NATS" /tr "\"%H1_DIR%\nats-server.exe\" -c \"%H1_DIR%\nats-server.conf\"" /sc onstart /ru SYSTEM /f
if %errorlevel% neq 0 echo WARNING: Could not create H1_NATS task (may need admin rights)

:: Install Orchestrator as scheduled task
echo [3] Installing H1_Orchestrator task...
schtasks /create /tn "H1_Orchestrator" /tr "\"%PYTHON%\" \"%H1_DIR%\orchestrator.py\"" /sc onstart /ru SYSTEM /f
if %errorlevel% neq 0 echo WARNING: Could not create H1_Orchestrator task

:: Install Security Monitor as scheduled task
echo [4] Installing H1_SecurityMonitor task...
schtasks /create /tn "H1_SecurityMonitor" /tr "\"%PYTHON%\" \"%H1_DIR%\security_monitor.py\"" /sc onstart /ru SYSTEM /f
if %errorlevel% neq 0 echo WARNING: Could not create H1_SecurityMonitor task

:: Start services
echo [5] Starting services...
schtasks /run /tn "H1_NATS"
timeout /t 3 /nobreak >nul
schtasks /run /tn "H1_Orchestrator"
schtasks /run /tn "H1_SecurityMonitor"

echo ============================================================
echo  Installation complete!
echo  Check status: schtasks /query /tn "H1_NATS"
echo ============================================================
pause
