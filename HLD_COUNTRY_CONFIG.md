# High-Level Design (HLD): Country-Based Prompt and Configuration System

## Overview
This document details all file changes required to implement a country-based configuration system for address validation. The system uses template files with placeholders that are replaced with country-specific configuration data.

## Directory Structure

### New Directories to Create
```
backend/
  ├── templates/
  │   ├── base-prompt.txt                    # NEW: Base prompt template
  │   └── country-rules/
  │       └── south-africa.json              # NEW: SA country configuration
  └── country_config.py                      # NEW: Configuration management module
```

---

## File Changes

### 1. NEW FILE: `backend/templates/base-prompt.txt`

**Purpose**: Store the base prompt template with placeholders `{address}` and `{configurable_rules}`

**Content**: 
```
You are "LogiCheck-Global", an expert address-quality assessor. Your job is to take ONE candidate address (which may be unstructured or partially structured) and decide whether it is Complete & Logistically Usable based on the provided Country Configuration Rules.

Address to validate: {address}
Country Configuration Rules: {configurable_rules}

IMPORTANT: If the address contains a city name followed by a state/province abbreviation (e.g., "City, AB"), extract the city name properly.

1. NORMALISE (Universal)
   • Trim extra whitespace, standardise casing (Title Case for names, UPPER for primary administrative unit codes).
   • Expand common abbreviations using the normalization rules (e.g., "St/Str" → "Street", "JHB" → "Johannesburg").
   • Rewrite coordinates to 6-decimal precision if present.

2. VALIDATE COMPONENTS (Apply Rules)
   All components must pass unless explicitly "N/A".
   
   a. Street Number: Must be a positive integer or legal stand/erf/lot number.
   b. Street Name: ≥ 3 alphabetic characters, not purely numeric. Must align with common street types.
   c. Suburb/Locality: Must be a recognized local administrative unit for the country.
   d. Town/City: Must be a valid city for the country and consistent with suburb.
   e. Province/State (Primary Administrative Unit): MUST be exactly one of the names/codes listed in validation.provinceConfig.list.
   f. Postal Code: MUST match the validation.postalCode.formatRegex and fall within one of the validation.postalCode.ranges.
   g. Latitude/Longitude: MUST be inside the country bounding box defined by validation.coordinateBounds. NEVER return 0,0.
   h. ZoneID/Routing Code: If supplied, must match validation.zoneIdRegex.

3. SPECIAL ADDRESS TYPES (Universal/Rule-Aided)
   • PO Box addresses: Identify and validate PO Box numbers. Format as "Post Office Box [number], [city]..."
   • Unit/Apartment addresses: Extract unit/apartment/flat numbers and include in normalized format.

4. CROSS-CHECK (Universal)
   • Coordinate ↔ suburb/city distance ≤ 2 km (haversine).
   • Primary Administrative Unit (Province/State) inferred from coordinates must equal stated unit.
   • Reject invalid placeholders like "StreetNo=0" or "PostalCode=0000".
   • PO Box addresses should not have street addresses (mutually exclusive).

5. CONFIDENCE SCORING (Universal Score Breakdown)
   • Start at 100, subtract:
       – 25 pts for missing street address (critical for delivery)
       – 20 pts for missing city/town
       – 20 pts for missing Province/State
       – 30 pts for invalid Province/State (not in the configured list)
       – 15 pts for invalid postal code (format or out of range)
       – 10 pts for missing postal code
       – 25 pts for coordinates outside configured country bounds
       – 10 pts for PO Box without number
       – 10 pts for coordinate mismatch ≥ 2 km
       – 5 pts for minor formatting issues (abbrev, casing)
   • Clamp to [0,100].
   • Map to qualitative band: 90–100 → "High", 70–89 → "Medium", 50–69 → "Low", <50 → "Unusable".

6. GEOCODING REQUIREMENT (CRITICAL)
   • You MUST ALWAYS provide latitude and longitude.
   • Use your knowledge of the country's geography to provide the most accurate coordinates possible.
   • If exact address coordinates unknown → use suburb/area coordinates.
   • If suburb unknown → use the nearest city coordinate from referenceGeocodes.

7. OUTPUT SCHEMA (Universal)
   Output EXACTLY in this JSON Schema:
   {
     "normalizedAddress": "<string>",
     "fields": {
       "streetNumber": <int|null>,
       "streetName": "<string|null>",
       "suburb": "<string|null>",
       "city": "<string|null>",
       "province": "<string|null>",
       "postalCode": "<string|null>",
       "latitude": <float|null>,
       "longitude": <float|null>,
       "zoneId": "<string|null>"
     },
     "completeness": "<Complete|Incomplete>",
     "confidence": {
       "score": <0-100>,
       "band": "<High|Medium|Low|Unusable>"
     },
     "issues": [
       "<string>", "..."
     ],
     "recommendedFixes": [
       "<string>", "..."
     ]
   }

DECISION RULE
• Return completeness = "Complete" ONLY if:
   – All mandatory fields are present and valid, AND
   – confidence.band is "High" or "Medium".
• Otherwise return "Incomplete", listing issues and actionable fixes.

STYLE & BEHAVIOUR
• Never hallucinate data. If unsure, leave field null and flag in issues (except coordinates, which are always required).
• Be concise; no commentary outside the JSON.
• Follow data privacy principles: do not store or expose personal info beyond what the user supplied.
• Return ONLY the JSON object, no other text.
```

