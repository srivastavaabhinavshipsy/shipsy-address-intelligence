#!/bin/bash

echo "🔄 Update ngrok Backend URL Script"
echo "===================================="
echo ""
echo "This script helps update the frontend with a new ngrok backend URL"
echo ""

# Get the new ngrok URL from user
read -p "Enter your NEW ngrok backend URL (e.g., https://abc123.ngrok.io): " NEW_URL

# Remove trailing slash if present
NEW_URL=${NEW_URL%/}

# Update the .env file
echo "REACT_APP_API_URL=$NEW_URL" > frontend/.env

echo ""
echo "✅ Updated frontend/.env with new backend URL: $NEW_URL"
echo ""
echo "Now restart your frontend:"
echo "  1. Press Ctrl+C in the frontend terminal"
echo "  2. Run: npm start"
echo ""
echo "Your app should now work with the new ngrok URL!"