"""
LLM-based address validation using Google Gemini - SIMPLIFIED
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
        
        # Use Gemini 2.5 Pro
        self.model = genai.GenerativeModel('gemini-2.5-pro')
    
    def validate_address(self, address: str) -> Dict[str, Any]:
        """
        Validate a single address using LLM
        Simply send to LLM and return the response
        """
        # SA-LogiCheck system prompt
        prompt = f"""
You are "SA-LogiCheck", an expert address-quality assessor for the South African logistics industry.
Your job is to take ONE candidate address (which may be unstructured or partially structured) and decide whether it is *Complete & Logistically Usable*.

Address to validate: {address}

IMPORTANT: If the address contains a city name followed by a province abbreviation (e.g., "Margate, KZN"), extract the city name properly.

────────────────────────────────────────────────────────────
1. NORMALISE
   • Trim extra whitespace, standardise casing (Title Case for names, UPPER for province codes).
   • Expand common abbreviations: "St/Str" → "Street", "Rd" → "Road", "Ave/Av" → "Avenue", "Dr" → "Drive", "Ln" → "Lane", "Ct" → "Court", "Pl" → "Place", "Blvd" → "Boulevard", "Cres" → "Crescent"
   • City abbreviations: "JHB" → "Johannesburg", "PTA" → "Pretoria", "CPT" → "Cape Town", "DBN" → "Durban", "PE" → "Port Elizabeth"
   • "PO Box" → "Post Office Box", "Apt" → "Apartment", "Bldg" → "Building", "Fl" → "Floor", "Ste" → "Suite"
   • Rewrite coordinates to 6-decimal precision if present.

2. VALIDATE COMPONENTS (all must pass unless explicitly "N/A")
   a. Street Number — positive integer or legal stand/erf number.
   b. Street Name — ≥ 3 alphabetic characters, not purely numeric. Valid types: Street, Road, Avenue, Drive, Lane, Crescent, Way, Close, Place, Boulevard, Highway, Freeway.
   c. Suburb/Locality — must be a recognized South African suburb.
   d. Town/City — must be a valid SA city and consistent with suburb.
   e. Province — MUST be exactly one of these 9 provinces or their codes:
      • Eastern Cape (EC)
      • Free State (FS)
      • Gauteng (GP)
      • KwaZulu-Natal (KZN)
      • Limpopo (LP)
      • Mpumalanga (MP)
      • Northern Cape (NC)
      • North West (NW)
      • Western Cape (WC)
   f. Postal Code — MUST be exactly 4 digits and within valid ranges:
      • Eastern Cape: 4700-6499
      • Free State: 9300-9999
      • Gauteng: 1400-1999, 2000-2199
      • KwaZulu-Natal: 2900-4730
      • Limpopo: 0600-0999
      • Mpumalanga: 1000-1399, 2200-2499
      • Northern Cape: 8300-8999
      • North West: 2500-2899
      • Western Cape: 6500-8299, 7000-8099
   g. Latitude/Longitude — MUST be inside SA bounding box (-34.83 ≤ lat ≤ -22.13, 16.45 ≤ lon ≤ 32.89). NEVER return 0,0 as coordinates.
   h. ZoneID/Routing Code — if supplied, must match regex: ^(AGSUB\\d{{11}}|ZISA\\d{{12}})$.

3. SPECIAL ADDRESS TYPES
   • PO Box addresses: Identify and validate PO Box numbers. Format as "PO Box [number], [city], [province], [postal_code]"
   • Unit/Apartment addresses: Extract unit/apartment/flat numbers and include in normalized format as "Unit [number], [street address]..."
   
