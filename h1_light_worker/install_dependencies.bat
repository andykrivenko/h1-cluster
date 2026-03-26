@echo off
:: H1 Light Worker — Install Dependencies
:: Run as Administrator

echo ============================================================
echo  H1 Light Worker — Dependencies Installation
echo ============================================================

set H1_DIR=C:\H1_Node
set PYTHON=C:\Python\python.exe

if not exist "%PYTHON%" (
    echo ERROR: Python not found at %PYTHON%
    echo Please install Python 3.10+ to C:\Python\
    pause
    exit /b 1
)

:: Create directories
if not exist "%H1_DIR%" mkdir "%H1_DIR%"
if not exist "%H1_DIR%\logs" mkdir "%H1_DIR%\logs"

:: Install Python dependencies
echo [1] Installing Python dependencies...
%PYTHON% -m pip install -r "%H1_DIR%\requirements.txt"

:: Install Playwright browsers
echo [2] Installing Playwright browsers...
%PYTHON% -m playwright install chromium

echo ============================================================
echo  Dependencies installed successfully!
echo ============================================================
pause
