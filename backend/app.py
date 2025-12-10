"""
AI Address Intelligence Flask Backend API with LLM Support
"""

from flask import Flask, request, jsonify, send_file, make_response
from flask_cors import CORS, cross_origin
import csv
import io
import uuid
import json
import time
import random
import string
from datetime import datetime
from typing import List, Dict
import os
import requests
from validator import SAAddressValidator
from dotenv import load_dotenv
import threading
from database import AddressDatabase

# Import country detection utilities
from countries import (
    detect_country_from_address,
    detect_country_from_cn_details,
    list_supported_countries,
    get_country_info,
    is_supported
)

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize database
db = AddressDatabase()

# Simple CORS configuration that works
app.config['CORS_HEADERS'] = 'Content-Type'
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize validators
validator = SAAddressValidator()  # Rule-based validator

# Initialize LLM validator (will be created on demand if API key is available)
llm_validator = None

# Virtual number management
virtual_numbers_lock = threading.Lock()
available_virtual_numbers = []
used_virtual_numbers = []

# Background polling
polling_thread = None
polling_active = False

def load_virtual_numbers():
    """Load virtual numbers from JSON file"""
    global available_virtual_numbers
    try:
        with open('virtual_numbers.json', 'r') as f:
            available_virtual_numbers = json.load(f)
        print(f"Loaded {len(available_virtual_numbers)} virtual numbers")
    except Exception as e:
        print(f"Failed to load virtual numbers: {e}")
        available_virtual_numbers = []

def get_next_virtual_number():
    """Get the next available virtual number"""
    global available_virtual_numbers, used_virtual_numbers
    with virtual_numbers_lock:
        if available_virtual_numbers:
            number = available_virtual_numbers.pop(0)
            used_virtual_numbers.append(number)
            # Save the updated list back to file
            try:
                with open('virtual_numbers.json', 'w') as f:
                    json.dump(available_virtual_numbers, f, indent=2)
            except Exception as e:
                print(f"Failed to save virtual numbers: {e}")
            return number
        else:
            # Fallback to generated ID if no virtual numbers available
            return f"VAL{int(time.time()*1000)}"

# Load virtual numbers on startup
load_virtual_numbers()

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