4. CROSS-CHECK
   • Coordinate ↔ suburb/city distance ≤ 2 km (haversine).
   • Province inferred from coordinates must equal stated province.
   • If postal-code lookup returns multiple suburbs, supplied suburb must appear in list.
   • Reject invalid placeholders like "StreetNo=0" or "PostalCode=0000".
   • PO Box addresses should not have street addresses (they're mutually exclusive).

5. CONFIDENCE SCORING
   • Start at 100, subtract:
       – 25 pts for missing street address (critical for delivery)
       – 20 pts for missing city/town
       – 20 pts for missing province
       – 30 pts for invalid province (not one of the 9 SA provinces)
       – 15 pts for invalid postal code (wrong format or out of range)
       – 10 pts for missing postal code
       – 25 pts for coordinates outside SA bounds
       – 10 pts for PO Box without number
       – 10 pts for coordinate mismatch > 2 km
       – 5 pts for minor formatting issues (abbrev, casing)
   • Clamp to [0,100].
   • Map to qualitative band:
       – 90–100 → "High" (CONFIDENT)
       – 70–89  → "Medium" (LIKELY)
       – 50–69  → "Low" (SUSPICIOUS)
       – <50    → "Unusable" (FAILED)

6. GEOCODING REQUIREMENT (CRITICAL)
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
       - Margate: -30.8631, 30.3686

7. OUTPUT EXACTLY IN THIS JSON SCHEMA
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
        
        print(f"\n{'='*80}")
        print(f"🤖 LLM VALIDATION REQUEST (Gemini 2.5 Pro)")
        print(f"📍 Input Address: {address}")
        print(f"{'='*80}")
        
        try:
            # Generate response from Gemini
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=1.0,
                    top_p=0.95,
                    max_output_tokens=8192,  # Increased to prevent truncation
                )
            )
            
            # Get the response text
            response_text = response.text.strip()
            
            print(f"\n📝 LLM Response:")
            print(response_text)
            print(f"{'='*80}\n")
            
            # Clean up response if it has markdown code blocks
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()
            
            # Parse JSON response
            result = json.loads(response_text)
            
            # Transform to match our backend format
            return self._transform_response(result, address)
            
        except Exception as e:
            print(f"Error calling LLM: {e}")
            # Return error response
            return {
                'original_address': address,
                'normalized_address': address,
                'is_valid': False,
                'confidence_score': 0,
                'confidence_level': 'FAILED',
                'components': {},
                'coordinates': {'latitude': -28.4793, 'longitude': 24.6727},
                'issues': [f'LLM Error: {str(e)}'],
                'suggestions': ['Please try again'],
                'validation_method': 'LLM',
                'llm_model': 'gemini-2.5-pro',
                'error': True
            }
    
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
            'Unusable': 'FAILED'
        }
        
        confidence_level = band_to_level.get(confidence.get('band', 'Low'), 'SUSPICIOUS')
        confidence_score = confidence.get('score', 50)
        
        # Build components dictionary
        components = {}
        if fields.get('streetNumber'):
            components['street_no'] = str(fields.get('streetNumber'))
        if fields.get('streetName'):
            components['street'] = fields.get('streetName')
            components['street_address'] = f"{fields.get('streetNumber', '')} {fields.get('streetName', '')}".strip()
        if fields.get('suburb'):
            components['suburb'] = fields.get('suburb')
        if fields.get('city'):
            components['city'] = fields.get('city')
        if fields.get('province'):
            components['province'] = fields.get('province')
        if fields.get('postalCode'):
            components['postal_code'] = fields.get('postalCode')
        
        # Get coordinates from LLM response
        coordinates = {
            'latitude': fields.get('latitude', -28.4793),
            'longitude': fields.get('longitude', 24.6727)
        }
        
        return {
            'original_address': original_address,
            'normalized_address': llm_result.get('normalizedAddress', original_address),
            'is_valid': llm_result.get('completeness', 'Incomplete') == 'Complete',
            'confidence_score': confidence_score,
            'confidence_level': confidence_level,
            'components': components,
            'coordinates': coordinates,
            'issues': llm_result.get('issues', []),
            'suggestions': llm_result.get('recommendedFixes', []),
            'validation_method': 'LLM',
            'llm_model': 'gemini-2.5-pro'
        }