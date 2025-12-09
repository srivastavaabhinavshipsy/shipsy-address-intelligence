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
WHATSAPP_AGENT_BASE_PROMPT_FILE = os.path.join(TEMPLATES_DIR, 'whatsapp-agent-base-prompt.txt')
COUNTRY_RULES_DIR = os.path.join(TEMPLATES_DIR, 'country-rules')

# Default country constant - can be updated when needed
DEFAULT_COUNTRY = "kazakhstan"

# Country name mapping (for code to name conversion)
COUNTRY_CODE_TO_NAME = {
    "ZA": "south-africa",
    "US": "united-states",
    "GB": "united-kingdom",
    "KZ": "kazakhstan",
    # Add more mappings as needed
}

# Cache for dynamic country name mapping (built from config files)
_COUNTRY_NAME_MAPPING = None

def _build_country_name_mapping() -> Dict[str, str]:
    """
    Build a mapping from country names (including localized names) to normalized file names.
    Scans all country config files and maps their countryName, countryCode, and countryAliases to the file name.
    This allows handling Russian, English, and other language country names.
    """
    print(f"🔍 [COUNTRY_MAPPING] Building country name mapping from: {COUNTRY_RULES_DIR}")
    mapping = {}
    
    if not os.path.exists(COUNTRY_RULES_DIR):
        print(f"⚠️  [COUNTRY_MAPPING] Country rules directory does not exist: {COUNTRY_RULES_DIR}")
        return mapping
    
    # Scan all JSON files in country-rules directory
    json_files = [f for f in os.listdir(COUNTRY_RULES_DIR) if f.endswith('.json')]
    print(f"📁 [COUNTRY_MAPPING] Found {len(json_files)} country config file(s): {json_files}")
    
    for filename in json_files:
        # Extract normalized name from filename (e.g., "kazakhstan.json" -> "kazakhstan")
        normalized_name = filename[:-5]  # Remove .json extension
        print(f"  📄 [COUNTRY_MAPPING] Processing: {filename} -> normalized: '{normalized_name}'")
        
        try:
            config_file = os.path.join(COUNTRY_RULES_DIR, filename)
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
                mappings_added = []
                
                def add_mapping(key: str):
                    """Helper to add both original case and lowercase mappings"""
                    if key:
                        mapping[key] = normalized_name
                        mapping[key.lower()] = normalized_name
                        mappings_added.append(key)
                
                # Map countryName (can be in any language) to normalized name
                country_name = config.get('countryName', '')
                if country_name:
                    add_mapping(country_name)
                    print(f"    ✓ [COUNTRY_MAPPING] Added countryName: '{country_name}'")
                        
                # Also map countryCode if available
                country_code = config.get('countryCode', '')
                if country_code:
                    add_mapping(country_code)
                    print(f"    ✓ [COUNTRY_MAPPING] Added countryCode: '{country_code}'")
                
                # Map countryAliases if available (supports multiple aliases)
                country_aliases = config.get('countryAliases', [])
                if isinstance(country_aliases, list) and country_aliases:
                    print(f"    ✓ [COUNTRY_MAPPING] Found {len(country_aliases)} alias(es)")
                    for alias in country_aliases:
                        if alias:  # Skip empty strings
                            add_mapping(alias)
                            print(f"      → Added alias: '{alias}'")
                elif not country_aliases:
                    print(f"    ℹ️  [COUNTRY_MAPPING] No countryAliases found in config")
                
                print(f"    ✅ [COUNTRY_MAPPING] Total mappings added for '{normalized_name}': {len(mappings_added)}")
                        
        except Exception as e:
            # Skip files that can't be read
            print(f"    ❌ [COUNTRY_MAPPING] Warning: Could not read country config {filename}: {e}")
            continue
    
    print(f"🎯 [COUNTRY_MAPPING] Mapping build complete. Total entries: {len(mapping)}")
    return mapping

def _get_country_name_mapping() -> Dict[str, str]:
    """Get or build the country name mapping cache"""
    global _COUNTRY_NAME_MAPPING
    if _COUNTRY_NAME_MAPPING is None:
        print("🔄 [COUNTRY_MAPPING] Cache miss - building new mapping")
        _COUNTRY_NAME_MAPPING = _build_country_name_mapping()
    else:
        print("💾 [COUNTRY_MAPPING] Using cached mapping")
    return _COUNTRY_NAME_MAPPING

