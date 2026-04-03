@echo off
SETLOCAL

echo ==========================================
echo Checking for Python 3.13...
echo ==========================================

python --version 2>nul | findstr "3.13" >nul
IF %ERRORLEVEL% NEQ 0 (
    echo Python 3.13 not found. Installing...
    winget install -e --id Python.Python.3.13
    echo Please restart this script after installation completes.
    pause
    exit /b
)

echo ==========================================
echo Creating virtual environment (aiagent)...
echo ==========================================

python -m venv aiagent

echo ==========================================
echo Activating virtual environment...
echo ==========================================

call aiagent\Scripts\activate

echo ==========================================
echo Upgrading pip...
echo ==========================================

python -m pip install --upgrade pip

echo ==========================================
echo Installing dependencies...
echo ==========================================

pip install -r requirements.txt

echo ==========================================
echo Setup Complete!
echo ==========================================

pause