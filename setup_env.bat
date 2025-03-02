@echo off
echo Setting up virtual environment for Hairstyle Analyzer...

:: Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python is not installed or not in PATH. Please install Python 3.9 or higher.
    exit /b 1
)

:: Create virtual environment
echo Creating virtual environment...
python -m venv venv
if %ERRORLEVEL% neq 0 (
    echo Failed to create virtual environment.
    exit /b 1
)

:: Activate virtual environment and install requirements
echo Activating virtual environment and installing dependencies...
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .

echo Virtual environment setup complete.
echo To activate the environment, run: venv\Scripts\activate
