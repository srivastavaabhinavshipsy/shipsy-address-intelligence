"""
LLM-based address validation using Google Gemini.
Supports multiple countries through country-specific prompts.
"""
import os
import json
import google.generativeai as genai
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Import country module
from countries import get_prompt, get_default_coordinates, get_country_info

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

    def validate_address(self, address: str, country_code: str = "ZA") -> Dict[str, Any]:
        """
        Validate a single address using LLM.

        Args:
            address: The address to validate
            country_code: ISO country code (ZA for South Africa, KZ for Kazakhstan)

        Returns:
            Validation result dictionary
        """
        # Get country-specific prompt
        try:
            prompt = get_prompt(country_code, address)
            country_info = get_country_info(country_code)
            default_coords = get_default_coordinates(country_code)
        except ValueError as e:
            return {
                'original_address': address,
                'normalized_address': address,
                'is_valid': False,
                'confidence_score': 0,
                'confidence_level': 'FAILED',
                'components': {},
                'coordinates': {'latitude': 0, 'longitude': 0},
                'issues': [str(e)],
                'suggestions': ['Use a supported country code: ZA, KZ'],
                'validation_method': 'LLM',
                'llm_model': 'gemini-2.5-pro',
                'country': country_code,
                'error': True
            }

        print(f"\n{'='*80}")
        print(f"🤖 LLM VALIDATION REQUEST (Gemini 2.5 Pro)")
        print(f"🌍 Country: {country_info['name']} ({country_code})")
        print(f"📍 Input Address: {address}")
        print(f"{'='*80}")

        try:
            # Generate response from Gemini
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=1.0,
                    top_p=0.95,
                    max_output_tokens=8192,
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
            return self._transform_response(result, address, country_code, default_coords)

        except Exception as e:
            print(f"Error calling LLM: {e}")
            # Return error response with country-specific default coordinates
            return {
                'original_address': address,
                'normalized_address': address,
                'is_valid': False,
                'confidence_score': 0,
                'confidence_level': 'FAILED',
                'components': {},
                'coordinates': {'latitude': default_coords['lat'], 'longitude': default_coords['lon']},
                'issues': [f'LLM Error: {str(e)}'],
                'suggestions': ['Please try again'],
                'validation_method': 'LLM',
                'llm_model': 'gemini-2.5-pro',
                'country': country_code,
                'error': True
            }

    def _transform_response(
        self,
        llm_result: Dict,
        original_address: str,
        country_code: str,
        default_coords: Dict
    ) -> Dict[str, Any]:
        """
        Transform LLM response to match our backend format.
        Handles different field structures for different countries.
        """
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

        # Build components dictionary based on country
        components = self._extract_components(fields, country_code)

        # Get coordinates from LLM response (with country-specific defaults)
        coordinates = {
            'latitude': fields.get('latitude', default_coords['lat']),
            'longitude': fields.get('longitude', default_coords['lon'])
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
            'llm_model': 'gemini-2.5-pro',
            'country': country_code
        }

    def _extract_components(self, fields: Dict, country_code: str) -> Dict:
        """
        Extract address components from LLM fields.
        Different countries have different field structures.
        """
        components = {}

        if country_code == "ZA":
            # South Africa fields
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

        elif country_code == "KZ":
            # Kazakhstan fields (different structure)
            if fields.get('streetName'):
                components['street'] = fields.get('streetName')
            if fields.get('buildingNumber'):
                components['building'] = fields.get('buildingNumber')
                # Combine street and building for street_address
                street = fields.get('streetName', '')
                building = fields.get('buildingNumber', '')
                if street and building:
                    components['street_address'] = f"{street}, д. {building}"
                elif street:
                    components['street_address'] = street
            if fields.get('apartment'):
                components['apartment'] = fields.get('apartment')
            if fields.get('block'):
                components['block'] = fields.get('block')
            if fields.get('microdistrict'):
                components['microdistrict'] = fields.get('microdistrict')
            if fields.get('city'):
                components['city'] = fields.get('city')
            if fields.get('oblast'):
                components['oblast'] = fields.get('oblast')
                components['region'] = fields.get('oblast')  # Alias for consistency
            if fields.get('postalCode'):
                components['postal_code'] = fields.get('postalCode')

        else:
            # Generic fallback - copy all fields
            for key, value in fields.items():
                if value is not None and key not in ('latitude', 'longitude'):
                    components[key] = value

        return components
