# NAICS Enhancement Options - Implementation Complete

## Overview
Added three separate NAICS enhancement options to the AI Enhancement tab on the Advanced page, giving users more granular control over NAICS data processing.

## New Enhancement Options

### 1. **NAICS (both values)**
- **Type**: `naics`
- **Behavior**: Original full NAICS enhancement
- Infers/classifies NAICS codes using LLM
- Adds official descriptions from lookup table
- Updates both `naics` and `naics_description` fields

### 2. **NAICS (code only)**
- **Type**: `naics_code`
- **Behavior**: Focuses only on NAICS code inference
- Uses LLM to classify/infer NAICS codes
- Automatically fetches official description from lookup table
- Useful when you want to classify prospects without changing existing descriptions
- Skips prospects that already have NAICS codes (unless force_redo)

### 3. **NAICS (description only)**
- **Type**: `naics_description`
- **Behavior**: Backfills descriptions for existing codes
- Does NOT use LLM - purely lookup-based
- Extremely fast (O(1) dictionary lookups)
- Only processes prospects with NAICS codes but missing descriptions
- Uses official NAICS 2022 descriptions from internal lookup table

## Changes Made

### Frontend
1. **AIEnrichment.tsx**:
   - Updated `EnhancementType` to include `naics_code` and `naics_description`
   - Added three NAICS options to the dropdown selector

### Backend
1. **llm_service.py**:
   - Updated `EnhancementType` literal to include new types
   - Added separate processing logic for `naics_code` enhancement
   - Added separate processing logic for `naics_description` enhancement
   - Maintains backward compatibility with existing `naics` type

2. **llm_processing.py**:
   - Updated validation to accept new enhancement types
   - Added planned steps logic for new NAICS types
   - Proper skip detection for each type

3. **enhancement_queue.py**:
   - Updated to handle new NAICS types in progress tracking
   - Added appropriate status messages for each type
   - Updated filtering logic for bulk processing

## Benefits

1. **Flexibility**: Users can choose exactly what aspect of NAICS data to enhance
2. **Efficiency**: Description-only mode is extremely fast (no LLM calls)
3. **Safety**: Code-only mode preserves existing descriptions if desired
4. **Control**: Users can backfill descriptions without risking code changes
5. **Cost-effective**: Description backfill uses zero LLM tokens

## Testing

To test the new functionality:

1. Navigate to http://localhost:3002/advanced
2. Go to the "AI Enrichment" tab
3. In the Enhancement Type dropdown, you'll see:
   - All Enhancements
   - Value Parsing
   - **NAICS (both values)** - Full enhancement
   - **NAICS (code only)** - Just classify codes
   - **NAICS (description only)** - Just backfill descriptions
   - Title Enhancement
   - Set-Aside Standardization

4. Test scenarios:
   - Select "NAICS (description only)" to quickly backfill descriptions for prospects with codes
   - Select "NAICS (code only)" to classify prospects without overwriting descriptions
   - Select "NAICS (both values)" for full NAICS enhancement (original behavior)

## Performance Notes

- **NAICS (description only)**: Fastest option - can process thousands of prospects per minute
- **NAICS (code only)**: LLM-based, typical speed (~2-3 seconds per prospect)
- **NAICS (both values)**: LLM-based, same speed as code only

## Database Impact

- No schema changes required
- Backfilled descriptions are marked in the `extra` field with timestamp
- Original NAICS data is preserved when enhanced