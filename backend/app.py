"""
AI Address Intelligence Flask Backend API with LLM Support
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import csv
import io
import uuid
import json
import time
from datetime import datetime
from typing import List, Dict
import os
import requests
from validator import SAAddressValidator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
# Enable CORS for all routes and origins with ngrok support
CORS(app, 
     resources={r"/*": {"origins": "*"}},
     methods=["GET", "POST", "OPTIONS", "HEAD"],
     allow_headers=["Content-Type", "Authorization", "ngrok-skip-browser-warning"],
     expose_headers=["Content-Length", "Content-Type"],
     supports_credentials=True)

# Initialize validators
validator = SAAddressValidator()  # Rule-based validator

# Initialize LLM validator (will be created on demand if API key is available)
llm_validator = None

def get_llm_validator():
    """Get or create LLM validator instance"""
    global llm_validator
    if llm_validator is None:
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key:
            try:
                from llm_validator import LLMAddressValidator
                llm_validator = LLMAddressValidator(api_key)
                print("LLM validator initialized successfully")
            except Exception as e:
                print(f"Failed to initialize LLM validator: {e}")
    return llm_validator

# In-memory storage for batch jobs
batch_jobs = {}

@app.route('/api/validate-single', methods=['POST', 'OPTIONS'])
def validate_single():
    """Validate a single address with option for LLM or rule-based"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        data = request.get_json()
        print(f"Received validation request: {data}")
        
        if not data or 'address' not in data:
            return jsonify({
                "error": "Missing 'address' field in request"
            }), 400
        
        address = data['address'].strip()
        validation_mode = data.get('validation_mode', 'rule')  # 'rule' or 'llm'
        
        if not address:
            return jsonify({
                "error": "Address cannot be empty"
            }), 400
        
        # Choose validator based on mode
        start_time = time.time()
        
        if validation_mode == 'llm':
            llm = get_llm_validator()
            if llm:
                try:
                    print(f"Using LLM validation for: {address}")
                    result = llm.validate_address(address)
                    processing_time = round((time.time() - start_time) * 1000, 2)
                    result['processing_time_ms'] = processing_time
                    result['timestamp'] = datetime.now().isoformat()
                    print(f"LLM validation successful: {result.get('confidence_score')}%")
                    return jsonify(result), 200
                except Exception as e:
                    print(f"LLM validation error: {e}")
                    # Fallback to rule-based
                    result = validator.validate_address(address)
                    processing_time = round((time.time() - start_time) * 1000, 2)
                    response = result.to_dict()
                    response['processing_time_ms'] = processing_time
                    response['timestamp'] = datetime.now().isoformat()
                    response['validation_method'] = 'rule (fallback)'
                    response['llm_error'] = str(e)
                    return jsonify(response), 200
            else:
                return jsonify({
                    "error": "LLM validation requested but GEMINI_API_KEY not configured. Please set GEMINI_API_KEY in .env file."
                }), 400
        
        # Default to rule-based validation
        print(f"Using rule-based validation for: {address}")
        result = validator.validate_address(address)
        processing_time = round((time.time() - start_time) * 1000, 2)
        
        response = result.to_dict()
        response['processing_time_ms'] = processing_time
        response['timestamp'] = datetime.now().isoformat()
        response['validation_method'] = 'rule'
        
        print(f"Validation complete: {response['confidence_score']}% confidence")
        return jsonify(response), 200
        
    except Exception as e:
        print(f"Error in validate_single: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500

@app.route('/api/validate-batch', methods=['POST', 'OPTIONS'])
def validate_batch():
    """Process batch validation from CSV with option for LLM or rule-based"""
    if request.method == 'OPTIONS':
        return '', 204
        
    validation_mode = request.form.get('validation_mode', 'rule')  # Get from form data
    
    if 'file' not in request.files:
        # Try to get CSV content from request body
        data = request.get_json()
        if not data or 'csv_content' not in data:
            return jsonify({"error": "No file or CSV content provided"}), 400
            
        csv_content = data['csv_content']
        csv_file = io.StringIO(csv_content)
        validation_mode = data.get('validation_mode', 'rule')  # Also check JSON data
    else:
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Read file content
        file_content = file.read().decode('utf-8')
        csv_file = io.StringIO(file_content)
    
    try:
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        
        if not rows:
            return jsonify({"error": "CSV file is empty"}), 400
        
        # Create a new job
        job_id = str(uuid.uuid4())
        addresses = []
        
        # Field mapping for flexible CSV parsing
        field_mappings = {
            'street_no': ['streetno', 'street_no', 'street_number', 'house_number', 'number', 'street no'],
            'street': ['street', 'street_address', 'address1', 'address_1', 'street address', 'street_name', 'street name'],
            'suburb': ['suburb', 'neighborhood', 'locality'],
            'city': ['city', 'town'],
            'area': ['area'],
            'province': ['province', 'state', 'region'],
            'postal_code': ['postalcode', 'postal_code', 'postal code', 'postcode', 'zip', 'zipcode', 'zip_code', 'pincode']
        }
        
        # Extract addresses from CSV
        for idx, row in enumerate(rows):
            # Check if 'address' column exists
            address = None
            
            # First, check for direct address field
            for key in row:
                if 'address' in key.lower() and row[key].strip():
                    address = row[key].strip()
                    print(f"Found address in column '{key}': {address}")
                    break
            
            # If no direct address field, try to build from components
            if not address:
                components = {}
                
                # Map CSV columns to component fields
                for field_key, field_variants in field_mappings.items():
                    for csv_key in row:
                        if csv_key.lower().strip() in field_variants:
                            value = row[csv_key].strip()
                            if value:
                                components[field_key] = value
                                print(f"Mapped {csv_key} -> {field_key}: {value}")
                                break
                
                # Build address from components
                address_parts = []
                
                # Add street number and name
                if 'street_no' in components and 'street' in components:
                    address_parts.append(f"{components['street_no']} {components['street']}")
                elif 'street' in components:
                    address_parts.append(components['street'])
                
                # Add other components
                if 'suburb' in components:
                    address_parts.append(components['suburb'])
                if 'city' in components:
                    address_parts.append(components['city'])
                elif 'area' in components:
                    address_parts.append(components['area'])
                if 'province' in components:
                    address_parts.append(components['province'])
                if 'postal_code' in components:
                    address_parts.append(components['postal_code'])
                
                if address_parts:
                    address = ', '.join(address_parts)
                    print(f"Built address from components: {address}")
            
            if address:
                addresses.append({
                    "id": len(addresses) + 1,
                    "original_row": row,
                    "address": address
                })
        
        if not addresses:
            return jsonify({
                "error": "No valid addresses found in CSV"
            }), 400
        
        # Process addresses
        batch_jobs[job_id] = {
            "status": "processing",
            "total": len(addresses),
            "processed": 0,
            "results": [],
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "validation_mode": validation_mode
        }
        
        # Process addresses with selected validation mode
        results = []
        
        # Choose validator
        if validation_mode == 'llm':
            llm = get_llm_validator()
            if not llm:
                return jsonify({
                    "error": "LLM validation requested but GEMINI_API_KEY not configured"
                }), 400
        
        for i, addr_data in enumerate(addresses):
            if validation_mode == 'llm':
                try:
                    result = llm.validate_address(addr_data["address"])
                except Exception as e:
                    print(f"LLM validation error for address {i+1}: {e}")
                    # Fallback to rule-based
                    rule_result = validator.validate_address(addr_data["address"])
                    result = rule_result.to_dict()
                    result['validation_method'] = 'rule (fallback)'
                    result['llm_error'] = str(e)
            else:
                rule_result = validator.validate_address(addr_data["address"])
                result = rule_result.to_dict()
                result['validation_method'] = 'rule'
            
            results.append({
                "id": addr_data["id"],
                "original_row": addr_data["original_row"],
                **result
            })
            batch_jobs[job_id]["processed"] = i + 1
            batch_jobs[job_id]["results"] = results
        
        batch_jobs[job_id]["status"] = "complete"
        batch_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        
        return jsonify({
            "job_id": job_id,
            "status": "processing",
            "total_addresses": len(addresses),
            "message": f"Processing {len(addresses)} addresses using {validation_mode} validation..."
        })
        
    except Exception as e:
        print(f"Error processing CSV: {str(e)}")
        return jsonify({
            "error": "Failed to process CSV file",
            "message": str(e)
        }), 500

@app.route('/api/batch-status/<job_id>', methods=['GET', 'OPTIONS'])
def get_batch_status(job_id):
    """Get status of a batch job"""
    if request.method == 'OPTIONS':
        return '', 204
        
    if job_id not in batch_jobs:
        return jsonify({"error": "Job not found"}), 404
    
    job = batch_jobs[job_id]
    return jsonify(job)

@app.route('/api/batch-results/<job_id>', methods=['GET', 'OPTIONS'])
def get_batch_results(job_id):
    """Download batch results as CSV"""
    if request.method == 'OPTIONS':
        return '', 204
        
    if job_id not in batch_jobs:
        return jsonify({"error": "Job not found"}), 404
    
    job = batch_jobs[job_id]
    if job["status"] != "complete":
        return jsonify({"error": "Job still processing"}), 202
    
    # Create CSV output
    output = io.StringIO()
    
    if job["results"]:
        fieldnames = [
            "id", "original_address", "is_valid", "confidence_score", 
            "confidence_level", "normalized_address", "street_address",
            "suburb", "city", "province", "postal_code", "issues", "suggestions",
            "validation_method"
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in job["results"]:
            row = {
                "id": result["id"],
                "original_address": result["original_address"],
                "is_valid": result["is_valid"],
                "confidence_score": result["confidence_score"],
                "confidence_level": result["confidence_level"],
                "normalized_address": result["normalized_address"],
                "street_address": result["components"].get("street_address", ""),
                "suburb": result["components"].get("suburb", ""),
                "city": result["components"].get("city", ""),
                "province": result["components"].get("province", ""),
                "postal_code": result["components"].get("postal_code", ""),
                "issues": "; ".join(result["issues"]),
                "suggestions": "; ".join(result["suggestions"]),
                "validation_method": result.get("validation_method", "rule")
            }
            writer.writerow(row)
    
    # Prepare file for download
    output.seek(0)
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)
    
    return send_file(
        mem,
        mimetype='text/csv',
        download_name=f'ai_address_intelligence_results_{job_id[:8]}.csv',
        as_attachment=True
    )

@app.route('/api/stats', methods=['GET', 'OPTIONS'])
def get_stats():
    """Get validation statistics"""
    if request.method == 'OPTIONS':
        return '', 204
        
    # Calculate stats from batch jobs
    total_validated = sum(job.get("processed", 0) for job in batch_jobs.values())
    completed_jobs = len([j for j in batch_jobs.values() if j.get("status") == "complete"])
    
    # Calculate success rate and method breakdown
    all_results = []
    llm_count = 0
    rule_count = 0
    
    for job in batch_jobs.values():
        all_results.extend(job.get("results", []))
    
    if all_results:
        valid_count = len([r for r in all_results if r.get("is_valid", False)])
        success_rate = int((valid_count / len(all_results)) * 100)
        
        # Count validation methods
        for r in all_results:
            method = r.get('validation_method', 'rule')
            if 'llm' in method.lower():
                llm_count += 1
            else:
                rule_count += 1
    else:
        success_rate = 0
    
    failed_validations = len([r for r in all_results if not r.get("is_valid", False)])
    
    return jsonify({
        "total_validated": total_validated,
        "success_rate": success_rate,
        "failed_validations": failed_validations,
        "completed_jobs": completed_jobs,
        "validation_methods": {
            "llm": llm_count,
            "rule": rule_count
        },
        "llm_available": get_llm_validator() is not None
    })

@app.route('/api/trigger-agent', methods=['POST', 'OPTIONS'])
def trigger_agent():
    """Trigger Shipsy agent for address resolution"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        
        # Extract address details from request
        address = data.get('address', '')
        action_type = data.get('action_type', 'call')  # 'call' or 'whatsapp'
        
        # Parse address to extract components
        result = validator.validate_address(address)
        components = result.components
        
        # Prepare payload for Shipsy agent
        agent_payload = {
            "customer_phone_number": "+917702189930",  # Updated phone number
            "reference_number": f"ADDR_{int(time.time())}",
            "customer_name": "Customer",
            "shipment_description": "Address Verification",
            "cod_amount": "0",
            "address_details": {
                "address_line_1": address,
                "pincode": components.get('postal_code', ''),
                "city": components.get('city', ''),
                "country": "South Africa",
                "latitude": str(result.coordinates.get('latitude', '')) if result.coordinates else '',
                "longitude": str(result.coordinates.get('longitude', '')) if result.coordinates else ''
            },
            "preferred_language": "en"
        }
        
        # Try to make API call to Shipsy agent
        try:
            shipsy_response = requests.post(
                'https://agent.shipsy.tech/api/v1/agent/address_resolution/aramexapp/create',
                headers={
                    'api-key': 'jsdbfjhsbdfjhsdbfuguwer9238749832kdssi89',
                    'Content-Type': 'application/json'
                },
                json=agent_payload,
                timeout=5
            )
            
            if shipsy_response.status_code == 200:
                return jsonify({
                    "success": True,
                    "message": f"Agent triggered for {action_type}",
                    "reference_number": agent_payload["reference_number"],
                    "response": shipsy_response.json()
                })
            else:
                raise Exception(f"API returned status {shipsy_response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"Failed to connect to Shipsy API: {e}")
            # Return success anyway (demo mode)
            return jsonify({
                "success": True,
                "message": f"Agent triggered for {action_type} (Demo Mode)",
                "reference_number": agent_payload["reference_number"],
                "demo_mode": True
            })
            
    except Exception as e:
        print(f"Error in trigger_agent: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    llm_status = "available" if get_llm_validator() else "not configured"
    return jsonify({
        "status": "healthy",
        "llm_validator": llm_status,
        "rule_validator": "available"
    })

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "name": "AI Address Intelligence API",
        "version": "2.0",
        "endpoints": [
            "/api/validate-single",
            "/api/validate-batch",
            "/api/batch-status/<job_id>",
            "/api/batch-results/<job_id>",
            "/api/stats",
            "/api/trigger-agent",
            "/health"
        ],
        "validation_modes": ["rule", "llm"],
        "llm_status": "available" if get_llm_validator() else "not configured (set GEMINI_API_KEY in .env)"
    })

if __name__ == '__main__':
    # Check for LLM availability on startup
    if get_llm_validator():
        print("✅ LLM validator is available (Gemini 2.5 Flash)")
    else:
        print("⚠️  LLM validator not configured. Set GEMINI_API_KEY in .env file to enable.")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)