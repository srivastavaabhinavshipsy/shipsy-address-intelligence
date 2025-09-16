#!/bin/bash

echo "Testing Backend API with curl..."
echo "================================"

# Test health endpoint
echo -e "\n1. Testing Health Check:"
curl -X GET http://localhost:5000/api/health

# Test validation endpoint
echo -e "\n\n2. Testing Address Validation:"
curl -X POST http://localhost:5000/api/validate-single \
  -H "Content-Type: application/json" \
  -d '{"address": "123 Main Street, Cape Town, Western Cape, 8001"}'

echo -e "\n\n3. Testing CORS Preflight:"
curl -X OPTIONS http://localhost:5000/api/validate-single \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v 2>&1 | grep -i "access-control"

echo -e "\n"