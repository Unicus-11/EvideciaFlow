@echo off
echo ========================================
echo EvideciaFlow Development Servers
echo ========================================
echo.

echo Checking dependencies...
python -c "import flask, flask_cors, groq" 2>nul
if errorlevel 1 (
    echo Installing Python dependencies...
    pip install -r requirements.txt
)

if not exist "frontend\node_modules" (
    echo Installing Node.js dependencies...
    cd frontend
    npm install
    cd ..
)

echo.
echo Starting Flask Backend on port 5000...
start "Flask Backend" cmd /k "cd /d %~dp0 && python app.py"

timeout /t 5 /nobreak >nul

echo Starting Next.js Frontend on port 3000...
start "Next.js Frontend" cmd /k "cd /d %~dp0\frontend && npm run dev"

echo.
echo ========================================
echo Both servers are starting...
echo Backend: http://localhost:5000
echo Frontend: http://localhost:3000
echo Test API: frontend/test-api.html
echo ========================================
echo.
echo Press any key to exit...
pause >nul
