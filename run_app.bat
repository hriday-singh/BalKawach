@echo off
echo =======================================================
echo   Child Protection Case Management Platform Launcher
echo =======================================================
echo.

set /p USE_VENV="Do you want to run using the virtual environment (venv)? (Y/N, default=Y): "
if /I "%USE_VENV%"=="N" (
    echo Running WITHOUT virtual environment...
    set PYTHON_CMD=python
) else (
    if exist venv\Scripts\activate.bat (
        echo Running WITH virtual environment...
        set PYTHON_CMD=venv\Scripts\python.exe
    ) else (
        echo [WARNING] venv not found! Running WITHOUT virtual environment...
        set PYTHON_CMD=python
    )
)

echo.
echo Starting Main FastAPI Backend...
start "Main Backend (FastAPI)" cmd /k "%PYTHON_CMD% main.py"

echo.
echo Starting Transcription Server...
start "Transcription Server" cmd /k "%PYTHON_CMD% -m transcription_server.main"

echo.
echo Starting React Frontend...
start "Frontend (Vite)" cmd /k "cd frontend && npm run dev"

echo.
echo All services are booting up in separate windows!
echo - Main Backend will be available at http://localhost:9120
echo - Transcription Server will be available at http://localhost:9121
echo - Frontend will be available at http://localhost:9122
echo.
pause