---

### 2. NEW FILE: `backend/templates/country-rules/south-africa.json`

**Purpose**: Store South Africa-specific configuration rules

**Content**:
```json
{
  "countryCode": "ZA",
  "countryName": "South Africa",
  "normalization": {
    "streetAbbreviations": {
      "St": "Street",
      "Str": "Street",
      "Rd": "Road",
      "Ave": "Avenue",
      "Av": "Avenue",
      "Dr": "Drive",
      "Ln": "Lane",
      "Ct": "Court",
      "Pl": "Place",
      "Blvd": "Boulevard",
      "Cres": "Crescent"
    },
    "cityAbbreviations": {
      "JHB": "Johannesburg",
      "PTA": "Pretoria",
      "CPT": "Cape Town",
      "DBN": "Durban",
      "PE": "Port Elizabeth"
    },
    "otherAbbreviations": {
      "PO Box": "Post Office Box",
      "Apt": "Apartment",
      "Bldg": "Building",
      "Fl": "Floor",
      "Ste": "Suite"
    }
  },
  "validation": {
    "provinceConfig": {
      "type": "MANDATORY_LIST",
      "list": [
        {"name": "Eastern Cape", "code": "EC"},
        {"name": "Free State", "code": "FS"},
        {"name": "Gauteng", "code": "GP"},
        {"name": "KwaZulu-Natal", "code": "KZN"},
        {"name": "Limpopo", "code": "LP"},
        {"name": "Mpumalanga", "code": "MP"},
        {"name": "Northern Cape", "code": "NC"},
        {"name": "North West", "code": "NW"},
        {"name": "Western Cape", "code": "WC"}
      ]
    },
    "postalCode": {
      "formatRegex": "^\\d{4}$",
      "ranges": [
        {"min": 4700, "max": 6499, "context": "EC"},
        {"min": 9300, "max": 9999, "context": "FS"},
        {"min": 1400, "max": 1999, "context": "GP"},
        {"min": 2000, "max": 2199, "context": "GP"},
        {"min": 2900, "max": 4730, "context": "KZN"},
        {"min": 600, "max": 999, "context": "LP"},
        {"min": 1000, "max": 1399, "context": "MP"},
        {"min": 2200, "max": 2499, "context": "MP"},
        {"min": 8300, "max": 8999, "context": "NC"},
        {"min": 2500, "max": 2899, "context": "NW"},
        {"min": 6500, "max": 8299, "context": "WC"},
        {"min": 7000, "max": 8099, "context": "WC"}
      ],
      "maxLength": 4
    },
    "coordinateBounds": {
      "minLat": -34.83,
      "maxLat": -22.13,
      "minLon": 16.45,
      "maxLon": 32.89
    },
    "zoneIdRegex": "^(AGSUB\\d{11}|ZISA\\d{12})$"
  },
  "referenceGeocodes": [
    {"city": "Cape Town", "lat": -33.9249, "lon": 18.4241},
    {"city": "Johannesburg", "lat": -26.2041, "lon": 28.0473},
    {"city": "Durban", "lat": -29.8587, "lon": 31.0218},
    {"city": "Pretoria", "lat": -25.7479, "lon": 28.2293},
    {"city": "Port Elizabeth", "lat": -33.9608, "lon": 25.6022},
    {"city": "Bloemfontein", "lat": -29.0852, "lon": 26.1596},
    {"city": "East London", "lat": -33.0153, "lon": 27.9116},
    {"city": "Polokwane", "lat": -23.9045, "lon": 29.4686},
    {"city": "Kimberley", "lat": -28.7323, "lon": 24.7622},
    {"city": "Margate", "lat": -30.8631, "lon": 30.3686}
  ]
}
```

