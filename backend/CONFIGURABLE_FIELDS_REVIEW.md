# Review of Additional Configurable Fields

## Overview
This document reviews fields that are currently hardcoded but could potentially be made configurable per country.

## Currently Configurable (via JSON config)

### ✅ Already Implemented:
1. **Normalization Rules**
   - Street abbreviations
   - City abbreviations
   - Other abbreviations

2. **Validation Rules**
   - Province/State configuration (type, list)
   - Postal code format (regex, ranges, maxLength)
   - Coordinate bounds
   - Zone ID regex

3. **Reference Data**
   - Reference geocodes (city coordinates)

## Potentially Configurable Fields

### 1. Confidence Scoring Weights ⚠️
**Current Status**: Hardcoded in base prompt template

**Current Values**:
- -25 pts for missing street address
- -20 pts for missing city/town
- -20 pts for missing Province/State
- -30 pts for invalid Province/State
- -15 pts for invalid postal code
- -10 pts for missing postal code
- -25 pts for coordinates outside bounds
- -10 pts for PO Box without number
- -10 pts for coordinate mismatch ≥ 2 km
- -5 pts for minor formatting issues

**Recommendation**: 
- **Should be configurable** - Different countries may have different priorities
- Example: In some countries, postal code is more critical than street address
- **Implementation**: Add `confidenceScoring` section to country JSON config

**Proposed JSON Structure**:
```json
{
  "confidenceScoring": {
    "missingStreetAddress": -25,
    "missingCity": -20,
    "missingProvince": -20,
    "invalidProvince": -30,
    "invalidPostalCode": -15,
    "missingPostalCode": -10,
    "coordinatesOutsideBounds": -25,
    "poBoxWithoutNumber": -10,
    "coordinateMismatch": -10,
    "formattingIssues": -5
  }
}
```

### 2. Confidence Level Thresholds ⚠️
**Current Status**: Hardcoded in base prompt template

**Current Values**:
- 90–100 → "High"
- 70–89 → "Medium"
- 50–69 → "Low"
- <50 → "Unusable"

**Recommendation**: 
- **Could be configurable** - But likely universal across countries
- **Implementation**: Add `confidenceThresholds` section if needed

**Proposed JSON Structure**:
```json
{
  "confidenceThresholds": {
    "high": {"min": 90, "max": 100},
    "medium": {"min": 70, "max": 89},
    "low": {"min": 50, "max": 69},
    "unusable": {"min": 0, "max": 49}
  }
}
```

### 3. Coordinate Validation Distance Threshold ⚠️
**Current Status**: Hardcoded as 2 km in base prompt

**Current Value**: 2 km (haversine distance)

**Recommendation**: 
- **Could be configurable** - Different countries may have different tolerance
- Example: Dense urban areas might need stricter validation
- **Implementation**: Add to validation section

**Proposed JSON Structure**:
```json
{
  "validation": {
    "coordinateValidationDistanceKm": 2.0
  }
}
```

### 4. JSON Output Schema Structure ✅
**Current Status**: Hardcoded in base prompt

**Current Schema**: Fixed structure with specific fields

**Recommendation**: 
- **Should remain fixed** - Backend expects consistent format
- Changing schema would break API contracts
- **Conclusion**: Keep as-is in base prompt

### 5. Address Parsing Logic ⚠️
**Current Status**: Partially in rule-based validator (`validator.py`)

**Recommendation**: 
- **Not applicable for LLM validator** - LLM handles parsing dynamically
- Rule-based validator could be country-aware, but that's separate from this implementation
- **Conclusion**: Out of scope for current LLM-based implementation

### 6. Street Types Validation ⚠️
**Current Status**: Mentioned in base prompt but not configurable

**Current**: "Must align with common street types"

**Recommendation**: 
- **Should be configurable** - Different countries have different street type conventions
- **Implementation**: Add to validation section

**Proposed JSON Structure**:
```json
{
  "validation": {
    "streetTypes": [
      "Street", "Road", "Avenue", "Drive", "Lane", 
      "Crescent", "Way", "Close", "Place", "Boulevard", 
      "Highway", "Freeway"
    ]
  }
}
```

### 7. Minimum Street Name Length ⚠️
**Current Status**: Hardcoded as ≥ 3 characters in base prompt

**Recommendation**: 
- **Could be configurable** - But likely universal
- **Conclusion**: Keep as-is unless specific country requirements emerge

### 8. PO Box Format ⚠️
**Current Status**: Hardcoded format in base prompt

**Recommendation**: 
- **Could be configurable** - Different countries use different PO Box formats
- **Implementation**: Add to validation section

**Proposed JSON Structure**:
```json
{
  "validation": {
    "poBoxFormat": {
      "pattern": "PO Box [number]",
      "regex": "^PO\\s*Box\\s*\\d+$"
    }
  }
}
```

## Summary Recommendations

### High Priority (Should be configurable):
1. ✅ **Confidence Scoring Weights** - Different countries have different priorities
2. ✅ **Street Types List** - Country-specific street type conventions
3. ⚠️ **Coordinate Validation Distance** - Could vary by country density

### Medium Priority (Could be configurable):
1. ⚠️ **Confidence Level Thresholds** - Likely universal but could vary
2. ⚠️ **PO Box Format** - Different countries may have different formats

### Low Priority (Keep as-is):
1. ✅ **JSON Output Schema** - Must remain consistent for API
2. ✅ **Minimum Street Name Length** - Universal requirement
3. ✅ **Address Parsing Logic** - Handled by LLM dynamically

## Implementation Notes

If implementing additional configurable fields:

1. **Update `country_config.py`**:
   - Modify `format_config_for_prompt()` to include new fields
   - Add formatting logic for confidence scoring, thresholds, etc.

2. **Update `templates/base-prompt.txt`**:
   - Replace hardcoded values with placeholders or references to config
   - Example: `{confidenceScoring}` or direct references like `validation.confidenceScoring.missingStreetAddress`

3. **Update `templates/country-rules/south-africa.json`**:
   - Add new sections for configurable fields
   - Provide default values matching current hardcoded behavior

4. **Backward Compatibility**:
   - Ensure defaults match current behavior if fields are missing
   - Fallback to hardcoded values if config doesn't specify

## Current Implementation Status

**Phase 1 (Completed)**: Core configuration system
- Base prompt template
- Country-specific rules (normalization, validation, geocodes)
- Dynamic prompt building

**Phase 2 (Future Enhancement)**: Extended configurability
- Confidence scoring weights
- Street types validation
- Coordinate validation distance
- PO Box format rules

