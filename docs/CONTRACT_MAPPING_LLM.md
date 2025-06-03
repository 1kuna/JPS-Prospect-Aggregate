# Contract Mapping and LLM Enhancement Documentation

## Overview

This document describes the contract data mapping and LLM enhancement functionality added to the JPS Prospect Aggregate system. The implementation follows a modular design that allows immediate use of core data while providing optional LLM-based enhancements using qwen3:8b via Ollama.

## Architecture

### 1. Database Schema Updates

New fields have been added to the `prospects` table to support standardized contract mapping:

#### Core Fields (Populated from Source Data)
- `estimated_value_text` - Original contract value as text
- `naics_description` - NAICS industry description
- `naics_source` - Source of NAICS code ('original', 'llm_inferred', 'llm_enhanced')

#### LLM-Enhanced Fields (Populated by qwen3:8b)
- `estimated_value_min` - Parsed minimum contract value
- `estimated_value_max` - Parsed maximum contract value
- `estimated_value_single` - Best single estimate value
- `primary_contact_email` - Extracted primary contact email
- `primary_contact_name` - Extracted primary contact name
- `ollama_processed_at` - Timestamp of LLM processing
- `ollama_model_version` - LLM model version used

### 2. Services

#### ContractMapperService (`app/services/contract_mapper_service.py`)
Handles mapping from various government sources to standardized schema:
- Supports 9 different government data sources (DOT, DHS, HHS, DOC, SSA, DOS, DOJ, Treasury, AcqGateway)
- Extracts NAICS codes from source data where available
- Preserves all source-specific fields in structured JSON `extra` field

#### ContractLLMService (`app/services/contract_llm_service.py`)
Provides modular LLM enhancement using qwen3:8b:
- **Value Parsing**: Extracts structured min/max/single values from text like "$1M-$5M"
- **Contact Extraction**: Identifies primary contact from various contact fields
- **NAICS Classification**: Classifies contracts without NAICS codes based on title/description

### 3. Migration Scripts

#### Database Migration
```bash
flask db upgrade
```
Applies the schema changes to add new contract mapping fields.

#### Data Migration (`scripts/migrate_contract_fields.py`)
```bash
python scripts/migrate_contract_fields.py [--with-llm]
```
- Migrates existing NAICS data to new format
- Extracts value text from extra JSON fields
- Restructures contact information for LLM processing
- Optional `--with-llm` flag runs initial LLM enhancement

#### LLM Enhancement (`scripts/enrichment/enhance_prospects_with_llm.py`)
```bash
python scripts/enrichment/enhance_prospects_with_llm.py [values|contacts|naics|all] [--limit N]
```
- Targeted enhancement of specific data types
- Batch processing with configurable limits
- Shows statistics before and after processing

## API Endpoints

### LLM Processing Control (`/api/llm/*`)

#### GET `/api/llm/status`
Returns current LLM processing statistics including:
- Total prospects and processing status
- NAICS coverage percentages
- Value parsing and contact extraction stats

#### POST `/api/llm/enhance`
Triggers LLM enhancement for prospects:
```json
{
    "enhancement_type": "values|contacts|naics|all",
    "limit": 100
}
```

#### POST `/api/llm/preview`
Preview enhancement for a single prospect without saving:
```json
{
    "prospect_id": "abc123",
    "enhancement_types": ["values", "contacts", "naics"]
}
```

## Usage Workflow

### 1. Initial Setup
```bash
# Apply database migration
flask db upgrade

# Migrate existing data (no LLM required)
python scripts/migrate_contract_fields.py
```

### 2. Check Enhancement Status
```bash
python scripts/enrichment/enhance_prospects_with_llm.py --stats
```

### 3. Run LLM Enhancement (Requires Ollama)
```bash
# Ensure Ollama is running with qwen3:8b
ollama serve
ollama pull qwen3:8b

# Enhance contract values
python scripts/enrichment/enhance_prospects_with_llm.py values --limit 100

# Enhance all fields
python scripts/enrichment/enhance_prospects_with_llm.py all
```

### 4. Use API for Programmatic Control
```python
import requests

# Check status
response = requests.get('http://localhost:5000/api/llm/status')
stats = response.json()

# Trigger enhancement
response = requests.post('http://localhost:5000/api/llm/enhance', 
    json={'enhancement_type': 'naics', 'limit': 50})
```

## Benefits of Modular Design

1. **Immediate Access**: Use 100% of data without waiting for LLM processing
2. **Incremental Enhancement**: Add LLM features when ready, in any order
3. **Rollback Safety**: LLM fields are separate - can disable without losing core data
4. **Performance Flexibility**: Core queries work fast without LLM dependencies
5. **Future-Proof**: Easy to swap qwen3:8b for newer models later

## Data Quality Improvements

- **NAICS Coverage**: From 97.4% to potentially 100% with LLM inference
- **Value Standardization**: Consistent numeric values from various text formats
- **Contact Consolidation**: Primary contact extracted from fragmented fields
- **Source Tracking**: Clear attribution of data origin vs LLM inference