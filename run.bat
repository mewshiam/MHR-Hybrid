@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo [X] python is not installed or not on PATH.
    exit /b 1
)

if not exist "config.json" (
    echo [X] Missing required file: config.json
    echo     Hint: copy config.example.json config.json
    exit /b 1
)

python -c "import src.app" >nul 2>&1
if errorlevel 1 (
    echo [*] Installing dependencies from requirements.txt ...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [X] Dependency install failed. Install manually: python -m pip install -r requirements.txt
        exit /b 1
    )
)

python bootstrap.py %*
exit /b %errorlevel%
