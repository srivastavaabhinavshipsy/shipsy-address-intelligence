#!/usr/bin/env python3
"""
Integration test to verify API is working correctly
"""

import requests
import json
import time

def test_backend():
    """Test backend API endpoints"""
    print("=" * 60)
    print("🧪 Testing Backend API")
    print("=" * 60)
    
    base_url = "http://localhost:5000/api"
    
    # Test 1: Health Check
    print("\n1. Testing Health Check...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        print("   Please ensure the backend is running (python3 app.py)")
        return False
    
    # Test 2: Validate Single Address
    print("\n2. Testing Single Address Validation...")
    test_addresses = [
        "123 Main Street, Cape Town, Western Cape, 8001",
        "PO Box 456, Johannesburg, Gauteng, 2000",
        "Invalid Address Without Province"
    ]
    
    for address in test_addresses:
        try:
            response = requests.post(
                f"{base_url}/validate-single",
                json={"address": address},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Validated: {address[:50]}...")
                print(f"   Confidence: {data['confidence_level']} ({data['confidence_score']}%)")
                print(f"   Valid: {data['is_valid']}")
                if data.get('issues'):
                    print(f"   Issues: {', '.join(data['issues'][:2])}")
            else:
                print(f"❌ Validation failed for: {address}")
                print(f"   Error: {response.json()}")
        except Exception as e:
            print(f"❌ Error validating address: {e}")
    
    # Test 3: Get Provinces
    print("\n3. Testing Get Provinces...")
    try:
        response = requests.get(f"{base_url}/provinces")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Got {data['total']} provinces")
            print(f"   First 3: {', '.join([p['name'] for p in data['provinces'][:3]])}")
        else:
            print(f"❌ Failed to get provinces: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting provinces: {e}")
    
    # Test 4: CORS Headers
    print("\n4. Testing CORS Headers...")
    try:
        response = requests.options(
            f"{base_url}/validate-single",
            headers={
                "Origin": "http://localhost:3001",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        if response.status_code == 204:
            print("✅ CORS preflight passed")
        else:
            print(f"❌ CORS preflight failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing CORS: {e}")
    
    print("\n" + "=" * 60)
    print("✅ All backend tests completed!")
    print("=" * 60)
    return True

def test_frontend_connection():
    """Test if frontend can connect to backend"""
    print("\n" + "=" * 60)
    print("🌐 Testing Frontend → Backend Connection")
    print("=" * 60)
    
    print("\nTo test the frontend connection:")
    print("1. Open http://localhost:3001 in your browser")
    print("2. Open Developer Console (F12)")
    print("3. Type an address and click 'Validate'")
    print("4. Check the Network tab for the API call")
    print("5. Check the Console tab for any errors")
    
    print("\nExpected behavior:")
    print("✅ API call to http://localhost:5000/api/validate-single")
    print("✅ Response with confidence_level and score")
    print("✅ Toast notification showing result")

if __name__ == "__main__":
    print("\n🚀 SA-LogiCheck Integration Test")
    print("================================\n")
    
    # Check if backend is running
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=2)
        backend_running = True
    except:
        backend_running = False
    
    if not backend_running:
        print("❌ Backend is not running!")
        print("\nTo start the backend:")
        print("1. Open a new terminal")
        print("2. cd sa-logicheck-demo/backend")
        print("3. python3 app.py")
        print("\nThen run this test again.")
    else:
        if test_backend():
            test_frontend_connection()
            print("\n✅ Integration test complete!")
            print("\nNext steps:")
            print("1. Ensure frontend is running (cd frontend && npm start)")
            print("2. Open http://localhost:3001")
            print("3. Try validating an address")
            print("\nExample addresses to try:")
            print("- 123 Main Street, Cape Town, Western Cape, 8001")
            print("- PO Box 456, Johannesburg, Gauteng, 2000")
            print("- Unit 7, 89 Beach Road, Durban, KwaZulu-Natal, 4319")