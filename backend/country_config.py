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

def normalize_country_name(country_input: Optional[str] = None) -> str:
    """
    Normalize country name/code to file format (lowercase with hyphens)
    Raises ValueError if country_input is not provided.
    
    Examples:
        "Kazakhstan" -> "kazakhstan"
        "KZ" -> "kazakhstan"
        "South Africa" -> "south-africa"
        "ZA" -> "south-africa"
        None -> ValueError
    """
    if not country_input:
        raise ValueError("Country input is required. Please provide country name or code.")
    
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

