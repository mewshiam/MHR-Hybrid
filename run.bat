@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM -------- MHR-Hybrid launcher (Windows) --------
REM Modes:
REM   backend   (default)
REM   ui
REM   both

set "VENV_DIR=.venv"
set "PY="
set "MODE=backend"
set "EXTRA_ARGS="
set "UI_ARGS="
set "CONFIG_PATH=config.json"
set "TARGET_HOST=127.0.0.1"
set "TARGET_PORT=8080"
set "TARGET_LOG_LEVEL=INFO"
set "USER_SET_HOST="
set "USER_SET_PORT="
set "USER_SET_LOG_LEVEL="
set "USER_SET_CONFIG="

where python >nul 2>&1
if !errorlevel!==0 (
    set "PY=python"
) else (
    where py >nul 2>&1
    if !errorlevel!==0 (
        set "PY=py -3"
    )
)

if "%PY%"=="" (
    echo [X] Python 3.10+ was not found on PATH.
    echo     Install from https://www.python.org/downloads/ and rerun this script.
    exit /b 1
)

:parse_args
if "%~1"=="" goto after_parse

if /I "%~1"=="--ui" (
    set "MODE=ui"
    shift
    goto parse_args
)
if /I "%~1"=="--backend" (
    set "MODE=backend"
    shift
    goto parse_args
)
if /I "%~1"=="--both" (
    set "MODE=both"
    shift
    goto parse_args
)
if /I "%~1"=="--mode" (
    if "%~2"=="" (
        echo [X] Missing value for --mode ^(backend^|ui^|both^).
        exit /b 1
    )
    if /I "%~2"=="backend" set "MODE=backend"
    if /I "%~2"=="ui" set "MODE=ui"
    if /I "%~2"=="both" set "MODE=both"
    shift
    shift
    goto parse_args
)

if /I "%~1"=="--host" (
    if "%~2"=="" (
        echo [X] Missing value for --host.
        exit /b 1
    )
    set "TARGET_HOST=%~2"
    set "USER_SET_HOST=1"
    set "EXTRA_ARGS=!EXTRA_ARGS! --host "%~2""
    set "UI_ARGS=!UI_ARGS! --host "%~2""
    shift
    shift
    goto parse_args
)
if /I "%~1"=="--port" (
    if "%~2"=="" (
        echo [X] Missing value for --port.
        exit /b 1
    )
    set "TARGET_PORT=%~2"
    set "USER_SET_PORT=1"
    set "EXTRA_ARGS=!EXTRA_ARGS! --port %~2"
    set "UI_ARGS=!UI_ARGS! --port %~2"
    shift
    shift
    goto parse_args
)
if /I "%~1"=="--log-level" (
    if "%~2"=="" (
        echo [X] Missing value for --log-level.
        exit /b 1
    )
    set "TARGET_LOG_LEVEL=%~2"
    set "USER_SET_LOG_LEVEL=1"
    set "EXTRA_ARGS=!EXTRA_ARGS! --log-level %~2"
    shift
    shift
    goto parse_args
)
if /I "%~1"=="--config" (
    if "%~2"=="" (
        echo [X] Missing value for --config.
        exit /b 1
    )
    set "CONFIG_PATH=%~2"
    set "USER_SET_CONFIG=1"
    set "EXTRA_ARGS=!EXTRA_ARGS! --config "%~2""
    shift
    shift
    goto parse_args
)
if /I "%~1"=="-c" (
    if "%~2"=="" (
        echo [X] Missing value for -c.
        exit /b 1
    )
    set "CONFIG_PATH=%~2"
    set "USER_SET_CONFIG=1"
    set "EXTRA_ARGS=!EXTRA_ARGS! -c "%~2""
    shift
    shift
    goto parse_args
)

set "EXTRA_ARGS=!EXTRA_ARGS! "%~1""
shift
goto parse_args

:after_parse
if /I not "%MODE%"=="backend" if /I not "%MODE%"=="ui" if /I not "%MODE%"=="both" (
    echo [X] Invalid mode "%MODE%". Use backend, ui, or both.
    exit /b 1
)

if "%~1"=="" if /I "%MODE%"=="backend" (
    set /p MODE_CHOICE="Select launch mode [B]ackend / [U]I / [A]ll (default B): "
    if /I "!MODE_CHOICE!"=="U" set "MODE=ui"
    if /I "!MODE_CHOICE!"=="A" set "MODE=both"
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [*] Creating virtual environment in %VENV_DIR% ...
    %PY% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [X] Failed to create virtual environment.
        exit /b 1
    )
)

set "VPY=%VENV_DIR%\Scripts\python.exe"

echo [*] Installing dependencies ...
"%VPY%" -m pip install --disable-pip-version-check -q --upgrade pip >nul
"%VPY%" -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
    echo [X] Could not install dependencies.
    echo     Friendly tip: check internet access and Python build tools, then rerun.
    exit /b 1
)

if not exist "%CONFIG_PATH%" (
    echo [X] Config file not found: "%CONFIG_PATH%"
    echo     Guided fix:
    echo       1^) Copy config.example.json to config.json
    echo       2^) Fill in required values like auth_key and relay settings
    echo       3^) Rerun: run.bat --config "config.json"
    exit /b 1
)

echo.
echo ================================================
echo   MHR-Hybrid Startup
echo -----------------------------------------------
echo   Active mode    : %MODE%
echo   Target host    : %TARGET_HOST%
echo   Target port    : %TARGET_PORT%
echo   Config file    : %CONFIG_PATH%
echo ================================================
echo.

if /I "%MODE%"=="ui" (
    echo [Hint] Starting desktop UI only. Ensure backend is already running.
    "%VPY%" -m desktop_ui.main %UI_ARGS%
    set "RC=%errorlevel%"
    if not "%RC%"=="0" (
        echo [X] UI failed to start. Common causes: missing PyQt5 dependency.
    )
    exit /b %RC%
)

if /I "%MODE%"=="both" (
    echo [Hint] Starting backend in a new window, then opening desktop UI.
    start "MHR-Hybrid Backend" cmd /c "cd /d "%cd%" && "%VPY%" main.py %EXTRA_ARGS%"
    if errorlevel 1 (
        echo [X] Failed to start backend window.
        exit /b 1
    )
    timeout /t 2 >nul
    "%VPY%" -m desktop_ui.main %UI_ARGS%
    set "RC=%errorlevel%"
    if not "%RC%"=="0" (
        echo [X] UI failed to start. Common causes: missing PyQt5 dependency.
        exit /b %RC%
    )
    exit /b 0
)

echo [Hint] Starting backend only. Open another terminal and run run.bat --ui for dashboard.
"%VPY%" main.py %EXTRA_ARGS%
set "RC=%errorlevel%"
if not "%RC%"=="0" (
    echo [X] Backend startup failed.
    echo     Common causes: invalid config.json, occupied port, missing deps.
)
exit /b %RC%
