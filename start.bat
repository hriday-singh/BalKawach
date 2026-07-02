@echo off
echo ===================================================
echo Starting BalKawach (Child Protection Management)
echo ===================================================
echo.

echo Starting FastAPI Backend...
start "BalKawach Backend" cmd /k "python -m uvicorn main:app --host 0.0.0.0 --port 8000"

echo Starting Vite React Frontend...
start "BalKawach Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Both servers are starting up in separate windows!
echo Backend API will be available at: http://localhost:8000
echo Frontend will be available at: http://localhost:5173
echo.
pause
