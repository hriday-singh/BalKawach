@echo off
:: Change to the directory of this script (fixes issues when running as Administrator)
cd /d "%~dp0"

echo ===================================================
echo Starting BalKawach in Docker
echo ===================================================
echo.

docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed or not running.
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop
    pause & exit /b 1
)

echo Building and starting containers (this may take a few minutes the first time)...
docker-compose up --build -d

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start Docker containers.
    echo Please make sure Docker Desktop is fully running and try opening this script as Administrator.
    pause & exit /b 1
)

echo.
echo ===================================================
echo Containers started successfully!
echo.
echo Frontend   : http://localhost:9122
echo Backend API: http://localhost:9123
echo ===================================================
echo.
echo Opening browser...
timeout /t 3 >nul
start http://localhost:9122
pause
