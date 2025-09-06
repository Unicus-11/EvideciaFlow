#!/bin/bash

echo "========================================"
echo "EvideciaFlow Development Servers"
echo "========================================"
echo

echo "Checking dependencies..."
python3 -c "import flask, flask_cors, groq" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing Python dependencies..."
    pip3 install -r requirements.txt
fi

if [ ! -d "frontend/node_modules" ]; then
    echo "Installing Node.js dependencies..."
    cd frontend
    npm install
    cd ..
fi

echo
echo "Starting Flask Backend on port 5000..."
gnome-terminal -- bash -c "cd $(dirname "$0") && python3 app.py; exec bash" &

sleep 5

echo "Starting Next.js Frontend on port 3000..."
gnome-terminal -- bash -c "cd $(dirname "$0")/frontend && npm run dev; exec bash" &

echo
echo "========================================"
echo "Both servers are starting..."
echo "Backend: http://localhost:5000"
echo "Frontend: http://localhost:3000"
echo "Test API: frontend/test-api.html"
echo "========================================"
echo
echo "Press Ctrl+C to exit..."
wait
