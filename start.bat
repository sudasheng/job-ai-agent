@echo off
setlocal

:: ============================================================
::  Job AI Agent - Start (daily use)
:: ============================================================
::  Usage:
::    start.bat           normal start
::    start.bat dev       dev mode (hot-reload)
::    start.bat skip      skip Docker MySQL
:: ============================================================

set DEV_MODE=0
set SKIP_DOCKER=0

if /i "%~1"=="dev"  set DEV_MODE=1
if /i "%~1"=="skip" set SKIP_DOCKER=1
if /i "%~2"=="dev"  set DEV_MODE=1
if /i "%~2"=="skip" set SKIP_DOCKER=1

set "PROJECT_ROOT=%~dp0"
set "VENV_PATH=%PROJECT_ROOT%.venv"

echo.
echo ============================================================
echo   Job AI Agent - Start
echo ============================================================
echo.

:: 1. Check and activate venv
if not exist "%VENV_PATH%" (
    echo [ERROR] venv not found. Please run deploy.bat first
    exit /b 1
)

call "%VENV_PATH%\Scripts\activate.bat"
echo [OK] venv activated

:: 2. Start Docker MySQL if not running
if %SKIP_DOCKER%==1 goto :SKIP_DOCKER

docker ps --filter "name=job-ai-agent-mysql" --format "{{.Names}}" 2>nul | findstr /c:"job-ai-agent-mysql" >nul
if not errorlevel 1 goto :MYSQL_RUNNING

echo [INFO] Starting MySQL container...
docker ps -a --filter "name=job-ai-agent-mysql" --format "{{.Names}}" 2>nul | findstr /c:"job-ai-agent-mysql" >nul
if errorlevel 1 (
    docker compose up -d mysql >nul 2>&1
    echo [INFO] MySQL container created
) else (
    docker start job-ai-agent-mysql >nul 2>&1
    echo [INFO] MySQL container started
)

echo [INFO] Waiting for MySQL...
set /a RETRY=0
:WAIT_MYSQL
docker exec job-ai-agent-mysql mysqladmin ping -h localhost -u root -proot123456 >nul 2>&1
if not errorlevel 1 goto :MYSQL_READY
set /a RETRY+=1
if %RETRY% geq 30 goto :MYSQL_READY
timeout /t 2 /nobreak >nul
goto :WAIT_MYSQL

:MYSQL_READY
:MYSQL_RUNNING
echo [OK] MySQL container running

:SKIP_DOCKER

:: 3. Start application
echo.
echo ============================================================
echo   Frontend:  http://localhost:8000
echo   API Docs:  http://localhost:8000/api/docs
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