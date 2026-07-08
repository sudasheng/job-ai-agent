@echo off
setlocal enabledelayedexpansion

:: ============================================================
::  Job AI Agent - One-Click Deploy
:: ============================================================
::  Usage:
::    deploy.bat           normal deploy
::    deploy.bat dev       dev mode (hot-reload + dev deps)
::    deploy.bat skip      skip Docker MySQL
:: ============================================================

set DEV_MODE=0
set SKIP_DOCKER=0

if /i "%~1"=="dev"  set DEV_MODE=1
if /i "%~1"=="skip" set SKIP_DOCKER=1
if /i "%~2"=="dev"  set DEV_MODE=1
if /i "%~2"=="skip" set SKIP_DOCKER=1

set "PROJECT_ROOT=%~dp0"
set "VENV_PATH=%PROJECT_ROOT%.venv"
set "ENV_FILE=%PROJECT_ROOT%.env"
set "ENV_EXAMPLE=%PROJECT_ROOT%.env.example"

echo.
echo ============================================================
echo   Job AI Agent - One-Click Deploy
echo   %date% %time%
echo ============================================================
echo.

:: ============================================================
:: Step 1: Environment Check
:: ============================================================
echo [1/6] Checking environment...

where python >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Python not found. Please install Python 3.11+ and add to PATH
    echo   Download: https://www.python.org/downloads/
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo   [OK] %%i

if %SKIP_DOCKER%==1 goto :SKIP_DOCKER_CHECK

where docker >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Docker not found. Please install Docker Desktop
    echo   Download: https://www.docker.com/products/docker-desktop/
    echo   Tip: Use deploy.bat skip to bypass Docker
    exit /b 1
)
for /f "tokens=*" %%i in ('docker --version 2^>^&1') do echo   [OK] %%i

docker info >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Docker is not running. Please start Docker Desktop first
    exit /b 1
)

:SKIP_DOCKER_CHECK

:: ============================================================
:: Step 2: Virtual Environment + Dependencies
:: ============================================================
echo.
echo [2/6] Setting up Python virtual environment...

if exist "%VENV_PATH%" (
    echo   venv already exists: %VENV_PATH%
) else (
    python -m venv "%VENV_PATH%"
    echo   venv created: %VENV_PATH%
)

call "%VENV_PATH%\Scripts\activate.bat"
if errorlevel 1 (
    echo   [ERROR] Failed to activate venv
    exit /b 1
)
echo   venv activated

echo   Upgrading pip...
python -m pip install --upgrade pip -q

echo   Installing dependencies...
if %DEV_MODE%==1 (
    python -m pip install -e ".[dev]" -q
) else (
    python -m pip install -e . -q
)
echo   Dependencies installed

echo   Installing Playwright Chromium...
playwright install chromium >nul 2>&1
if errorlevel 1 (
    echo   [WARN] Playwright Chromium install failed. Run manually: playwright install chromium
) else (
    echo   Playwright Chromium installed
)

:: ============================================================
:: Step 3: .env Config
:: ============================================================
echo.
echo [3/6] Setting up .env config...

if exist "%ENV_FILE%" (
    echo   .env already exists, skipping
) else (
    if exist "%ENV_EXAMPLE%" (
        copy "%ENV_EXAMPLE%" "%ENV_FILE%" >nul
        echo   .env created from .env.example
        echo   [WARN] Please edit .env and fill in your API keys
        echo   [WARN] Required: DEEPSEEK_API_KEY, QWEN_API_KEY
    ) else (
        echo   [ERROR] .env.example not found
        exit /b 1
    )
)

:: ============================================================
:: Step 4: Start Docker MySQL
:: ============================================================
if %SKIP_DOCKER%==1 goto :SKIP_DOCKER

echo.
echo [4/6] Starting Docker MySQL...

docker ps -a --filter "name=job-ai-agent-mysql" --format "{{.Names}}" 2>nul | findstr /c:"job-ai-agent-mysql" >nul
if errorlevel 1 (
    echo   Creating and starting MySQL container...
    docker compose up -d mysql >nul 2>&1
    if errorlevel 1 (
        echo   [ERROR] Docker MySQL failed to start
        exit /b 1
    )
    echo   MySQL container created and started
) else (
    docker ps --filter "name=job-ai-agent-mysql" --format "{{.Names}}" 2>nul | findstr /c:"job-ai-agent-mysql" >nul
    if errorlevel 1 (
        echo   Starting existing MySQL container...
        docker start job-ai-agent-mysql >nul 2>&1
        echo   MySQL container started
    ) else (
        echo   MySQL container already running
    )
)

echo   Waiting for MySQL to be ready...
set /a RETRY=0
:WAIT_MYSQL
docker exec job-ai-agent-mysql mysqladmin ping -h localhost -u root -proot123456 >nul 2>&1
if not errorlevel 1 goto :MYSQL_READY
set /a RETRY+=1
if %RETRY% geq 30 goto :MYSQL_TIMEOUT
echo   Waiting... (%RETRY%/30)
timeout /t 2 /nobreak >nul
goto :WAIT_MYSQL

:MYSQL_TIMEOUT
echo   [WARN] MySQL health check timeout, container may still be initializing
echo   [WARN] If startup fails, wait a moment and retry
timeout /t 10 /nobreak >nul
goto :AFTER_MYSQL

:MYSQL_READY
echo   MySQL is ready

:AFTER_MYSQL
:SKIP_DOCKER

:: ============================================================
:: Step 5: Init Database Tables
:: ============================================================
echo.
echo [5/6] Initializing database tables...

python -c "import asyncio; from app.core.database import init_db; asyncio.run(init_db()); print('OK')" 2>nul
if errorlevel 1 (
    echo   [WARN] DB init failed, will retry on app startup
) else (
    echo   Database tables initialized
)

:: ============================================================
:: Step 6: Start Application
:: ============================================================
echo.
echo [6/6] Starting application...
echo.
echo ============================================================
echo   Deploy complete! Starting app...
echo   Frontend:  http://localhost:8000
echo   API Docs:  http://localhost:8000/api/docs
echo   API Redoc: http://localhost:8000/api/redoc
echo   Press Ctrl+C to stop
echo ============================================================
echo.

if %DEV_MODE%==1 (
    set APP_DEBUG=true
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
) else (
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
)

endlocal