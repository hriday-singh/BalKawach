@echo off
echo ===================================================
echo Starting BalKawach (Child Protection Management)
echo ===================================================
echo.

echo Starting FastAPI Backend...
start "BalKawach Backend" cmd /k "python main.py"

echo Starting Transcription Server...
start "Transcription Server" cmd /k "python -m transcription_server.main"

echo Starting Vite React Frontend...
start "BalKawach Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Servers are starting up in separate windows!
echo Backend API will be available at: http://localhost:9120
echo Transcription API will be available at: http://localhost:9121
echo Frontend will be available at: http://localhost:9122
echo.
pause
