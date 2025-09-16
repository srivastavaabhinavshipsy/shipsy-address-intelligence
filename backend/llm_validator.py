"""
LLM-based address validation using Google Gemini with geocoding
"""
import os
import json
import google.generativeai as genai
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMAddressValidator:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the LLM validator with Gemini API"""
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required. Please set it in .env file or pass it directly.")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Use Gemini 1.5 Pro for latest capabilities
        self.model = genai.GenerativeModel('gemini-1.5-pro')
    
    def validate_address(self, address: str) -> Dict[str, Any]:
        """
        Validate a single address using LLM with geocoding
        
        Args:
            address: The address string to validate
            
        Returns:
            Dictionary with validation results including coordinates
        """
        try:
            # SA-LogiCheck system prompt with geocoding emphasis
            prompt = f"""
You are "SA-LogiCheck", an expert address-quality assessor for the South African logistics industry.
Your job is to take ONE candidate address (which may be unstructured or partially structured) and decide whether it is *Complete & Logistically Usable*.

Address to validate: {address}

────────────────────────────────────────────────────────────
1. NORMALISE
   • Trim extra whitespace, standardise casing (Title Case for names, UPPER for province codes).
   • Expand common abbreviations: "St" → "Street", "Rd" → "Road", "Ave/Av" → "Avenue", "PO Box" → "Post Office Box".
   • Rewrite coordinates to 6-decimal precision if present.

2. VALIDATE COMPONENTS (all must pass unless explicitly "N/A")
   a. Street Number — positive integer or legal stand/erf number.
   b. Street Name — ≥ 3 alphabetic characters, not purely numeric.
   c. Suburb/Locality — must exist in the South African Post Office (SAPO) database.
   d. Town/City — must exist in SAPO database and be consistent with suburb.
   e. Province — one of 9 official names or ISO-3166-2 code (e.g. "WC", "Western Cape").
   f. Postal Code — 4 digits, must match suburb–city pair per SAPO lookup.
   g. Latitude/Longitude — must be inside SA bounding box (-35.0 ≤ lat ≤ -21.0, 16.0 ≤ lon ≤ 33.0). NEVER return 0,0 as coordinates.
   h. ZoneID/Routing Code — if supplied, must match regex: ^(AGSUB\\d{11}|ZISA\\d{12})$.

3. CROSS-CHECK
   • Coordinate ↔ suburb/city distance ≤ 2 km (haversine).
   • Province inferred from coordinates must equal stated province.
   • If postal-code lookup returns multiple suburbs, supplied suburb must appear in list.
   • Reject invalid placeholders like "StreetNo=0" or "PostalCode=0000".

4. CONFIDENCE SCORING
   • Start at 100, subtract:
       – 10 pts per missing mandatory field
       – 10 pts for coordinate mismatch > 2 km
       – 20 pts for postal-code mismatch
       – 5 pts for minor formatting issues (abbrev, casing)
   • Clamp to [0,100].
   • Map to qualitative band:
       – 90–100 → "High"
       – 70–89  → "Medium"
       – 50–69  → "Low"
       – <50    → "Unusable"

5. GEOCODING REQUIREMENT (CRITICAL)
   • You MUST ALWAYS provide latitude and longitude.
   • Use your knowledge of South African geography to provide the most accurate coordinates possible.
   • If exact address coordinates unknown → use suburb/area coordinates.
   • If suburb unknown → use city coordinates.
   • Known city coordinates (reference only):
       - Cape Town: -33.9249, 18.4241
       - Johannesburg: -26.2041, 28.0473
       - Durban: -29.8587, 31.0218
       - Pretoria: -25.7479, 28.2293
       - Port Elizabeth/Gqeberha: -33.9608, 25.6022
       - Bloemfontein: -29.0852, 26.1596
       - East London: -33.0153, 27.9116
       - Polokwane: -23.9045, 29.4686
       - Kimberley: -28.7323, 24.7622
       - Lydenburg: -25.0947, 30.4528

