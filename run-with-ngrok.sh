#!/bin/bash

echo "🚀 AI Address Intelligence - Ngrok Setup Script"
echo "================================================"
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed. Please install it first:"
    echo "   brew install ngrok (on macOS)"
    echo "   or download from: https://ngrok.com/download"
    exit 1
fi

echo "📋 Instructions:"
echo "1. This script will help you run the application publicly via ngrok"
echo "2. You'll need to run ngrok tunnels for both frontend and backend"
echo ""

echo "Step 1: Start the backend server"
echo "---------------------------------"
echo "In Terminal 1, run:"
echo "  cd backend"
echo "  python app.py"
echo ""
read -p "Press Enter when backend is running on port 5000..."

echo ""
echo "Step 2: Create ngrok tunnel for backend"
echo "----------------------------------------"
echo "In Terminal 2, run:"
echo "  ngrok http 5000"
echo ""
echo "Copy the HTTPS URL (e.g., https://abc123.ngrok.io)"
read -p "Enter your backend ngrok URL: " BACKEND_URL

# Create .env file for frontend
echo ""
echo "Creating frontend .env file..."
cat > frontend/.env << EOF
REACT_APP_API_URL=$BACKEND_URL
EOF

echo "✅ Frontend .env file created with backend URL: $BACKEND_URL"

echo ""
echo "Step 3: Start the frontend server"
echo "----------------------------------"
echo "In Terminal 3, run:"
echo "  cd frontend"
echo "  npm start"
echo ""
read -p "Press Enter when frontend is running on port 3000..."

echo ""
echo "Step 4: Create ngrok tunnel for frontend"
echo "-----------------------------------------"
echo "In Terminal 4, run:"
echo "  ngrok http 3000"
echo ""
echo "Copy the HTTPS URL (e.g., https://xyz456.ngrok.io)"
read -p "Enter your frontend ngrok URL: " FRONTEND_URL

echo ""
echo "================================================"
echo "🎉 Setup Complete!"
echo "================================================"
echo ""
echo "Your application is now publicly accessible at:"
echo "  Frontend: $FRONTEND_URL"
echo "  Backend:  $BACKEND_URL"
echo ""
echo "Share the frontend URL with others to access your app!"
echo ""
echo "⚠️  Important Notes:"
echo "- ngrok URLs change each time you restart the tunnel"
echo "- Free ngrok has connection limits"
echo "- Keep all terminals open while using the app"
echo ""
echo "To stop, press Ctrl+C in each terminal"