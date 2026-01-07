@echo off
echo Starting Little Story...

:: Запускаем Бэкенд в отдельном окне
start "Backend Server" cmd /k "cd backend && venv\Scripts\activate && uvicorn main:app --reload"

:: Ждем 2 секунды, чтобы бэкенд успел проснуться
timeout /t 2 /nobreak >nul

:: Запускаем Фронтенд в отдельном окне
start "Frontend Client" cmd /k "cd frontend && npm run dev"

echo Game started! You can close this window.