6. OUTPUT EXACTLY IN THIS JSON SCHEMA
{{
  "normalizedAddress": "<string>",
  "fields": {{
    "streetNumber": <int|null>,
    "streetName": "<string|null>",
    "suburb": "<string|null>",
    "city": "<string|null>",
    "province": "<string|null>",
    "postalCode": "<string|null>",
    "latitude": <float|null>,
    "longitude": <float|null>,
    "zoneId": "<string|null>"
  }},
  "completeness": "<Complete|Incomplete>",
  "confidence": {{
    "score": <0-100>,
    "band": "<High|Medium|Low|Unusable>"
  }},
  "issues": [
    "<string>", "..."
  ],
  "recommendedFixes": [
    "<string>", "..."
  ]
}}

DECISION RULE
• Return completeness = "Complete" ONLY if:
   – All mandatory fields are present and valid, AND
   – confidence.band is "High" or "Medium".
• Otherwise return "Incomplete", listing issues and actionable fixes.

STYLE & BEHAVIOUR
• Never hallucinate data. If unsure, leave field null and flag in issues (except coordinates, which are always required).
• Be concise; no commentary outside the JSON.
• Follow South African POPIA and GDPR principles: do not store or expose personal info beyond what the user supplied.
• Return ONLY the JSON object, no other text.
"""
            
            # Generate response from Gemini
            print(f"\n{'='*80}")
            print(f"🤖 LLM VALIDATION REQUEST (Gemini 1.5 Pro)")
            print(f"{'='*80}")
            print(f"📍 Input Address: {address}")
            print(f"{'='*80}")
            
            # Direct LLM call without safety filters
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=genai.GenerationConfig(
                        temperature=0.1,  # Low temperature for consistent results
                        max_output_tokens=1000,
                    )
                )
                print(f"✅ LLM Response received successfully")
            except Exception as llm_error:
                print(f"❌ LLM Error: {llm_error}")
                raise llm_error
            
            # Check if response was blocked or empty
            if not response.parts or not response.text:
                print(f"\n⚠️ No response from LLM. Using fallback parsing.")
                # Simple fallback - parse what we can from the address
                city = self._extract_city_from_address(address)
                coords = self._get_default_coordinates(city)
                
                # Parse address components
                parts = address.split(',')
                normalized = ', '.join(p.strip() for p in parts)
                
                # Extract province if present
                province_map = {
                    'western cape': 'Western Cape', 'wc': 'Western Cape',
                    'eastern cape': 'Eastern Cape', 'ec': 'Eastern Cape',
                    'northern cape': 'Northern Cape', 'nc': 'Northern Cape',
                    'free state': 'Free State', 'fs': 'Free State',
                    'kwazulu-natal': 'KwaZulu-Natal', 'kzn': 'KwaZulu-Natal',
                    'north west': 'North West', 'nw': 'North West',
                    'gauteng': 'Gauteng', 'gp': 'Gauteng',
                    'mpumalanga': 'Mpumalanga', 'mp': 'Mpumalanga',
                    'limpopo': 'Limpopo', 'lp': 'Limpopo'
                }
                
                address_lower = address.lower()
                province = None
                for key, val in province_map.items():
                    if key in address_lower:
                        province = val
                        break
                
                # Extract postal code (4 digits)
                import re
                postal_match = re.search(r'\b\d{4}\b', address)
                postal_code = postal_match.group(0) if postal_match else None
                
                # Build structured response with specific missing components
                issues = []
                recommendedFixes = []
                
                # Check what's missing and provide specific feedback
                if not city:
                    issues.append("City/town name is missing")
                    recommendedFixes.append("Add the city name (e.g., Cape Town, Johannesburg)")
                
                if not province:
                    issues.append("Province is missing")
                    recommendedFixes.append("Add the province (e.g., Western Cape, Gauteng)")
                
                if not postal_code:
                    issues.append("Postal code is missing")
                    recommendedFixes.append("Add the 4-digit postal code")
                
                # Always flag missing street details
                issues.append("Street number is missing")
                issues.append("Street name is missing")
                issues.append("Suburb/area is missing")
                
                recommendedFixes.append("Add the street number (e.g., 123)")
                recommendedFixes.append("Add the street name (e.g., Main Road)")
                recommendedFixes.append("Add the suburb or area name")
                
                # Calculate score based on what we found
                score = 100
                score -= 20 if not city else 0
                score -= 20 if not province else 0
                score -= 10 if not postal_code else 0
                score -= 30  # For missing street details
                score = max(score, 0)
                
                fallback_response = {
                    "normalizedAddress": normalized,
                    "fields": {
                        "streetNumber": None,
                        "streetName": None,
                        "suburb": None,
                        "city": city if city else None,
                        "province": province,
                        "postalCode": postal_code,
                        "latitude": coords['latitude'],
                        "longitude": coords['longitude'],
                        "zoneId": None
                    },
                    "completeness": "Incomplete",
                    "confidence": {
                        "score": score,
                        "band": "High" if score >= 90 else "Medium" if score >= 70 else "Low" if score >= 50 else "Unusable"
                    },
                    "issues": issues,
                    "recommendedFixes": recommendedFixes
                }
                
                response_text = json.dumps(fallback_response)
                # Create a mock response object
                class MockResponse:
                    def __init__(self, text):
                        self.text = text
                        self.parts = [True]
                
                response = MockResponse(response_text)
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            print(f"\n📝 LLM RAW RESPONSE:")
            print(f"{'-'*80}")
            print(response_text)
            print(f"{'-'*80}")
            
            # Clean up response if it has markdown code blocks
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            # Parse JSON response
            result = json.loads(response_text)
            
            print(f"\n✅ LLM PARSED RESULT:")
            print(f"{'-'*80}")
            print(f"Normalized: {result.get('normalizedAddress', 'N/A')}")
            print(f"Completeness: {result.get('completeness', 'N/A')}")
            print(f"Confidence: {result.get('confidence', {}).get('score', 'N/A')}% ({result.get('confidence', {}).get('band', 'N/A')})")
            print(f"Coordinates: ({result.get('fields', {}).get('latitude', 'N/A')}, {result.get('fields', {}).get('longitude', 'N/A')})")
            print(f"Issues: {', '.join(result.get('issues', [])) if result.get('issues') else 'None'}")
            print(f"Recommendations: {', '.join(result.get('recommendedFixes', [])) if result.get('recommendedFixes') else 'None'}")
            print(f"{'='*80}\n")
            
            # Transform to match our backend format
            return self._transform_response(result, address)
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            if 'response_text' in locals():
                print(f"Raw response: {response_text}")
                # Try to extract city from incomplete response
                city = ''
                if '"city":' in response_text:
                    try:
                        city_part = response_text.split('"city":')[1].split(',')[0].strip().strip('"')
                        city = city_part.lower()
                        print(f"Extracted city from partial response: {city}")
                    except:
                        pass
                
                if not city:
                    city = self._extract_city_from_address(address)
                
                return {
                    'original_address': address,
                    'normalized_address': address,
                    'is_valid': False,
                    'confidence_score': 50,  # Partial validation
                    'confidence_level': 'SUSPICIOUS',
                    'components': {'city': city} if city else {},
                    'coordinates': self._get_default_coordinates(city),
                    'issues': [x for x in [
                        'Street number is missing',
                        'Street name is missing', 
                        'Suburb is missing',
                        'Province is missing' if 'province' not in components else None,
                        'Postal code is missing' if 'postal_code' not in components else None
                    ] if x],
                    'suggestions': [x for x in [
                        'Add the street number (e.g., 123)',
                        'Add the street name (e.g., Main Road)',
                        'Add the suburb or area name',
                        'Add the province (e.g., Western Cape, Gauteng)' if 'province' not in components else None,
                        'Add the 4-digit postal code' if 'postal_code' not in components else None
                    ] if x],
                    'validation_method': 'LLM (partial)',
                    'llm_model': 'gemini-1.5-pro'
                }
            return self._error_response(address, "Invalid JSON response from LLM")
        except (AttributeError, ValueError) as e:
            error_msg = str(e)
            if 'response.text' in error_msg or 'finish_reason' in error_msg:
                print(f"\n⚠️ LLM Response Blocked: Generating structured fallback response")
                # Return a well-structured fallback response
                city = self._extract_city_from_address(address)
                coords = self._get_default_coordinates(city)
                
                # Parse what we can from the address
                parts = address.split(',')
                normalized = ', '.join(p.strip() for p in parts)
                
                # Extract province if present
                province_map = {
                    'western cape': 'Western Cape', 'wc': 'Western Cape',
                    'eastern cape': 'Eastern Cape', 'ec': 'Eastern Cape',
                    'northern cape': 'Northern Cape', 'nc': 'Northern Cape',
                    'free state': 'Free State', 'fs': 'Free State',
                    'kwazulu-natal': 'KwaZulu-Natal', 'kzn': 'KwaZulu-Natal',
                    'north west': 'North West', 'nw': 'North West',
                    'gauteng': 'Gauteng', 'gp': 'Gauteng',
                    'mpumalanga': 'Mpumalanga', 'mp': 'Mpumalanga',
                    'limpopo': 'Limpopo', 'lp': 'Limpopo'
                }
                
                address_lower = address.lower()
                province = None
                for key, val in province_map.items():
                    if key in address_lower:
                        province = val
                        break
                
                # Extract postal code
                import re
                postal_match = re.search(r'\b\d{4}\b', address)
                postal_code = postal_match.group(0) if postal_match else None
                
                # Build components
                components = {'city': city} if city else {}
                if province:
                    components['province'] = province
                if postal_code:
                    components['postal_code'] = postal_code
                
                # Build specific issues and suggestions
                issues = []
                suggestions = []
                
                if not city:
                    issues.append("City/town name is missing")
                    suggestions.append("Add the city name (e.g., Cape Town, Johannesburg)")
                
                if not province:
                    issues.append("Province is missing")
                    suggestions.append("Add the province (e.g., Western Cape, Gauteng)")
                
                if not postal_code:
                    issues.append("Postal code is missing")
                    suggestions.append("Add the 4-digit postal code")
                
                # Always flag missing street details since we can't extract them
                issues.extend([
                    "Street number is missing",
                    "Street name is missing",
                    "Suburb/area is missing"
                ])
                
                suggestions.extend([
                    "Add the street number (e.g., 123)",
                    "Add the street name (e.g., Main Road)",
                    "Add the suburb or area name"
                ])
                
                return {
                    'original_address': address,
                    'normalized_address': normalized,
                    'is_valid': bool(city and province),  # Valid if we have at least city and province
                    'confidence_score': 65 if (city and province) else 40,
                    'confidence_level': 'LOW' if (city and province) else 'SUSPICIOUS',
                    'components': components,
                    'coordinates': coords,
                    'issues': issues,
                    'suggestions': suggestions,
                    'validation_method': 'LLM (with fallback parsing)',
                    'llm_model': 'gemini-1.5-pro'
                }
            else:
                print(f"LLM validation error: {e}")
                return self._error_response(address, str(e))
        except Exception as e:
            print(f"LLM validation error: {e}")
            import traceback
            traceback.print_exc()
            return self._error_response(address, str(e))
    
    def validate_batch(self, addresses: list) -> list:
        """
        Validate multiple addresses
        
        Args:
            addresses: List of address strings
            
        Returns:
            List of validation results
        """
        results = []
        for address in addresses:
            result = self.validate_address(address)
            results.append(result)
        return results
    
    def _transform_response(self, llm_result: Dict, original_address: str) -> Dict[str, Any]:
        """Transform LLM response to match our backend format"""
        
        # Extract fields with safe defaults
        fields = llm_result.get('fields', {})
        confidence = llm_result.get('confidence', {})
        
        # Map confidence band to our confidence level
        band_to_level = {
            'High': 'CONFIDENT',
            'Medium': 'LIKELY',
            'Low': 'SUSPICIOUS',
            'Unusable': 'INVALID'
        }
        
        confidence_level = band_to_level.get(confidence.get('band', 'Low'), 'SUSPICIOUS')
        confidence_score = confidence.get('score', 50)
        
        # Build components dictionary
        components = {
            'street_no': str(fields.get('streetNumber', '')) if fields.get('streetNumber') else '',
            'street': fields.get('streetName', ''),
            'street_address': f"{fields.get('streetNumber', '')} {fields.get('streetName', '')}".strip() if fields.get('streetName') else '',
            'suburb': fields.get('suburb', ''),
            'city': fields.get('city', ''),
            'province': fields.get('province', ''),
            'postal_code': fields.get('postalCode', ''),
            'area': fields.get('area', '')
        }
        
        # Remove empty values
        components = {k: v for k, v in components.items() if v}
        
        # Build coordinates - ensure they're always present for map display
        coordinates = None
        if fields.get('latitude') is not None and fields.get('longitude') is not None:
            try:
                lat = float(fields.get('latitude'))
                lon = float(fields.get('longitude'))
                # Reject 0,0 coordinates and validate South African bounds
                if lat == 0 and lon == 0:
                    coordinates = self._get_default_coordinates(fields.get('city', 'lydenburg'))
                    print(f"📍 Rejected 0,0 coordinates, using city default")
                elif -35 <= lat <= -22 and 16 <= lon <= 33:
                    coordinates = {'latitude': lat, 'longitude': lon}
                    print(f"📍 Using LLM coordinates: ({lat}, {lon})")
                else:
                    # Outside SA bounds, use city default
                    coordinates = self._get_default_coordinates(fields.get('city', ''))
                    print(f"📍 Coordinates outside SA bounds, using city default")
            except (ValueError, TypeError):
                coordinates = self._get_default_coordinates(fields.get('city', ''))
                print(f"📍 Invalid coordinates from LLM, using city default")
        else:
            # No coordinates from LLM, use city defaults
            coordinates = self._get_default_coordinates(fields.get('city', ''))
            print(f"📍 No coordinates from LLM, using city default")
        
        return {
            'original_address': original_address,
            'normalized_address': llm_result.get('normalizedAddress', original_address),
            'is_valid': llm_result.get('completeness', 'Incomplete') == 'Complete',
            'confidence_score': confidence_score,
            'confidence_level': confidence_level,
            'components': components,
            'coordinates': coordinates,  # Always include coordinates
            'issues': llm_result.get('issues', []),
            'suggestions': llm_result.get('recommendedFixes', []),
            'validation_method': 'LLM',
            'llm_model': 'gemini-1.5-pro'
        }
    
    def _error_response(self, address: str, error_msg: str) -> Dict[str, Any]:
        """Generate an error response with specific feedback"""
        # Try to extract what we can from the address
        city = self._extract_city_from_address(address)
        coords = self._get_default_coordinates(city)
        
        # Extract province if present
        province_map = {
            'western cape': 'Western Cape', 'wc': 'Western Cape',
            'eastern cape': 'Eastern Cape', 'ec': 'Eastern Cape',
            'northern cape': 'Northern Cape', 'nc': 'Northern Cape',
            'free state': 'Free State', 'fs': 'Free State',
            'kwazulu-natal': 'KwaZulu-Natal', 'kzn': 'KwaZulu-Natal',
            'north west': 'North West', 'nw': 'North West',
            'gauteng': 'Gauteng', 'gp': 'Gauteng',
            'mpumalanga': 'Mpumalanga', 'mp': 'Mpumalanga',
            'limpopo': 'Limpopo', 'lp': 'Limpopo'
        }
        
        address_lower = address.lower()
        province = None
        for key, val in province_map.items():
            if key in address_lower:
                province = val
                break
        
        # Build specific feedback
        issues = []
        suggestions = []
        
        # Always provide specific missing component feedback
        if not city:
            issues.append("City/town name is missing")
            suggestions.append("Add the city name (e.g., Cape Town, Johannesburg)")
        
        if not province:
            issues.append("Province is missing")
            suggestions.append("Add the province (e.g., Western Cape, Gauteng)")
        
        # Always flag missing street details
        issues.extend([
            "Street number is missing",
            "Street name is missing",
            "Suburb/area is missing",
            "Postal code is missing"
        ])
        
        suggestions.extend([
            "Add the street number (e.g., 123)",
            "Add the street name (e.g., Main Road)",
            "Add the suburb or area name",
            "Add the 4-digit postal code"
        ])
        
        components = {}
        if city:
            components['city'] = city
        if province:
            components['province'] = province
        
        return {
            'original_address': address,
            'normalized_address': address,
            'is_valid': False,
            'confidence_score': 20 if (city or province) else 0,
            'confidence_level': 'INVALID',
            'components': components,
            'coordinates': coords,
            'issues': issues,
            'suggestions': suggestions,
            'validation_method': 'LLM',
            'llm_model': 'gemini-1.5-pro',
            'error': True
        }
    
    def _get_default_coordinates(self, city: str) -> Dict[str, float]:
        """Get default coordinates based on city name"""
        city_coords = {
            'cape town': {'latitude': -33.9249, 'longitude': 18.4241},
            'johannesburg': {'latitude': -26.2041, 'longitude': 28.0473},
            'durban': {'latitude': -29.8587, 'longitude': 31.0218},
            'pretoria': {'latitude': -25.7479, 'longitude': 28.2293},
            'port elizabeth': {'latitude': -33.9608, 'longitude': 25.6022},
            'gqeberha': {'latitude': -33.9608, 'longitude': 25.6022},
            'bloemfontein': {'latitude': -29.0852, 'longitude': 26.1596},
            'east london': {'latitude': -33.0153, 'longitude': 27.9116},
            'polokwane': {'latitude': -23.9045, 'longitude': 29.4686},
            'kimberley': {'latitude': -28.7323, 'longitude': 24.7622},
            'stellenbosch': {'latitude': -33.9321, 'longitude': 18.8602},
            'hermanus': {'latitude': -34.4187, 'longitude': 19.2345},
            'mbombela': {'latitude': -25.4753, 'longitude': 30.9694},
            'nelspruit': {'latitude': -25.4753, 'longitude': 30.9694},
            'mahikeng': {'latitude': -25.8560, 'longitude': 25.6403},
            'soweto': {'latitude': -26.2678, 'longitude': 27.8585},
            'sandton': {'latitude': -26.1076, 'longitude': 28.0567},
            'umhlanga': {'latitude': -29.7263, 'longitude': 31.0809},
            'camps bay': {'latitude': -33.9506, 'longitude': 18.3777},
            'sea point': {'latitude': -33.9149, 'longitude': 18.3995},
            'diepsloot': {'latitude': -25.9330, 'longitude': 28.0128},
            'randburg': {'latitude': -26.0936, 'longitude': 28.0066},
            'pinetown': {'latitude': -29.8149, 'longitude': 30.8717},
            'bellville': {'latitude': -33.9004, 'longitude': 18.6278},
            'mitchells plain': {'latitude': -34.0385, 'longitude': 18.6157},
            'lydenburg': {'latitude': -25.0947, 'longitude': 30.4528}
        }
        
        # Try to find city in the map
        city_lower = city.lower().strip() if city else ''
        for key, coords in city_coords.items():
            if key in city_lower or city_lower in key:
                print(f"📍 Using default coordinates for {key}: {coords}")
                return coords
        
        # Default to center of South Africa if city not found
        print(f"📍 City not found, using South Africa center")
        return {'latitude': -28.4793, 'longitude': 24.6727}
    
    def _extract_city_from_address(self, address: str) -> str:
        """Extract city name from address string"""
        address_lower = address.lower()
        # List of known cities to search for
        cities = [
            'cape town', 'johannesburg', 'durban', 'pretoria', 'port elizabeth',
            'gqeberha', 'bloemfontein', 'east london', 'polokwane', 'kimberley',
            'stellenbosch', 'hermanus', 'mbombela', 'nelspruit', 'mahikeng',
            'soweto', 'sandton', 'umhlanga', 'camps bay', 'sea point',
            'diepsloot', 'randburg', 'pinetown', 'bellville', 'mitchells plain',
            'lydenburg'
        ]
        
        for city in cities:
            if city in address_lower:
                print(f"📍 Extracted city from address: {city}")
                return city
        
        return ''