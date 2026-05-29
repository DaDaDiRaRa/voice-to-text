@echo off
echo Starting Voice-to-Text...

start "Backend" cmd /k "cd /d D:\APPS\voice-to-text\backend && .\venv\Scripts\activate && uvicorn main:app --reload --port 8000"

timeout /t 2 /nobreak >nul

start "Frontend" cmd /k "cd /d D:\APPS\voice-to-text\frontend && npm run dev"

echo.
echo Backend:  http://localhost:8000/docs
echo Frontend: http://localhost:5173
echo.
