<!-- f322b18e-c234-4adf-a425-8fb8b8a27c4d 11bb519e-b24d-4a6f-b348-34e6bed3c375 -->
# Country-Based Prompt and Configuration System

## Overview

Transform the hardcoded South African address validation system into a multi-country configurable system where:

- Base prompt template is stored in `templates/base-prompt.txt` with placeholders `{address}` and `{configurable_rules}`
- Country-specific configuration rules are stored in `templates/country-rules/{country-name}.json`
- The base prompt's `{configurable_rules}` placeholder is replaced with the JSON content from country rules file
- Country name comes from destination details in API requests
- No API endpoint needed - countries are added by creating new JSON files manually

## Implementation Plan

### 1. Directory Structure Setup

- Create `backend/prompts/` directory
- Create `backend/prompts/country_prompts/` directory  
- Create `backend/configs/` directory
- Extract base prompt from current hardcoded prompt in `llm_validator.py` → `prompts/base_prompt.txt`
- Create initial `prompts/country_prompts/south_africa.txt` with SA-specific content
- Create initial `configs/south_africa.json` with SA configuration

### 2. Country Configuration Schema

Define JSON schema for country configs (based on provided example):

- `countryCode` (e.g., "ZA")
- `countryName` (e.g., "South Africa")
- `normalization`: `streetAbbreviations`, `cityAbbreviations`, `otherAbbreviations`
- `validation`: `provinceConfig` (type, list), `postalCode` (formatRegex, ranges, maxLength), `coordinateBounds`, `zoneIdRegex`
- `referenceGeocodes`: array of city coordinates

### 3. Configuration Management Module

Create `backend/country_config.py`:

- `load_country_config(country_name)` - Load JSON config from `configs/{country_name}.json`
- `save_country_config(country_name, config)` - Save/overwrite config file
- `get_country_prompt(country_name)` - Load prompt from `prompts/country_prompts/{country_name}.txt`
- `save_country_prompt(country_name, prompt)` - Save/overwrite prompt file
- `get_base_prompt()` - Load base prompt from `prompts/base_prompt.txt`
- `build_final_prompt(base_prompt, country_prompt, country_config, address)` - Combine prompts and inject config data

### 4. API Endpoint for Country Configuration

Add to `backend/app.py`:

- `POST /api/configure-country` endpoint
- Accepts: `countryCode`, `countryName`, `prompt` (country-specific), `normalization`, `validation`, `referenceGeocodes`
- Normalizes country name to lowercase with underscores (e.g., "South Africa" → "south_africa")
- Saves prompt to `prompts/country_prompts/{country_name}.txt` (overwrites if exists)
- Saves config to `configs/{country_name}.json` (overwrites if exists)
- Returns success/error response

### 5. Modify LLM Validator

Update `backend/llm_validator.py`:

- Modify `validate_address()` to accept `country_name` parameter
- Load base prompt, country prompt, and country config
- Build final prompt by combining base + country prompt + injecting config data
- Handle missing country config gracefully (fallback to SA or error)
- Update prompt to use dynamic country-specific rules instead of hardcoded SA rules

### 6. Update API Endpoints

Modify `backend/app.py`:

- Update `/api/validate-single` to extract `country` from request (from destination details)
- Pass country name to `llm_validator.validate_address()`
- Normalize country name (handle variations like "South Africa", "south africa", "ZA" → "south_africa")
- Update `/api/validate-batch` similarly

### 7. Additional Configurable Fields Review

Verify if these should also be configurable:

- Confidence scoring weights (currently hardcoded: -25 for missing street, -20 for missing city, etc.)
- Confidence level thresholds (90-100 High, 70-89 Medium, etc.)
- Coordinate validation distance threshold (currently 2km)
- JSON output schema structure
- Address parsing logic (currently SA-specific)

### 8. Migration and Backward Compatibility

- Ensure existing SA functionality continues to work
- Default to "south_africa" if country not specified
- Create initial SA config and prompt files from current hardcoded values

## Files to Modify/Create

### New Files:

- `backend/prompts/base_prompt.txt` - Base validation prompt
- `backend/prompts/country_prompts/south_africa.txt` - SA-specific prompt
- `backend/configs/south_africa.json` - SA configuration
- `backend/country_config.py` - Configuration management module

### Modified Files:

- `backend/llm_validator.py` - Make country-aware, load prompts/configs dynamically
- `backend/app.py` - Add `/api/configure-country` endpoint, extract country from requests

### Files to Review:

- `backend/validator.py` - May need country-aware rule-based validation
- `backend/sa_data.py` - Consider if this should be migrated to config system

### To-dos

- [ ] Create directory structure: prompts/, prompts/country_prompts/, configs/
- [ ] Extract base prompt from llm_validator.py and save to prompts/base_prompt.txt
- [ ] Create prompts/country_prompts/south_africa.txt with SA-specific prompt content
- [ ] Create configs/south_africa.json with SA configuration based on provided schema
- [ ] Create country_config.py with functions to load/save prompts and configs
- [ ] Modify llm_validator.py to accept country_name, load prompts/configs, and build dynamic prompt
- [ ] Add POST /api/configure-country endpoint to app.py for dynamic country configuration
- [ ] Update /api/validate-single and /api/validate-batch to extract country from request and pass to validator
- [ ] Review and document which additional fields (confidence scoring, thresholds) should be configurable