@app.route('/api/fetch-cn-details', methods=['POST'])
@cross_origin()
def fetch_cn_details():
    """Fetch consignment details from Shipsy API"""
    try:
        data = request.json
        consignment_number = data.get('consignment_number', '').strip()
        
        if not consignment_number:
            return jsonify({"error": "Consignment number is required"}), 400
        
        # Call Shipsy API to fetch consignment details
        shipsy_api_url = "https://demodashboardapi.shipsy.in/api/client/integration/fetchConsignments"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Basic YmNmZDdlZWJmNzdiMmQ4NDJlNzVjMDA1NzI3OGY4Og=='
        }
        payload = {
            "referenceNumberList": [consignment_number]
        }
        
        try:
            response = requests.post(shipsy_api_url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            
            shipsy_data = response.json()
            
            # Extract consignment details from response
            if (shipsy_data and 'data' in shipsy_data and 
                'page_data' in shipsy_data['data'] and 
                len(shipsy_data['data']['page_data']) > 0):
                consignment = shipsy_data['data']['page_data'][0]
                
                # Extract required fields - using correct field names
                consignee_name = consignment.get('destination_name', 'N/A')
                consignee_address = consignment.get('destination_address_line_1', 'N/A')
                status = consignment.get('status', 'N/A')
                
                # Also extract additional useful fields
                contact_number = consignment.get('consignment_destination_phone', '')
                email = consignment.get('destination_email', '')
                destination_city = consignment.get('destination_city', '')
                destination_state = consignment.get('destination_state', '')
                destination_pincode = consignment.get('destination_pincode', '')
                
                # Construct full address
                full_address = consignee_address
                if destination_city:
                    full_address += f", {destination_city}"
                if destination_state:
                    full_address += f", {destination_state}"
                if destination_pincode:
                    full_address += f", {destination_pincode}"
                
                return jsonify({
                    "success": True,
                    "consignment_number": consignment_number,
                    "consignee_name": consignee_name,
                    "consignee_address": consignee_address,
                    "full_address": full_address,
                    "status": status,
                    "contact_number": contact_number,
                    "email": email,
                    "destination_city": destination_city,
                    "destination_state": destination_state,
                    "destination_pincode": destination_pincode,
                    "ready_for_intelligence": True,
                    "raw_data": consignment  # Include full data for debugging
                }), 200
            else:
                return jsonify({
                    "success": False,
                    "error": "No consignment found with this number",
                    "consignment_number": consignment_number
                }), 404
                
        except requests.exceptions.RequestException as e:
            print(f"Error calling Shipsy API: {e}")
            return jsonify({
                "success": False,
                "error": f"Failed to fetch from Shipsy API: {str(e)}",
                "consignment_number": consignment_number
            }), 500
            
    except Exception as e:
        print(f"Error in fetch_cn_details: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/validate-single', methods=['POST'])
@cross_origin()
def validate_single():
    """Validate a single address with LLM for intelligence analysis"""

    try:
        data = request.get_json()
        print(f"Received validation request: {data}")

        # Handle both direct address and CN-based requests
        if not data or ('address' not in data and 'consignment_number' not in data):
            return jsonify({
                "error": "Missing 'address' or 'consignment_number' field in request"
            }), 400

        address = data.get('address', '').strip()
        consignment_number = data.get('consignment_number', '').strip()
        cn_details = data.get('cn_details', {})

        # If we have CN details, use them
        if cn_details and not address:
            address = cn_details.get('full_address') or cn_details.get('consignee_address', '')

        if not address:
            return jsonify({
                "error": "Address cannot be empty"
            }), 400

        # Determine country: URL param > request body > CN details > auto-detect from address
        country_code = request.args.get('country', '').upper()
        if not country_code:
            country_code = data.get('country', '').upper()
        if not country_code and cn_details:
            country_code = detect_country_from_cn_details(cn_details)
        if not country_code:
            country_code = detect_country_from_address(address)

        # Validate country is supported
        if not is_supported(country_code):
            return jsonify({
                "error": f"Unsupported country: {country_code}",
                "supported_countries": [c['code'] for c in list_supported_countries()]
            }), 400

        country_info = get_country_info(country_code)
        print(f"🌍 Detected country: {country_info['name']} ({country_code})")

        # Always use LLM for CN-based addresses for intelligence analysis
        validation_mode = 'llm' if consignment_number else data.get('validation_mode', 'llm')

        # Choose validator based on mode
        start_time = time.time()

        if validation_mode == 'llm':
            llm = get_llm_validator()
            if llm:
                try:
                    print(f"Using LLM intelligence analysis for CN {consignment_number}: {address}")
                    result = llm.validate_address(address, country_code)
                    processing_time = round((time.time() - start_time) * 1000, 2)
                    result['processing_time_ms'] = processing_time
                    result['timestamp'] = datetime.now().isoformat()
                    # Use consignment number with timestamp for uniqueness
                    result['id'] = f"{consignment_number}_{int(time.time()*1000)}" if consignment_number else get_next_virtual_number()
                    result['original_address'] = address
                    result['contact_number'] = data.get('contact_number') or cn_details.get('contact_number')
                    result['consignment_number'] = consignment_number
                    result['consignee_name'] = cn_details.get('consignee_name')
                    
                    # Save to database
                    db.save_validated_address(result)
                    
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
                    # Use consignment number with timestamp for uniqueness
                    response['id'] = f"{consignment_number}_{int(time.time()*1000)}" if consignment_number else get_next_virtual_number()
                    response['original_address'] = address
                    response['contact_number'] = data.get('contact_number') or cn_details.get('contact_number')
                    response['consignment_number'] = consignment_number
                    response['consignee_name'] = cn_details.get('consignee_name')
                    
                    # Save to database
                    db.save_validated_address(response)
                    
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
        # Use consignment number with timestamp for uniqueness
        response['id'] = f"{consignment_number}_{int(time.time()*1000)}" if consignment_number else get_next_virtual_number()
        response['original_address'] = address
        response['contact_number'] = data.get('contact_number') or cn_details.get('contact_number')
        response['consignment_number'] = consignment_number
        response['consignee_name'] = cn_details.get('consignee_name')
        
        # Save to database
        db.save_validated_address(response)
        
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

@app.route('/api/validate-batch', methods=['POST'])
@cross_origin()
def validate_batch():
    """Process batch validation from CSV with option for LLM or rule-based"""
        
    validation_mode = request.form.get('validation_mode', 'llm')  # Always use AI mode (llm)
    
    if 'file' not in request.files:
        # Try to get CSV content from request body
        data = request.get_json()
        if not data or 'csv_content' not in data:
            return jsonify({"error": "No file or CSV content provided"}), 400
            
        csv_content = data['csv_content']
        csv_file = io.StringIO(csv_content)
        validation_mode = data.get('validation_mode', 'llm')  # Always use AI mode (llm)
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

@app.route('/api/batch-status/<job_id>', methods=['GET'])
@cross_origin()
def get_batch_status(job_id):
    """Get status of a batch job"""
        
    if job_id not in batch_jobs:
        return jsonify({"error": "Job not found"}), 404
    
    job = batch_jobs[job_id]
    return jsonify(job)

@app.route('/api/batch-results/<job_id>', methods=['GET'])
@cross_origin()
def get_batch_results(job_id):
    """Download batch results as CSV"""
        
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

@app.route('/api/stats', methods=['GET'])
@cross_origin()
def get_stats():
    """Get validation statistics"""
        
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

@app.route('/api/confirmed-address/<virtual_number>', methods=['GET'])
@cross_origin()
def get_confirmed_address(virtual_number):
    """Get confirmed address for a validation from database"""
    
    # Extract consignment number from virtual_number (remove timestamp if present)
    if virtual_number and '_' in virtual_number:
        # If it has timestamp (e.g., "EQ5498765610_1758724415625"), take only the CN part
        reference_number = virtual_number.split('_')[0]
    else:
        reference_number = virtual_number
    
    # Try to get from database first using the clean reference number
    confirmed = db.get_confirmed_address(reference_number)
    
    if confirmed:
        return jsonify({
            "virtual_number": reference_number,
            "confirmed_address": {
                "address": confirmed['confirmed_address'],
                "coordinates": confirmed['confirmed_coordinates'],
                "confirmed_by": confirmed['confirmed_by'],
                "confirmed_at": confirmed['confirmed_at'],
                "confirmation_method": confirmed['confirmation_method'],
                "differences": confirmed['differences']
            },
            "status": "confirmed"
        })
    else:
        # Check if still pending
        pending = db.get_pending_confirmations()
        if reference_number in pending:
            # Trigger a poll for this specific address using clean reference number
            if poll_single_address(reference_number):
                # If polling succeeded, try to get the confirmed address again
                confirmed = db.get_confirmed_address(reference_number)
                if confirmed:
                    return jsonify({
                        "virtual_number": reference_number,
                        "confirmed_address": {
                            "address": confirmed['confirmed_address'],
                            "coordinates": confirmed['confirmed_coordinates'],
                            "confirmed_by": confirmed['confirmed_by'],
                            "confirmed_at": confirmed['confirmed_at'],
                            "confirmation_method": confirmed['confirmation_method'],
                            "differences": confirmed['differences']
                        },
                        "status": "confirmed"
                    })
        else:
            pass
            
        return jsonify({
            "virtual_number": reference_number,
            "status": "pending"
        })

def poll_single_address(reference_number):
    """Poll Shipsy API for a single address confirmation"""
    try:
        polling_url = "https://wbdemo.shipsy.io/webhook/job/details"
        
        response = requests.post(
            polling_url,
            json={"reference_number": reference_number},
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Extract the nested data
            task_data = response_data.get('data', {})
            updated_address = task_data.get('updated_address', {})
            
            # The KEY check: if updated_address exists, customer has confirmed
            if updated_address and updated_address.get('address'):
                # Customer has provided confirmed address!
                current_address = task_data.get('current_address', {})
                
                confirmed_data = {
                    'virtual_number': reference_number,
                    'confirmed_address': updated_address.get('address'),
                    'confirmed_coordinates': {
                        'latitude': updated_address.get('latitude'),
                        'longitude': updated_address.get('longitude')
                    },
                    'confirmation_method': 'whatsapp',  # Can be determined from task_data if needed
                    'confirmed_by': 'Customer',
                    'agent_response': response_data,
                    'differences': {
                        'original': current_address.get('address_line_1', ''),
                        'updated': updated_address.get('address')
                    },
                    'confirmed_at': response_data.get('updated_at', datetime.now().isoformat())
                }
                
                # Save to database
                db.save_confirmed_address(confirmed_data)
                return True
            else:
                # No updated_address yet, customer hasn't confirmed
                pass
                
    except Exception as e:
        print(f"Error polling address {reference_number}: {e}")
        import traceback
        traceback.print_exc()
    
    return False

@app.route('/api/poll-single/<virtual_number>', methods=['POST'])
@cross_origin()
def poll_single_endpoint(virtual_number):
    """Manually poll for a single virtual number"""
    success = poll_single_address(virtual_number)
    
    if success:
        confirmed = db.get_confirmed_address(virtual_number)
        if confirmed:
            return jsonify({
                "success": True,
                "message": f"Successfully polled and found confirmed address for {virtual_number}",
                "confirmed_address": confirmed
            })
    
    return jsonify({
        "success": False,
        "message": f"No confirmed address found yet for {virtual_number}"
    })

@app.route('/api/debug-database', methods=['GET'])
@cross_origin()
def debug_database():
    """Debug endpoint to check database contents"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Check confirmed addresses
        cursor.execute("SELECT virtual_number, confirmed_address FROM confirmed_addresses")
        confirmed = cursor.fetchall()
        
        # Check agent calls
        cursor.execute("SELECT virtual_number, action_type, status FROM agent_calls")
        agent_calls = cursor.fetchall()
        
        result = {
            "confirmed_addresses": [
                {"cn": row['virtual_number'], "address": row['confirmed_address']} 
                for row in confirmed
            ],
            "agent_calls": [
                {"cn": row['virtual_number'], "type": row['action_type'], "status": row['status']} 
                for row in agent_calls
            ]
        }
        
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500

@app.route('/api/check-status/<virtual_number>', methods=['GET'])
@cross_origin()
def check_status(virtual_number):
    """Check the complete status of a virtual number"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    status = {
        "virtual_number": virtual_number,
        "validated_address": None,
        "agent_triggered": False,
        "confirmed_address": None
    }
    
    try:
        # Check validated address
        cursor.execute("SELECT * FROM validated_addresses WHERE virtual_number = ?", (virtual_number,))
        validated = cursor.fetchone()
        if validated:
            status["validated_address"] = {
                "address": validated['original_address'],
                "confidence_score": validated['confidence_score']
            }
        
        # Check agent calls
        cursor.execute("SELECT * FROM agent_calls WHERE virtual_number = ?", (virtual_number,))
        agent_call = cursor.fetchone()
        if agent_call:
            status["agent_triggered"] = True
            status["agent_call"] = {
                "action_type": agent_call['action_type'],
                "status": agent_call['status'],
                "created_at": agent_call['created_at']
            }
        
        # Check confirmed address
        cursor.execute("SELECT * FROM confirmed_addresses WHERE virtual_number = ?", (virtual_number,))
        confirmed = cursor.fetchone()
        if confirmed:
            status["confirmed_address"] = {
                "address": confirmed['confirmed_address'],
                "confirmed_at": confirmed['confirmed_at']
            }
        
        conn.close()
        return jsonify(status)
        
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500

@app.route('/api/poll-confirmations', methods=['POST'])
@cross_origin()
def poll_confirmations():
    """Manually trigger polling for all pending confirmations"""
    # Debug: Check what's in agent_calls table
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT virtual_number, status, action_type FROM agent_calls ORDER BY created_at DESC")
        all_agent_calls = cursor.fetchall()
        
        cursor.execute("SELECT virtual_number FROM confirmed_addresses")
        confirmed = cursor.fetchall()
        conn.close()
    except Exception as e:
        pass
    
    pending = db.get_pending_confirmations()
    
    if not pending:
        return jsonify({
            "success": True,
            "message": "No pending confirmations to poll",
            "pending_count": 0
        })
    
    results = {
        'polled': [],
        'confirmed': [],
        'still_pending': []
    }
    
    for reference_number in pending:
        results['polled'].append(reference_number)
        # poll_single_address returns True only if updated_address was found
        if poll_single_address(reference_number):
            results['confirmed'].append(reference_number)
        else:
            results['still_pending'].append(reference_number)
    
    return jsonify({
        "success": True,
        "results": results,
        "message": f"Polled {len(pending)} addresses: {len(results['confirmed'])} confirmed, {len(results['still_pending'])} still pending"
    })

@app.route('/api/poll-all', methods=['POST'])
@cross_origin()
def poll_all_jobs():
    """Poll Shipsy API for all job statuses"""
    try:
        polling_url = "https://wbdemo.shipsy.io/webhook/job/all/details"
        
        response = requests.get(
            polling_url,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            all_jobs = response.json()
            
            # Process each completed job
            confirmed_count = 0
            for job in all_jobs:
                if job.get('status') == 'completed' and job.get('reference_number'):
                    reference_number = job.get('reference_number')
                    
                    # Check if this is one of our virtual numbers
                    if reference_number and reference_number.startswith('CRNSEP'):
                        confirmed_data = {
                            'virtual_number': reference_number,
                            'confirmed_address': job.get('corrected_address', job.get('address')),
                            'confirmed_coordinates': {
                                'latitude': job.get('latitude'),
                                'longitude': job.get('longitude')
                            },
                            'confirmation_method': job.get('interaction_type', 'unknown'),
                            'confirmed_by': 'Customer',
                            'agent_response': job,
                            'differences': job.get('changes', {}),
                            'confirmed_at': job.get('completed_at', datetime.now().isoformat())
                        }
                        
                        if db.save_confirmed_address(confirmed_data):
                            confirmed_count += 1
            
            return jsonify({
                "success": True,
                "total_jobs": len(all_jobs),
                "confirmed_count": confirmed_count,
                "message": f"Processed {len(all_jobs)} jobs, confirmed {confirmed_count} addresses"
            })
            
    except Exception as e:
        print(f"Error polling all jobs: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/trigger-agent', methods=['POST'])
@cross_origin()
def trigger_agent():
    """Trigger Shipsy agent for address resolution"""
    
    try:
        data = request.get_json()
        
        # Extract address details from request
        address = data.get('address', '')
        action_type = data.get('action_type', 'call')  # 'call' or 'whatsapp'
        issues = data.get('issues', [])  # Get issues from frontend
        confidence_score = data.get('confidence_score', 0)
        contact_number = data.get('contact_number', '+27812345678')  # Get contact number from frontend
        virtual_number = data.get('virtual_number')  # Get the virtual number (e.g., CRNSEP006)
        
        # Get already validated data from frontend instead of re-processing
        components = data.get('components', {})
        coordinates = data.get('coordinates', {})
        
        # If components/coordinates not sent from frontend, try to fetch from DB
        if not components or not coordinates:
            try:
                # Try to fetch from database using virtual number
                from database import AddressDatabase
                db_fetch = AddressDatabase()
                conn = db_fetch.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT components, coordinates FROM validated_addresses 
                    WHERE virtual_number = ?
                ''', (virtual_number,))
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    components = json.loads(row['components']) if row['components'] else {}
                    coordinates = json.loads(row['coordinates']) if row['coordinates'] else {}
            except Exception as e:
                print(f"Could not fetch from DB: {e}")
                # Last resort: use empty values
                components = {}
                coordinates = {}
        
        # Extract consignment number from virtual_number (remove timestamp if present)
        if virtual_number and '_' in virtual_number:
            # If it has timestamp (e.g., "EQ5498765610_1758724415625"), take only the CN part
            reference_number = virtual_number.split('_')[0]
        else:
            # Use as is if no timestamp, or generate if not provided
            reference_number = virtual_number if virtual_number else str(uuid.uuid4())
        
        # Generate unique 7-character alphanumeric task_id
        def generate_task_id():
            """Generate a unique 7-character alphanumeric string"""
            chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
            return ''.join(random.choice(chars) for _ in range(7))
        
        unique_task_id = generate_task_id()
        
        # Determine the correct API endpoint based on action type
        if action_type == 'whatsapp':
            api_url = "https://agent.shipsy.tech/api/v1/agent/whatsapp/address_resolution/aramexapp/create"
        else:  # voice_call
            api_url = "https://agent.shipsy.tech/api/v1/agent/voice_call/address_resolution/aramexapp/create"
        
        # Build custom_parameters based on action type
        if action_type == 'whatsapp':
            custom_params = {
                "issues": issues,  # Include issues only for WhatsApp
                "task_id": unique_task_id
            }
        else:  # voice_call
            custom_params = {
                "task_id": unique_task_id  # Only task_id for voice calls, no issues
            }
        
        # Use same payload structure for both endpoints
        agent_payload = {
            "customer_phone_number": contact_number,  # Use the contact number from frontend
            "reference_number": reference_number,  # Using virtual number as reference
            "customer_name": "there",  # Generic customer name
            "shipment_description": f"Address Verification - Score: {confidence_score}%",
            "address_details": {
                "address_line_1": address,
                "pincode": components.get('postal_code', ''),
                "city": components.get('city', ''),
                "country": "South Africa",
                "latitude": str(coordinates.get('latitude', '')) if coordinates else '',
                "longitude": str(coordinates.get('longitude', '')) if coordinates else ''
            },
            "preferred_language": "en",
            "status": "",
            "custom_parameters": custom_params
        }
        
        # Print the complete request being sent
        print("\n" + "="*80)
        print(f"SHIPSY API REQUEST - {action_type.upper()}")
        print("="*80)
        print(f"URL: {api_url}")
        print(f"\nHEADERS:")
        print(json.dumps({
            'api-key': 'jsdbfjhsbdfjhsdbfuguwer9238749832kdssi89',
            'Content-Type': 'application/json'
        }, indent=2))
        print(f"\nREQUEST BODY:")
        print(json.dumps(agent_payload, indent=2))
        print("="*80 + "\n")
        
        try:
            # Use API key for both endpoints
            headers = {
                'api-key': 'jsdbfjhsbdfjhsdbfuguwer9238749832kdssi89',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                api_url,
                json=agent_payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200 or response.status_code == 201:
                api_response = response.json()
                
                print("\nSHIPSY API RESPONSE:")
                print(json.dumps(api_response, indent=2))
                print("="*80 + "\n")
                
                # Save agent call to database
                db.save_agent_call({
                    'virtual_number': reference_number,
                    'action_type': action_type,
                    'reference_number': reference_number,
                    'phone_number': contact_number,
                    'issues_sent': issues,
                    'api_response': api_response,
                    'status': 'pending'
                })
                
                return jsonify({
                    "success": True,
                    "message": f"Agent triggered successfully for {action_type}",
                    "reference_number": reference_number,
                    "phone_number": contact_number,
                    "customer_name": "Customer",
                    "action": action_type,
                    "address": address,
                    "issues_sent": issues,
                    "shipsy_response": api_response
                })
            else:
                pass
                return jsonify({
                    "success": False,
                    "error": f"Shipsy API error: {response.status_code}",
                    "details": response.text
                }), response.status_code
                
        except requests.exceptions.Timeout:
            print("Shipsy API timeout")
            return jsonify({
                "success": False,
                "error": "API timeout - please try again"
            }), 504
        except requests.exceptions.RequestException as e:
            print(f"Request error: {str(e)}")
            return jsonify({
                "success": False,
                "error": f"Failed to connect to Shipsy API: {str(e)}"
            }), 503
            
    except Exception as e:
        print(f"Error in trigger_agent: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/addresses/all', methods=['GET'])
@cross_origin()
def get_all_addresses():
    """Get all validated addresses from database"""
    try:
        addresses = db.get_all_addresses()
        return jsonify({
            "success": True,
            "addresses": addresses,
            "total": len(addresses)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/health', methods=['GET'])
@cross_origin()
def health():
    llm_status = "available" if get_llm_validator() else "not configured"
    return jsonify({
        "status": "healthy",
        "llm_validator": llm_status,
        "rule_validator": "available"
    })


@app.route('/api/countries', methods=['GET'])
@cross_origin()
def get_countries():
    """Get list of supported countries for address validation"""
    return jsonify({
        "countries": list_supported_countries(),
        "default": "ZA"
    })


@app.route('/', methods=['GET'])
@cross_origin()
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
            "/api/countries",
            "/health"
        ],
        "supported_countries": ["ZA (South Africa)", "KZ (Kazakhstan)"],
        "validation_mode": "AI-powered (Gemini 2.5 Pro)",
        "llm_status": "available" if get_llm_validator() else "not configured (set GEMINI_API_KEY in .env)"
    })

def background_polling():
    """Background thread to poll for pending confirmations"""
    global polling_active
    while polling_active:
        try:
            # Get all CNs where agent was triggered but no confirmed address yet
            pending = db.get_pending_confirmations()
            
            if pending:
                
                confirmed_count = 0
                for virtual_number in pending:
                    # Try to poll for this address
                    # poll_single_address will only save if updated_address exists
                    if poll_single_address(virtual_number):
                        confirmed_count += 1
                
                pass
                
            # Wait 30 seconds before next poll cycle
            time.sleep(30)
            
        except Exception as e:
            pass
            time.sleep(30)

def start_background_polling():
    """Start the background polling thread"""
    global polling_thread, polling_active
    
    if not polling_thread or not polling_thread.is_alive():
        polling_active = True
        polling_thread = threading.Thread(target=background_polling, daemon=True)
        polling_thread.start()

def stop_background_polling():
    """Stop the background polling thread"""
    global polling_active
    polling_active = False

if __name__ == '__main__':
    # Check for LLM availability on startup
    if get_llm_validator():
        print("✅ LLM validator is available (Gemini 2.5 Pro)")
    else:
        print("⚠️  LLM validator not configured. Set GEMINI_API_KEY in .env file to enable.")
    
    port = int(os.environ.get('PORT', 5000))
    
    # Load virtual numbers on startup
    load_virtual_numbers()
    
    # Start background polling for pending confirmations
    start_background_polling()
    
    app.run(debug=True, host='0.0.0.0', port=port)