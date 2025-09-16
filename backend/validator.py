"""
South African Address Validation Logic
"""

import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from sa_data import *

@dataclass
class ValidationResult:
    is_valid: bool
    confidence_score: float
    confidence_level: str
    original_address: str
    normalized_address: str
    components: Dict[str, str]
    issues: List[str]
    suggestions: List[str]
    coordinates: Optional[Dict[str, float]] = None
    
    def to_dict(self):
        return asdict(self)

class SAAddressValidator:
    def __init__(self):
        self.provinces = PROVINCES
        self.postal_ranges = POSTAL_CODE_RANGES
        self.bounds = SA_BOUNDS
        self.street_types = STREET_TYPES
        self.suburbs = COMMON_SUBURBS
        self.abbreviations = COMMON_ABBREVIATIONS
        
    def validate_address(self, address: str) -> ValidationResult:
        """Main validation function"""
        issues = []
        suggestions = []
        components = self._parse_address(address)
        
        # Validate components
        confidence_score = 100.0
        
        # Check for required components
        if not components.get("street_address"):
            issues.append("Missing street address")
            confidence_score -= 25
            
        if not components.get("city"):
            issues.append("Missing city/town")
            confidence_score -= 20
            suggestions.append("Add city name for better accuracy")
            
        if not components.get("province"):
            issues.append("Missing province")
            confidence_score -= 20
            suggestions.append("Include province (e.g., Western Cape, Gauteng)")
        else:
            # Validate province
            if not self._validate_province(components["province"]):
                issues.append(f"Invalid province: {components['province']}")
                confidence_score -= 30
                suggestions.append(f"Valid provinces: {', '.join(self.provinces.keys())}")
                
        # Validate postal code
        postal_code = components.get("postal_code")
        if postal_code:
            if not self._validate_postal_code(postal_code, components.get("province")):
                issues.append(f"Invalid postal code: {postal_code}")
                confidence_score -= 15
                if components.get("province"):
                    ranges = self.postal_ranges.get(components["province"], [])
                    if ranges:
                        suggestions.append(f"Valid postal codes for {components['province']}: {ranges[0][0]}-{ranges[0][1]}")
        else:
            issues.append("Missing postal code")
            confidence_score -= 10
            suggestions.append("Add 4-digit postal code")
            
        # Check for PO Box
        if self._is_po_box(address):
            components["type"] = "PO Box"
            if not components.get("po_box_number"):
                issues.append("PO Box number not clearly specified")
                confidence_score -= 10
                
        # Validate coordinates if provided
        if components.get("latitude") and components.get("longitude"):
            if not self._validate_coordinates(components["latitude"], components["longitude"]):
                issues.append("Coordinates outside South Africa")
                confidence_score -= 25
                
        # Normalize address
        normalized = self._normalize_address(components)
        
        # Determine confidence level
        confidence_level = self._get_confidence_level(confidence_score)
        
        # Generate mock coordinates for demo
        coords = self._generate_mock_coordinates(components.get("province"), components.get("city"))
        
        return ValidationResult(
            is_valid=confidence_score >= 70,
            confidence_score=max(0, min(100, confidence_score)),
            confidence_level=confidence_level,
            original_address=address,
            normalized_address=normalized,
            components=components,
            issues=issues,
            suggestions=suggestions,
            coordinates=coords
        )
    
    def _parse_address(self, address: str) -> Dict[str, str]:
        """Parse address into components"""
        components = {}
        address_lower = address.lower()
        
        # Expand abbreviations
        for abbr, full in self.abbreviations.items():
            address_lower = re.sub(r'\b' + abbr + r'\b', full, address_lower)
        
        # Extract postal code
        postal_match = re.search(r'\b(\d{4})\b', address)
        if postal_match:
            components["postal_code"] = postal_match.group(1)
            address = address.replace(postal_match.group(1), "")
        
        # Extract province
        for province in self.provinces.keys():
            if province.lower() in address_lower:
                components["province"] = province
                address_lower = address_lower.replace(province.lower(), "")
                break
        else:
            # Check for province codes
            for code, province in PROVINCE_CODES.items():
                if f" {code.lower()} " in f" {address_lower} " or address_lower.endswith(f" {code.lower()}"):
                    components["province"] = province
                    address_lower = re.sub(r'\b' + code.lower() + r'\b', '', address_lower)
                    break
        
        # Extract city
        all_cities = []
        for province_data in self.provinces.values():
            all_cities.extend([c.lower() for c in province_data["major_cities"]])
        
        for city in all_cities:
            if city in address_lower:
                # Find original case version
                for province_data in self.provinces.values():
                    for orig_city in province_data["major_cities"]:
                        if orig_city.lower() == city:
                            components["city"] = orig_city
                            address_lower = address_lower.replace(city, "")
                            break
                break
        
        # Extract suburb if present
        if components.get("city"):
            suburbs = self.suburbs.get(components["city"], [])
            for suburb in suburbs:
                if suburb.lower() in address_lower:
                    components["suburb"] = suburb
                    address_lower = address_lower.replace(suburb.lower(), "")
                    break
        
        # Extract PO Box
        po_box_match = re.search(r'p\.?o\.?\s*box\s*(\d+)', address_lower)
        if po_box_match:
            components["po_box_number"] = po_box_match.group(1)
            components["type"] = "PO Box"
        
        # Extract unit/apartment number
        unit_match = re.search(r'(unit|apartment|apt|flat)\s*(\d+[a-z]?)', address_lower)
        if unit_match:
            components["unit"] = unit_match.group(2)
        
        # Extract street address (what's left after removing other components)
        street_parts = []
        remaining = address_lower
        for comp in ["province", "city", "suburb", "postal_code"]:
            if comp in components:
                remaining = remaining.replace(components[comp].lower(), "")
        
        remaining = re.sub(r'\s+', ' ', remaining).strip()
        if remaining and len(remaining) > 3:
            # Clean up and format
            remaining = remaining.strip(" ,.-")
            if remaining:
                components["street_address"] = remaining.title()
        
        return components
    
    def _validate_province(self, province: str) -> bool:
        """Validate province name or code"""
        return province in self.provinces or province in PROVINCE_CODES
    
    def _validate_postal_code(self, postal_code: str, province: Optional[str]) -> bool:
        """Validate postal code format and range"""
        if not re.match(r'^\d{4}$', postal_code):
            return False
        
        code = int(postal_code)
        
        if province and province in self.postal_ranges:
            ranges = self.postal_ranges[province]
            return any(start <= code <= end for start, end in ranges)
        
        # Check against all ranges if no province specified
        for ranges in self.postal_ranges.values():
            if any(start <= code <= end for start, end in ranges):
                return True
        
        return False
    
    def _validate_coordinates(self, lat: float, lon: float) -> bool:
        """Check if coordinates are within SA bounds"""
        return (self.bounds["lat_min"] <= lat <= self.bounds["lat_max"] and
                self.bounds["lon_min"] <= lon <= self.bounds["lon_max"])
    
    def _is_po_box(self, address: str) -> bool:
        """Check if address is a PO Box"""
        return bool(re.search(r'p\.?o\.?\s*box', address.lower()))
    
    def _normalize_address(self, components: Dict[str, str]) -> str:
        """Create normalized address string"""
        parts = []
        
        if components.get("unit"):
            parts.append(f"Unit {components['unit']}")
        
        if components.get("street_address"):
            parts.append(components["street_address"])
        
        if components.get("suburb"):
            parts.append(components["suburb"])
        
        if components.get("city"):
            parts.append(components["city"])
        
        if components.get("province"):
            parts.append(components["province"])
        
        if components.get("postal_code"):
            parts.append(components["postal_code"])
        
        if components.get("type") == "PO Box" and components.get("po_box_number"):
            parts.insert(0, f"PO Box {components['po_box_number']}")
        
        return ", ".join(parts)
    
    def _get_confidence_level(self, score: float) -> str:
        """Determine confidence level from score"""
        if score >= 90:
            return "CONFIDENT"
        elif score >= 70:
            return "LIKELY"
        elif score >= 50:
            return "SUSPICIOUS"
        else:
            return "FAILED"
    
    def _generate_mock_coordinates(self, province: Optional[str], city: Optional[str]) -> Optional[Dict[str, float]]:
        """Generate mock coordinates for demo purposes"""
        # Mock coordinates for major cities
        city_coords = {
            "Cape Town": {"latitude": -33.9249, "longitude": 18.4241},
            "Johannesburg": {"latitude": -26.2041, "longitude": 28.0473},
            "Durban": {"latitude": -29.8587, "longitude": 31.0218},
            "Pretoria": {"latitude": -25.7479, "longitude": 28.2293},
            "Port Elizabeth": {"latitude": -33.9608, "longitude": 25.6022},
            "Bloemfontein": {"latitude": -29.0852, "longitude": 26.1596},
            "East London": {"latitude": -33.0153, "longitude": 27.9116},
            "Nelspruit": {"latitude": -25.4753, "longitude": 30.9694},
            "Mbombela": {"latitude": -25.4753, "longitude": 30.9694},
            "Polokwane": {"latitude": -23.9045, "longitude": 29.4689},
            "Kimberley": {"latitude": -28.7282, "longitude": 24.7499},
            "Mahikeng": {"latitude": -25.8560, "longitude": 25.6403}
        }
        
        if city and city in city_coords:
            return city_coords[city]
        
        # Province center coordinates as fallback
        province_coords = {
            "Western Cape": {"latitude": -33.2278, "longitude": 21.8569},
            "Gauteng": {"latitude": -26.1076, "longitude": 28.0567},
            "KwaZulu-Natal": {"latitude": -28.5306, "longitude": 30.8958},
            "Eastern Cape": {"latitude": -32.2968, "longitude": 26.4194},
            "Free State": {"latitude": -28.4541, "longitude": 26.7968},
            "Mpumalanga": {"latitude": -25.5653, "longitude": 30.5279},
            "Limpopo": {"latitude": -23.4013, "longitude": 29.4179},
            "North West": {"latitude": -26.6639, "longitude": 25.2838},
            "Northern Cape": {"latitude": -29.0467, "longitude": 22.0247}
        }
        
        if province and province in province_coords:
            return province_coords[province]
        
        # Default to center of SA
        return {"latitude": -28.4793, "longitude": 24.6727}