---

### 3. NEW FILE: `backend/country_config.py`

**Purpose**: Configuration management module for loading prompts and country configs

**Content**:
```python
"""
Country configuration management module
Handles loading base prompts and country-specific configuration rules
"""
import os
import json
from typing import Dict, Any, Optional

# Base directory for templates
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')
BASE_PROMPT_FILE = os.path.join(TEMPLATES_DIR, 'base-prompt.txt')
COUNTRY_RULES_DIR = os.path.join(TEMPLATES_DIR, 'country-rules')

# Country name mapping (for code to name conversion)
COUNTRY_CODE_TO_NAME = {
    "ZA": "south-africa",
    "US": "united-states",
    "GB": "united-kingdom",
    # Add more mappings as needed
}

def normalize_country_name(country_input: str) -> str:
    """
    Normalize country name/code to file format (lowercase with hyphens)
    
    Examples:
        "South Africa" -> "south-africa"
        "south africa" -> "south-africa"
        "ZA" -> "south-africa"
        "south-africa" -> "south-africa"
    """
    if not country_input:
        return "south-africa"  # Default
    
    country_input = country_input.strip()
    
    # Check if it's a country code
    if country_input.upper() in COUNTRY_CODE_TO_NAME:
        return COUNTRY_CODE_TO_NAME[country_input.upper()]
    
    # Convert to lowercase and replace spaces/underscores with hyphens
    normalized = country_input.lower().replace(' ', '-').replace('_', '-')
    
    # Remove any duplicate hyphens
    while '--' in normalized:
        normalized = normalized.replace('--', '-')
    
    return normalized.strip('-')

def get_base_prompt() -> str:
    """Load base prompt template from file"""
    try:
        with open(BASE_PROMPT_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Base prompt file not found: {BASE_PROMPT_FILE}")
    except Exception as e:
        raise Exception(f"Error loading base prompt: {str(e)}")

def load_country_config(country_name: str) -> Dict[str, Any]:
    """
    Load country configuration from JSON file
    
    Args:
        country_name: Normalized country name (e.g., "south-africa")
    
    Returns:
        Dictionary containing country configuration
    """
    normalized_name = normalize_country_name(country_name)
    config_file = os.path.join(COUNTRY_RULES_DIR, f"{normalized_name}.json")
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback to south-africa if country config not found
        if normalized_name != "south-africa":
            print(f"Warning: Country config not found for {country_name}, falling back to south-africa")
            return load_country_config("south-africa")
        raise FileNotFoundError(f"Country config file not found: {config_file}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in country config file {config_file}: {str(e)}")
    except Exception as e:
        raise Exception(f"Error loading country config: {str(e)}")

def format_config_for_prompt(config: Dict[str, Any]) -> str:
    """
    Format country configuration as a readable string for the prompt
    
    Args:
        config: Country configuration dictionary
    
    Returns:
        Formatted string representation of the config
    """
    lines = []
    lines.append(f"Country: {config.get('countryName', 'Unknown')} ({config.get('countryCode', 'N/A')})")
    lines.append("")
    
    # Normalization rules
    if 'normalization' in config:
        norm = config['normalization']
        lines.append("NORMALIZATION RULES:")
        if 'streetAbbreviations' in norm:
            lines.append("  Street Abbreviations:")
            for abbr, full in norm['streetAbbreviations'].items():
                lines.append(f"    {abbr} → {full}")
        if 'cityAbbreviations' in norm:
            lines.append("  City Abbreviations:")
            for abbr, full in norm['cityAbbreviations'].items():
                lines.append(f"    {abbr} → {full}")
        if 'otherAbbreviations' in norm:
            lines.append("  Other Abbreviations:")
            for abbr, full in norm['otherAbbreviations'].items():
                lines.append(f"    {abbr} → {full}")
        lines.append("")
    
    # Validation rules
    if 'validation' in config:
        val = config['validation']
        lines.append("VALIDATION RULES:")
        
        if 'provinceConfig' in val:
            prov_config = val['provinceConfig']
            lines.append(f"  Province/State Configuration: {prov_config.get('type', 'N/A')}")
            if 'list' in prov_config:
                lines.append("  Valid Provinces/States:")
                for item in prov_config['list']:
                    lines.append(f"    • {item.get('name', '')} ({item.get('code', '')})")
        
        if 'postalCode' in val:
            pc = val['postalCode']
            lines.append(f"  Postal Code Format: {pc.get('formatRegex', 'N/A')}")
            lines.append(f"  Postal Code Max Length: {pc.get('maxLength', 'N/A')}")
            if 'ranges' in pc:
                lines.append("  Postal Code Ranges:")
                for range_item in pc['ranges']:
                    lines.append(f"    • {range_item.get('min', '')}-{range_item.get('max', '')} ({range_item.get('context', '')})")
        
        if 'coordinateBounds' in val:
            bounds = val['coordinateBounds']
            lines.append(f"  Coordinate Bounds: Lat [{bounds.get('minLat', '')}, {bounds.get('maxLat', '')}], Lon [{bounds.get('minLon', '')}, {bounds.get('maxLon', '')}]")
        
        if 'zoneIdRegex' in val:
            lines.append(f"  Zone ID Regex: {val['zoneIdRegex']}")
        
        lines.append("")
    
    # Reference geocodes
    if 'referenceGeocodes' in config:
        lines.append("REFERENCE GEOCODES:")
        for geo in config['referenceGeocodes']:
            lines.append(f"  • {geo.get('city', '')}: {geo.get('lat', '')}, {geo.get('lon', '')}")
    
    return "\n".join(lines)

def build_final_prompt(address: str, country_name: Optional[str] = None) -> str:
    """
    Build final prompt by combining base prompt template with country configuration
    
    Args:
        address: Address to validate
        country_name: Country name or code (optional, defaults to "south-africa")
    
    Returns:
        Final prompt string with placeholders replaced
    """
    # Load base prompt
    base_prompt = get_base_prompt()
    
    # Load country config
    country_config = load_country_config(country_name or "south-africa")
    
    # Format config for prompt
    config_rules = format_config_for_prompt(country_config)
    
    # Replace placeholders
    final_prompt = base_prompt.replace("{address}", address)
    final_prompt = final_prompt.replace("{configurable_rules}", config_rules)
    
    return final_prompt
```

