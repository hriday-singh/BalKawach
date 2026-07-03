@echo off
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

echo.
echo ===================================================
echo Containers started successfully!
echo.
echo Frontend   : http://localhost:9122
echo Backend API: http://localhost:9120
echo ===================================================
echo.
echo Opening browser...
timeout /t 3 >nul
start http://localhost:9122
pause
