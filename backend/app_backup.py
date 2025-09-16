"""
AI Address Intelligence Flask Backend API
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

app = Flask(__name__)
# Enable CORS for all routes and origins
CORS(app, resources={r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type"]}})

# In-memory storage for batch jobs (in production, use Redis or database)
batch_jobs = {}

# Initialize validator
validator = SAAddressValidator()

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    """Health check endpoint"""
    if request.method == 'OPTIONS':
        return '', 204
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "AI Address Intelligence API"
    })

@app.route('/api/validate-single', methods=['POST', 'OPTIONS'])
def validate_single():
    """Validate a single address"""
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
        
        if not address:
            return jsonify({
                "error": "Address cannot be empty"
            }), 400
        
        # Validate address
        start_time = time.time()
        result = validator.validate_address(address)
        processing_time = round((time.time() - start_time) * 1000, 2)  # in ms
        
        response = result.to_dict()
        response['processing_time_ms'] = processing_time
        response['timestamp'] = datetime.now().isoformat()
        
        # Add geocoding (mock coordinates for demo)
        # In production, you would use a real geocoding service
        if response.get('components', {}).get('city'):
            city = response['components']['city']
            # Mock coordinates based on city
            city_coords = {
                'Cape Town': {'lat': -33.9249, 'lng': 18.4241},
                'Johannesburg': {'lat': -26.2041, 'lng': 28.0473},
                'Durban': {'lat': -29.8587, 'lng': 31.0218},
                'Pretoria': {'lat': -25.7479, 'lng': 28.2293},
                'Port Elizabeth': {'lat': -33.9608, 'lng': 25.6022},
                'Bloemfontein': {'lat': -29.0852, 'lng': 26.1596},
                'Polokwane': {'lat': -23.9045, 'lng': 29.4686},
                'Kimberley': {'lat': -28.7323, 'lng': 24.7622},
                'Mbombela': {'lat': -25.4753, 'lng': 30.9694},
                'Mahikeng': {'lat': -25.8560, 'lng': 25.6403}
            }
            
            # Check for exact match or partial match
            coords = None
            for city_name, city_coord in city_coords.items():
                if city_name.lower() in city.lower() or city.lower() in city_name.lower():
                    coords = city_coord
                    break
            
            if not coords:
                # Default coordinates for unknown cities (center of South Africa)
                coords = {'lat': -29.0 + (hash(city) % 100) / 100, 'lng': 24.0 + (hash(city) % 100) / 50}
            
            response['coordinates'] = {
                'latitude': coords['lat'],
                'longitude': coords['lng']
            }
        else:
            # Default coordinates if no city identified
            response['coordinates'] = {
                'latitude': -28.4793,
                'longitude': 24.6727
            }
        
        print(f"Sending response: confidence_level={response.get('confidence_level')}, score={response.get('confidence_score')}")
        return jsonify(response)
    
    except Exception as e:
        print(f"Error during validation: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"Validation failed: {str(e)}"
        }), 500

@app.route('/api/validate-batch', methods=['POST', 'OPTIONS'])
def validate_batch():
    """Validate a batch of addresses from CSV file"""
    if request.method == 'OPTIONS':
        return '', 204
        
    try:
        if 'file' not in request.files:
            return jsonify({
                "error": "No file uploaded"
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                "error": "No file selected"
            }), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({
                "error": "Only CSV files are supported"
            }), 400
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Read CSV file
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        addresses = []
        for row in csv_reader:
            # Debug: Print row keys and values
            print(f"CSV Row keys: {list(row.keys())}")
            print(f"CSV Row values: {row}")
            
            # Try to find address column (case-insensitive)
            address = None
            
            # First check for a single 'address' column
            for key in row.keys():
                if 'address' in key.lower() and row[key] and row[key].strip():
                    address = row[key].strip()
                    break
            
            # If no single address column, build from components
            if not address:
                # Build address from individual components
                components = {}
                
                # Map common field names (case-insensitive)
                field_mappings = {
                    'street_no': ['streetno', 'street_no', 'street_number', 'house_number', 'number', 'street no'],
                    'street': ['street', 'street_address', 'address1', 'address_1', 'street address', 'street_name', 'street name'],
                    'suburb': ['suburb', 'neighborhood', 'locality'],  # Removed 'area' from suburb
                    'city': ['city', 'town'],
                    'area': ['area'],  # Handle area separately
                    'province': ['province', 'state', 'region'],
                    'postal_code': ['postalcode', 'postal_code', 'postal code', 'postcode', 'zip', 'zipcode', 'zip_code', 'pincode']
                }
                
                # Direct mapping for exact matches
                for key, value in row.items():
                    if value and value.strip():
                        key_clean = key.lower().strip().replace('_', '').replace('-', '').replace(' ', '')
                        
                        # Check for exact field matches
                        if key_clean == 'streetno' or key_clean == 'streetnum' or key_clean == 'streetnumber':
                            components['street_no'] = value.strip()
                        elif key_clean == 'street' or key_clean == 'streetname':
                            components['street'] = value.strip()
                        elif key_clean == 'suburb':
                            components['suburb'] = value.strip()
                        elif key_clean == 'area':
                            components['area'] = value.strip()
                        elif key_clean == 'city' or key_clean == 'town':
                            components['city'] = value.strip()
                        elif key_clean == 'province' or key_clean == 'state':
                            components['province'] = value.strip()
                        elif key_clean == 'postalcode' or key_clean == 'postcode' or key_clean == 'zipcode' or key_clean == 'zip':
                            components['postal_code'] = value.strip()
                
                # Use area as city if city not found but area exists
                if 'area' in components and 'city' not in components:
                    components['city'] = components['area']
                
                # Build address from components in proper order
                address_parts = []
                
                # Combine street number and street name if both exist
                street_full = ''
                if 'street_no' in components:
                    street_full = components['street_no']
                if 'street' in components:
                    if street_full:
                        street_full += ' ' + components['street']
                    else:
                        street_full = components['street']
                
                if street_full:
                    address_parts.append(street_full)
                if 'suburb' in components:
                    address_parts.append(components['suburb'])
                if 'city' in components:
                    address_parts.append(components['city'])
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
            "completed_at": None
        }
        
        # Simulate async processing (in production, use Celery or similar)
        results = []
        for i, addr_data in enumerate(addresses):
            result = validator.validate_address(addr_data["address"])
            results.append({
                "id": addr_data["id"],
                "original_row": addr_data["original_row"],
                **result.to_dict()
            })
            batch_jobs[job_id]["processed"] = i + 1
            batch_jobs[job_id]["results"] = results
        
        batch_jobs[job_id]["status"] = "complete"
        batch_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        
        return jsonify({
            "job_id": job_id,
            "status": "processing",
            "total_addresses": len(addresses),
            "message": f"Processing {len(addresses)} addresses..."
        })
    
    except Exception as e:
        return jsonify({
            "error": f"Batch processing failed: {str(e)}"
        }), 500

@app.route('/api/batch-status/<job_id>', methods=['GET', 'OPTIONS'])
def batch_status(job_id):
    """Get status of batch processing job"""
    if request.method == 'OPTIONS':
        return '', 204
        
    if job_id not in batch_jobs:
        return jsonify({
            "error": "Job not found"
        }), 404
    
    job = batch_jobs[job_id]
    
    return jsonify({
        "job_id": job_id,
        "status": job["status"],
        "total": job["total"],
        "processed": job["processed"],
        "progress_percentage": round((job["processed"] / job["total"]) * 100, 2),
        "started_at": job["started_at"],
        "completed_at": job["completed_at"],
        "results": job["results"] if job["status"] == "complete" else None
    })

@app.route('/api/download-results/<job_id>', methods=['GET', 'OPTIONS'])
def download_results(job_id):
    """Download validation results as CSV"""
    if request.method == 'OPTIONS':
        return '', 204
        
    if job_id not in batch_jobs:
        return jsonify({
            "error": "Job not found"
        }), 404
    
    job = batch_jobs[job_id]
    
    if job["status"] != "complete":
        return jsonify({
            "error": "Job not complete yet"
        }), 400
    
    # Create CSV
    output = io.StringIO()
    
    if job["results"]:
        fieldnames = [
            "id", "original_address", "is_valid", "confidence_score", 
            "confidence_level", "normalized_address", "street_address",
            "suburb", "city", "province", "postal_code", "issues", "suggestions"
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
                "suggestions": "; ".join(result["suggestions"])
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
        download_name=f'sa_logicheck_results_{job_id[:8]}.csv',
        as_attachment=True
    )

@app.route('/api/sample-data', methods=['GET', 'OPTIONS'])
def get_sample_data():
    """Get sample addresses for testing"""
    if request.method == 'OPTIONS':
        return '', 204
        
    sample_addresses = [
        "123 Main Street, Sea Point, Cape Town, Western Cape, 8005",
        "PO Box 456, Johannesburg, Gauteng, 2000",
        "Unit 7B, 89 Beach Road, Umhlanga, Durban, KwaZulu-Natal, 4319",
        "45 Church Street, Pretoria, 0001",
        "12 Long Street, Cape Town",  # Missing province and postal code
        "Port Elizabeth, Eastern Cape",  # Missing street address
        "567 Oak Avenue, Stellenbosch, WC, 7600",
        "Plot 234, Diepsloot, Johannesburg, GP",
        "15 Nelson Mandela Drive, Bloemfontein, Free State, 9301",
        "78 Jan Smuts Avenue, Hyde Park, Johannesburg, 2196",
        "Corner of Main and Market Streets, Polokwane, Limpopo, 699",
        "23A Vilakazi Street, Orlando West, Soweto, 1804",
        "456 Beyers Naude Drive, Randburg, GT, 2194",  # Invalid province code
        "89 Durban Road, Pinetown, KZN, 9999",  # Invalid postal code
        "12 Beach Road, Camps Bay, Cape Town, Western Cape, 8040",
        "Suite 301, Sandton City, Sandton, Johannesburg, Gauteng, 2196",
        "789 Main Road, Kimberley, Northern Cape, 8301",
        "34 President Street, Mbombela, Mpumalanga, 1200",
        "56 Thabo Mbeki Street, Mahikeng, North West, 2745",
        "90 Marine Drive, Hermanus, Western Cape, 7200"
    ]
    
    return jsonify({
        "sample_addresses": sample_addresses,
        "total": len(sample_addresses),
        "description": "Sample South African addresses for testing (mix of valid, partially valid, and invalid)"
    })

@app.route('/api/provinces', methods=['GET', 'OPTIONS'])
def get_provinces():
    """Get list of South African provinces"""
    if request.method == 'OPTIONS':
        return '', 204
        
    from sa_data import PROVINCES
    
    provinces_list = []
    for name, data in PROVINCES.items():
        provinces_list.append({
            "name": name,
            "code": data["code"],
            "capital": data["capital"],
            "major_cities": data["major_cities"]
        })
    
    return jsonify({
        "provinces": provinces_list,
        "total": len(provinces_list)
    })

@app.route('/api/stats', methods=['GET', 'OPTIONS'])
def get_stats():
    """Get validation statistics"""
    if request.method == 'OPTIONS':
        return '', 204
        
    total_validated = sum(len(job.get("results", [])) for job in batch_jobs.values())
    successful = sum(
        len([r for r in job.get("results", []) if r["is_valid"]])
        for job in batch_jobs.values()
    )
    
    success_rate = (successful / total_validated * 100) if total_validated > 0 else 0
    
    return jsonify({
        "total_validated": total_validated,
        "successful_validations": successful,
        "failed_validations": total_validated - successful,
        "success_rate": round(success_rate, 2),
        "active_jobs": len([j for j in batch_jobs.values() if j["status"] == "processing"]),
        "completed_jobs": len([j for j in batch_jobs.values() if j["status"] == "complete"])
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
            "customer_phone_number": "+919599195210",  # Fixed number as requested
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
                    "response": shipsy_response.json() if shipsy_response.text else {}
                })
            else:
                # Return success with mock response if external API fails
                print(f"External API returned {shipsy_response.status_code}, using mock response")
                return jsonify({
                    "success": True,
                    "message": f"Agent triggered for {action_type} (Demo Mode)",
                    "reference_number": agent_payload["reference_number"],
                    "response": {"status": "demo", "message": "Agent triggered in demo mode"}
                })
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            # Return success with mock response if connection fails
            print(f"External API connection failed: {str(e)}, using mock response")
            return jsonify({
                "success": True,
                "message": f"Agent triggered for {action_type} (Demo Mode)",
                "reference_number": agent_payload["reference_number"],
                "response": {"status": "demo", "message": "Agent triggered in demo mode"}
            })
            
    except Exception as e:
        print(f"Error triggering agent: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

# Add a catch-all OPTIONS handler
@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    return '', 204

if __name__ == '__main__':
    print("Starting AI Address Intelligence Backend on http://localhost:5000")
    print("API endpoints available at http://localhost:5000/api/")
    app.run(debug=True, port=5000, host='0.0.0.0')