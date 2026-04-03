@echo off

echo ==========================================
echo Checking for Python 3.13 or higher...
echo ==========================================

:: Get Python version
for /f "tokens=2 delims= " %%i in ('python --version 2^>nul') do set PYVER=%%i

:: Extract major and minor version
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do (
    set MAJOR=%%a
    set MINOR=%%b
)

:: Check if Python exists and version >= 3.13
if not defined PYVER (
    echo Python not found. Installing...
    winget install -e --id Python.Python.3.13
    timeout /t 10 >nul
) else (
    if %MAJOR% LSS 3 (
        echo Python version too low. Installing 3.13...
        winget install -e --id Python.Python.3.13
        timeout /t 10 >nul
    ) else if %MAJOR% EQU 3 if %MINOR% LSS 13 (
        echo Python version less than 3.13. Installing 3.13...
        winget install -e --id Python.Python.3.13
        timeout /t 10 >nul
    ) else (
        echo Python %PYVER% is valid.
    )
)

echo ==========================================
echo Creating virtual environment (aiagent)...
echo ==========================================

IF NOT EXIST aiagent (
    python -m venv aiagent
)

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

echo Opening shell in virtual environment...
cmd /k "call aiagent\Scripts\activate"