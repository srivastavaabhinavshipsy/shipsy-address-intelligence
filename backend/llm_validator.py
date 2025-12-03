"""
LLM-based address validation using Google Gemini - SIMPLIFIED
"""
import os
import json
import google.generativeai as genai
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from country_config import build_final_prompt

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
    
    def validate_address(self, address: str, country_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate a single address using LLM
        Simply send to LLM and return the response
        
        Args:
            address: Address string to validate
            country_name: Optional country name or code (defaults to "kazakhstan" if not provided)
                         Country should be provided from org-config or request beforehand
        """
        # Build dynamic prompt using country configuration
        prompt = build_final_prompt(address, country_name)
        
        print(f"\n{'='*80}")
        print(f"🤖 LLM VALIDATION REQUEST (Gemini 2.5 Pro)")
        print(f"📍 Input Address: {address}")
        if country_name:
            print(f"🌍 Country: {country_name}")
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
                'coordinates': {'latitude': 51.1694, 'longitude': 71.4491},
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