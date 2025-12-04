<!-- f322b18e-c234-4adf-a425-8fb8b8a27c4d 7e103faf-7451-4b7d-9351-4563b1a01f30 -->
# Country-Based Prompt and Configuration System

## Overview

Transform the hardcoded South African address validation system into a multi-country configurable system where:

- Base prompt template is stored in `templates/base-prompt.txt` with placeholders `{address}` and `{configurable_rules}`
- Country-specific configuration rules are stored in `templates/country-rules/{country-name}.json` (e.g., `south-africa.json`)
- The base prompt's `{configurable_rules}` placeholder is replaced with the JSON content from country rules file
- Country name comes from destination details in API requests
- No API endpoint needed - countries are added by manually creating new JSON files in `templates/country-rules/`

## Implementation Plan

### 1. Directory Structure Setup

- Create `backend/templates/` directory
- Create `backend/templates/country-rules/` directory
- Create `templates/base-prompt.txt` with the provided base prompt template (containing `{address}` and `{configurable_rules}` placeholders)
- Create initial `templates/country-rules/south-africa.json` with SA configuration based on provided schema

### 2. Country Configuration Schema

Define JSON schema for country configs (based on provided example):

- `countryCode` (e.g., "ZA")
- `countryName` (e.g., "South Africa")
- `normalization`: `streetAbbreviations`, `cityAbbreviations`, `otherAbbreviations`
- `validation`: `provinceConfig` (type, list), `postalCode` (formatRegex, ranges, maxLength), `coordinateBounds`, `zoneIdRegex`
- `referenceGeocodes`: array of city coordinates

### 3. Configuration Management Module

Create `backend/country_config.py`:

- `normalize_country_name(country_name)` - Convert country name to lowercase with hyphens (e.g., "South Africa" → "south-africa", "ZA" → lookup → "south-africa")
- `load_country_config(country_name)` - Load JSON config from `templates/country-rules/{country-name}.json`
- `get_base_prompt()` - Load base prompt template from `templates/base-prompt.txt`
- `build_final_prompt(address, country_name)` - Load base prompt, load country config, replace `{address}` and `{configurable_rules}` placeholders with actual values
- Handle missing country config gracefully (fallback to "south-africa" or error)

### 4. Modify LLM Validator

Update `backend/llm_validator.py`:

- Modify `validate_address()` to accept `country_name` parameter (optional, defaults to "south-africa")
- Use `country_config.build_final_prompt(address, country_name)` to build the prompt
- The function will:
- Load base prompt template from `templates/base-prompt.txt`
- Load country config JSON from `templates/country-rules/{country-name}.json`
- Replace `{address}` placeholder with actual address
- Replace `{configurable_rules}` placeholder with formatted JSON config content
- Remove all hardcoded SA-specific prompt content

### 5. Update API Endpoints

Modify `backend/app.py`:

- Update `/api/validate-single` to extract `country` from request body (from destination details)
- Look for `country`, `countryName`, or `countryCode` in request data
- Use `country_config.normalize_country_name()` to convert to file format (e.g., "south-africa")
- Pass normalized country name to `llm_validator.validate_address(address, country_name)`
- Default to "south-africa" if country not provided (for backward compatibility)
- Update `/api/validate-batch` similarly to extract country from each address or batch-level country

### 6. Additional Configurable Fields Review

Verify if these should also be configurable:

- Confidence scoring weights (currently hardcoded: -25 for missing street, -20 for missing city, etc.)
- Confidence level thresholds (90-100 High, 70-89 Medium, etc.)
- Coordinate validation distance threshold (currently 2km)
- JSON output schema structure
- Address parsing logic (currently SA-specific)

### 7. Migration and Backward Compatibility

- Ensure existing SA functionality continues to work
- Default to "south-africa" if country not specified
- Create initial `templates/country-rules/south-africa.json` from current hardcoded SA values in `llm_validator.py` and `sa_data.py`
- Map existing SA data structure to new JSON schema format

## Files to Modify/Create

### New Files:

- `backend/templates/base-prompt.txt` - Base validation prompt template with `{address}` and `{configurable_rules}` placeholders
- `backend/templates/country-rules/south-africa.json` - SA configuration JSON (contains normalization, validation rules, referenceGeocodes)
- `backend/country_config.py` - Configuration management module for loading prompts and configs

### Modified Files:

- `backend/llm_validator.py` - Remove hardcoded prompt, use `country_config.build_final_prompt()` to build dynamic prompt
- `backend/app.py` - Extract country from request destination details and pass to validator

### Files to Review:

- `backend/validator.py` - May need country-aware rule-based validation
- `backend/sa_data.py` - Consider if this should be migrated to config system

### To-dos

- [ ] Create directory structure: templates/, templates/country-rules/
- [ ] Create templates/base-prompt.txt with provided base prompt template (with {address} and {configurable_rules} placeholders)
- [ ] Create templates/country-rules/south-africa.json with SA configuration based on provided schema
- [ ] Create country_config.py with functions to normalize country names, load base prompt, load country configs, and build final prompt
- [ ] Modify llm_validator.py to accept country_name parameter and use country_config.build_final_prompt() instead of hardcoded prompt
- [ ] Update /api/validate-single to extract country from request destination details and pass to validator
- [ ] Update /api/validate-batch to extract country from request and pass to validator
- [ ] Review and document which additional fields (confidence scoring, thresholds) should be configurable