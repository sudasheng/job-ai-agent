@echo off
setlocal

:: ============================================================
::  Job AI Agent - Stop Services
:: ============================================================
::  Usage:
::    stop.bat           stop MySQL (keep data)
::    stop.bat clean     stop and remove all data
:: ============================================================

set CLEAN_MODE=0
if /i "%~1"=="clean" set CLEAN_MODE=1

echo.
echo ============================================================
echo   Job AI Agent - Stop
echo ============================================================
echo.

docker ps --filter "name=job-ai-agent-mysql" --format "{{.Names}}" 2>nul | findstr /c:"job-ai-agent-mysql" >nul
if errorlevel 1 (
    echo [INFO] MySQL container not running
    goto :DONE
)

if %CLEAN_MODE%==1 (
    echo [INFO] Removing MySQL container and data volume...
    docker compose down -v >nul 2>&1
    echo [OK] MySQL container and data removed
) else (
    echo [INFO] Stopping MySQL container (data preserved)...
    docker stop job-ai-agent-mysql >nul 2>&1
    echo [OK] MySQL container stopped
)

:DONE
echo.
echo   To restart: start.bat
echo.

endlocal