def normalize_country_name(country_input: Optional[str] = None) -> str:
    """
    Normalize country name/code to file format (lowercase with hyphens)
    Raises ValueError if country_input is not provided.
    
    Examples:
        "Kazakhstan" -> "kazakhstan"
        "KZ" -> "kazakhstan"
        "South Africa" -> "south-africa"
        "ZA" -> "south-africa"
        "Казахстан" -> "kazakhstan"  # Russian name
        None -> ValueError
    """
    print(f"\n🌍 [NORMALIZE] Normalizing country name: {repr(country_input)}")
    
    if not country_input:
        print("  ❌ [NORMALIZE] Error: Country input is required")
        raise ValueError("Country input is required. Please provide country name or code.")
    
    country_input = country_input.strip()
    print(f"  📝 [NORMALIZE] Trimmed input: {repr(country_input)}")
    
    # Get dynamic mapping from config files (includes localized names like Russian)
    country_mapping = _get_country_name_mapping()
    print(f"  🔍 [NORMALIZE] Checking dynamic mapping (size: {len(country_mapping)})")
    
    # Check if it's a known country name (including localized names like Russian)
    if country_input in country_mapping:
        result = country_mapping[country_input]
        print(f"  ✅ [NORMALIZE] Found in mapping (exact match): '{country_input}' -> '{result}'")
        return result
    
    # Check lowercase version
    country_lower = country_input.lower()
    if country_lower in country_mapping:
        result = country_mapping[country_lower]
        print(f"  ✅ [NORMALIZE] Found in mapping (lowercase match): '{country_lower}' -> '{result}'")
        return result
    
    print(f"  ⚠️  [NORMALIZE] Not found in dynamic mapping, checking static COUNTRY_CODE_TO_NAME")
    
    # Check if it's a country code (fallback to existing static mapping)
    if country_input.upper() in COUNTRY_CODE_TO_NAME:
        result = COUNTRY_CODE_TO_NAME[country_input.upper()]
        print(f"  ✅ [NORMALIZE] Found in static code mapping: '{country_input.upper()}' -> '{result}'")
        return result
    
    print(f"  ⚠️  [NORMALIZE] Not found in any mapping, using fallback normalization")
    
    # Convert to lowercase and replace spaces/underscores with hyphens
    normalized = country_input.lower().replace(' ', '-').replace('_', '-')
    
    # Remove any duplicate hyphens
    while '--' in normalized:
        normalized = normalized.replace('--', '-')
    
    result = normalized.strip('-')
    print(f"  📤 [NORMALIZE] Fallback normalization result: '{country_input}' -> '{result}'")
    return result

def get_base_prompt() -> str:
    """Load base prompt template from file"""
    try:
        with open(BASE_PROMPT_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Base prompt file not found: {BASE_PROMPT_FILE}")
    except Exception as e:
        raise Exception(f"Error loading base prompt: {str(e)}")

def load_country_config(country_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Load country configuration from JSON file
    
    Args:
        country_name: Normalized country name (e.g., "kazakhstan", "south-africa")
                     If None, uses DEFAULT_COUNTRY constant
    
    Returns:
        Dictionary containing country configuration
    """
    if country_name is None:
        country_name = DEFAULT_COUNTRY
    normalized_name = normalize_country_name(country_name)
    config_file = os.path.join(COUNTRY_RULES_DIR, f"{normalized_name}.json")
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Country config file not found: {config_file}. Please ensure the country configuration file exists.")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in country config file {config_file}: {str(e)}")
    except Exception as e:
        raise Exception(f"Error loading country config: {str(e)}")

def format_config_for_prompt(config: Dict[str, Any]) -> str:
    """
    Format country configuration as JSON string for the prompt
    
    Args:
        config: Country configuration dictionary
    
    Returns:
        JSON string representation of the config
    """
    return json.dumps(config, indent=2, ensure_ascii=False)

def build_final_prompt(address: str, country_name: Optional[str] = None) -> str:
    """
    Build final prompt by combining base prompt template with country configuration
    
    Args:
        address: Address to validate
        country_name: Country name or code (optional, uses DEFAULT_COUNTRY if not provided)
                     Country should be provided from org-config or request
    
    Returns:
        Final prompt string with placeholders replaced
    """
    # Load base prompt
    base_prompt = get_base_prompt()
    
    # Load country config (uses DEFAULT_COUNTRY if country_name is None)
    country_config = load_country_config(country_name)
    
    # Format config for prompt
    config_rules = format_config_for_prompt(country_config)
    
    # Replace placeholders
    final_prompt = base_prompt.replace("{address}", address)
    final_prompt = final_prompt.replace("{configurable_rules}", config_rules)
    
    return final_prompt

def get_whatsapp_agent_base_prompt() -> str:
    """Load WhatsApp agent base prompt template from file"""
    try:
        with open(WHATSAPP_AGENT_BASE_PROMPT_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"WhatsApp agent base prompt file not found: {WHATSAPP_AGENT_BASE_PROMPT_FILE}")
    except Exception as e:
        raise Exception(f"Error loading WhatsApp agent base prompt: {str(e)}")

def build_whatsapp_agent_prompt(country_name: Optional[str] = None) -> str:
    """
    Build WhatsApp agent prompt by combining base prompt template with country configuration
    
    Args:
        country_name: Country name or code (optional, uses DEFAULT_COUNTRY if not provided)
                     Country should be provided from org-config or request
    
    Returns:
        Final WhatsApp agent prompt string with placeholders replaced
    """
    # Load WhatsApp agent base prompt
    base_prompt = get_whatsapp_agent_base_prompt()
    
    # Load country config (uses DEFAULT_COUNTRY if country_name is None)
    country_config = load_country_config(country_name)
    
    # Get country name for display
    display_country_name = country_config.get('countryName', country_name or DEFAULT_COUNTRY)
    if not display_country_name:
        # Fallback: capitalize and format the normalized name
        normalized = normalize_country_name(country_name) if country_name else DEFAULT_COUNTRY
        display_country_name = normalized.replace('-', ' ').title()
    
    # Format country config as JSON (same as llm_validator.py)
    config_rules = format_config_for_prompt(country_config)
    
    # Replace placeholders
    final_prompt = base_prompt.replace("{country_name}", display_country_name)
    final_prompt = final_prompt.replace("{country_validation_rules}", config_rules)
    
    return final_prompt