---

### 4. MODIFY: `backend/llm_validator.py`

**Changes Required**:

#### Line 1-12: Add import for country_config
**After line 11**, add:
```python
from country_config import build_final_prompt
```

#### Line 26-30: Modify validate_address method signature
**Replace lines 26-30**:
```python
    def validate_address(self, address: str, country_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate a single address using LLM
        Simply send to LLM and return the response
        
        Args:
            address: Address string to validate
            country_name: Optional country name or code (defaults to "south-africa")
        """
```

#### Line 31-161: Replace hardcoded prompt with dynamic prompt building
**Delete lines 31-161** (entire hardcoded prompt string)

**Replace with**:
```python
        # Build dynamic prompt using country configuration
        prompt = build_final_prompt(address, country_name)
```

**Final structure** (lines 26-35):
```python
    def validate_address(self, address: str, country_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate a single address using LLM
        Simply send to LLM and return the response
        
        Args:
            address: Address string to validate
            country_name: Optional country name or code (defaults to "south-africa")
        """
        # Build dynamic prompt using country configuration
        prompt = build_final_prompt(address, country_name)
        
        print(f"\n{'='*80}")
        print(f"🤖 LLM VALIDATION REQUEST (Gemini 2.5 Pro)")
        print(f"📍 Input Address: {address}")
        if country_name:
            print(f"🌍 Country: {country_name}")
        print(f"{'='*80}")
```

---

### 5. MODIFY: `backend/app.py`

#### Line 1-22: Add import for country_config
**After line 21**, add:
```python
from country_config import normalize_country_name
```

