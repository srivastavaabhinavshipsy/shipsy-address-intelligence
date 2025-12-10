"""
Country Registry for Address Intelligence.

Simplified approach: Each country just provides an LLM prompt.
The LLM does all the heavy lifting (validation, normalization, suggestions).

This module provides:
- Country detection from address text or CN details
- LLM prompt selection by country
"""

from typing import Dict, Optional


# Country metadata (minimal - just what we need for routing)
COUNTRIES = {
    "ZA": {
        "name": "South Africa",
        "name_local": "South Africa",
        "language": "en",
        "postal_code_length": 4,
        "default_coords": {"lat": -28.4793, "lon": 24.6727},
    },
    "KZ": {
        "name": "Kazakhstan",
        "name_local": "Казахстан",
        "language": "ru",
        "postal_code_length": 6,
        "default_coords": {"lat": 48.0196, "lon": 66.9237},
    },
}

# Aliases for country detection (uppercase)
COUNTRY_ALIASES = {
    # South Africa
    "SOUTH AFRICA": "ZA",
    "SOUTH-AFRICA": "ZA",
    "RSA": "ZA",
    "SUID-AFRIKA": "ZA",
    "REPUBLIC OF SOUTH AFRICA": "ZA",

    # Kazakhstan
    "KAZAKHSTAN": "KZ",
    "KAZAKSTAN": "KZ",
    "КАЗАХСТАН": "KZ",
    "РЕСПУБЛИКА КАЗАХСТАН": "KZ",
    "REPUBLIC OF KAZAKHSTAN": "KZ",
    "QAZAQSTAN": "KZ",
}


def get_country_info(code: str) -> Dict:
    """
    Get country metadata by ISO code.

    Args:
        code: ISO 3166-1 alpha-2 code (ZA, KZ)

    Returns:
        Country metadata dict

    Raises:
        ValueError: If country not supported
    """
    code = code.upper().strip()

    # Check alias
    if code in COUNTRY_ALIASES:
        code = COUNTRY_ALIASES[code]

    if code not in COUNTRIES:
        raise ValueError(f"Unsupported country: {code}. Supported: {list(COUNTRIES.keys())}")

    return {"code": code, **COUNTRIES[code]}


def detect_country_from_address(address: str) -> str:
    """
    Auto-detect country from address text.

    Logic:
    1. Check for Cyrillic characters -> KZ
    2. Check for explicit country mentions
    3. Default to ZA (South Africa)

    Args:
        address: Address text

    Returns:
        Country code (ZA or KZ)
    """
    if not address:
        return "ZA"

    address_upper = address.upper()

    # Check for explicit country mentions
    for alias, code in COUNTRY_ALIASES.items():
        if alias in address_upper:
            return code

    # Check for Cyrillic characters (Russian/Kazakh)
    if any('\u0400' <= char <= '\u04FF' for char in address):
        return "KZ"

    # Default to South Africa
    return "ZA"


def detect_country_from_cn_details(cn_details: dict) -> str:
    """
    Detect country from Shipsy CN details.

    Args:
        cn_details: CN details from Shipsy API

    Returns:
        Country code
    """
    if not cn_details:
        return "ZA"

    # Check destination_country field at top level
    dest_country = cn_details.get("destination_country", "")

    # Also check inside raw_data (Shipsy nested structure)
    if not dest_country:
        raw_data = cn_details.get("raw_data", {})
        if raw_data:
            dest_country = raw_data.get("destination_country", "")

    if dest_country:
        dest_upper = dest_country.upper().strip()
        if dest_upper in COUNTRY_ALIASES:
            return COUNTRY_ALIASES[dest_upper]
        if dest_upper in COUNTRIES:
            return dest_upper

    # Fall back to address detection
    address = cn_details.get("full_address", "") or cn_details.get("destination_address_line_1", "")
    return detect_country_from_address(address)


def get_prompt(country_code: str, address: str) -> str:
    """
    Get the LLM prompt for a specific country.

    Args:
        country_code: ISO country code (ZA, KZ)
        address: Address to validate

    Returns:
        Complete LLM prompt string
    """
    code = country_code.upper().strip()

    if code in COUNTRY_ALIASES:
        code = COUNTRY_ALIASES[code]

    if code == "ZA":
        from .south_africa.prompt import get_prompt as get_za_prompt
        return get_za_prompt(address)
    elif code == "KZ":
        from .kazakhstan.prompt import get_prompt as get_kz_prompt
        return get_kz_prompt(address)
    else:
        raise ValueError(f"No prompt available for country: {code}")


def get_default_coordinates(country_code: str) -> Dict:
    """
    Get default/fallback coordinates for a country.

    Args:
        country_code: ISO country code

    Returns:
        Dict with lat, lon
    """
    info = get_country_info(country_code)
    return info["default_coords"]


def list_supported_countries() -> list:
    """List all supported countries."""
    return [
        {"code": code, **info}
        for code, info in COUNTRIES.items()
    ]


def is_supported(country_code: str) -> bool:
    """Check if a country is supported."""
    code = country_code.upper().strip()
    if code in COUNTRY_ALIASES:
        code = COUNTRY_ALIASES[code]
    return code in COUNTRIES
