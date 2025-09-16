#!/bin/bash

echo "🚀 Starting SA-LogiCheck (Shipsy Address Intelligence)"
echo "================================================"

# Start backend
echo "📦 Starting Flask backend..."
cd backend
python3 -m venv venv 2>/dev/null || true
source venv/bin/activate
pip install -q -r requirements.txt
python3 app.py &
BACKEND_PID=$!
echo "✅ Backend running on http://localhost:5000 (PID: $BACKEND_PID)"

# Start frontend
echo "📦 Starting React frontend..."
cd ../frontend
npm install --silent
npm start &
FRONTEND_PID=$!
echo "✅ Frontend will open at http://localhost:3000 (PID: $FRONTEND_PID)"

echo ""
echo "================================================"
echo "✨ Shipsy Address Intelligence is starting..."
echo "📍 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop all services"
echo "================================================"

# Wait and handle shutdown
trap "echo ''; echo '🛑 Shutting down services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

wait