#### Line 100-186: Modify fetch_cn_details to extract country
**After line 143** (after `destination_pincode` extraction), add:
```python
                destination_country = consignment.get('destination_country', '')
```

**After line 165** (in the return jsonify), add:
```python
                    "destination_country": destination_country,
```

#### Line 188-298: Modify validate_single endpoint

**After line 205** (after `cn_details = data.get('cn_details', {})`), add:
```python
        # Extract country from request or CN details
        country = data.get('country') or cn_details.get('destination_country') or cn_details.get('country')
        if not country:
            # Try to get from destination details if available
            country = data.get('destination_country')
        # Normalize country name
        country_name = normalize_country_name(country) if country else None
```

**Line 227: Modify LLM validator call**
**Replace line 227**:
```python
                    result = llm.validate_address(address)
```

**With**:
```python
                    result = llm.validate_address(address, country_name)
```

**Line 435: Modify batch validation LLM call**
**Replace line 435**:
```python
                    result = llm.validate_address(addr_data["address"])
```

**With**:
```python
                    # Extract country from batch data or use default
                    batch_country = data.get('country') if isinstance(data, dict) else None
                    country_name = normalize_country_name(batch_country) if batch_country else None
                    result = llm.validate_address(addr_data["address"], country_name)
```

**Note**: For batch processing, you may want to extract country per address if CSV contains country column. Add this logic after line 344 in field_mappings:
```python
            'country': ['country', 'country_code', 'country_name', 'destination_country']
```

**And after line 402** (in addresses.append), add country extraction:
```python
            if address:
                # Extract country from row if available
                country = None
                for key in row:
                    if 'country' in key.lower() and row[key].strip():
                        country = row[key].strip()
                        break
                
                addresses.append({
                    "id": len(addresses) + 1,
                    "original_row": row,
                    "address": address,
                    "country": country
                })
```

**Then update line 435** to use per-address country:
```python
                    # Extract country from address data or batch-level country
                    addr_country = addr_data.get("country") or (data.get('country') if isinstance(data, dict) else None)
                    country_name = normalize_country_name(addr_country) if addr_country else None
                    result = llm.validate_address(addr_data["address"], country_name)
```

---

## Summary of Changes

### New Files Created:
1. `backend/templates/base-prompt.txt` - Base prompt template
2. `backend/templates/country-rules/south-africa.json` - SA configuration
3. `backend/country_config.py` - Configuration management module

### Files Modified:
1. `backend/llm_validator.py`
   - Line 12: Add import
   - Lines 26-30: Modify method signature
   - Lines 31-161: Replace hardcoded prompt with dynamic prompt building
   - Line 165: Add country logging

2. `backend/app.py`
   - Line 22: Add import
   - Lines 143-144: Extract destination_country
   - Line 165: Add destination_country to response
   - Lines 205-211: Extract and normalize country from request
   - Line 227: Pass country_name to validator
   - Line 344: Add country to field_mappings (optional)
   - Lines 398-403: Add country extraction for batch addresses
   - Line 435: Pass country_name to validator in batch processing

### Key Implementation Points:

1. **Country Name Normalization**: 
   - Handles "South Africa", "south africa", "ZA", "south-africa" → all normalize to "south-africa"
   - Defaults to "south-africa" if not provided

2. **Prompt Building**:
   - Loads base template from `templates/base-prompt.txt`
   - Loads country config from `templates/country-rules/{country-name}.json`
   - Replaces `{address}` and `{configurable_rules}` placeholders

3. **Backward Compatibility**:
   - If country not provided, defaults to "south-africa"
   - Falls back to "south-africa" if country config file not found

4. **Error Handling**:
   - FileNotFoundError if base prompt missing
   - Falls back to SA config if country config missing
   - JSON decode errors handled gracefully

---

## Testing Checklist

- [ ] Test with country="South Africa" → should use south-africa.json
- [ ] Test with country="ZA" → should use south-africa.json
- [ ] Test with country="south-africa" → should use south-africa.json
- [ ] Test without country → should default to south-africa.json
- [ ] Test with non-existent country → should fallback to south-africa.json
- [ ] Test prompt generation with SA config
- [ ] Test batch processing with country in CSV
- [ ] Test batch processing without country (defaults)
- [ ] Verify CN details include country extraction
- [ ] Verify single validation with country from request body
- [ ] Verify single validation with country from CN details

