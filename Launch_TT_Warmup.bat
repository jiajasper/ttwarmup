@echo off
cd /d "%~dp0"

REM Check if pip is available
python -m pip --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo pip not found, installing pip...
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python get-pip.py --user
    del get-pip.py
)

REM Install dependencies
python -m pip install --user -r requirements.txt

REM Run the main script
python main.py

pause 