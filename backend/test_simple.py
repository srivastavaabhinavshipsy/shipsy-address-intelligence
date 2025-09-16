"""
Simple test server to verify connectivity
"""

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins="*")

@app.route('/api/health', methods=['GET'])
def health():
    print("Health check called!")
    return jsonify({"status": "ok", "message": "Backend is running"})

@app.route('/api/validate-single', methods=['POST', 'OPTIONS'])
def validate():
    if request.method == 'OPTIONS':
        return '', 204
    
    print("Validation called!")
    data = request.get_json()
    print(f"Received: {data}")
    
    # Return mock success response
    return jsonify({
        "is_valid": True,
        "confidence_score": 85.0,
        "confidence_level": "CONFIDENT",
        "original_address": data.get('address', ''),
        "normalized_address": data.get('address', ''),
        "components": {},
        "issues": [],
        "suggestions": [],
        "processing_time_ms": 10,
        "timestamp": "2024-01-01T00:00:00"
    })

if __name__ == '__main__':
    print("\n" + "="*50)
    print("TEST SERVER RUNNING")
    print("Test with: curl -X POST http://localhost:5000/api/validate-single -H 'Content-Type: application/json' -d '{\"address\":\"test\"}'")
    print("="*50 + "\n")
    app.run(port=5000, debug=True)