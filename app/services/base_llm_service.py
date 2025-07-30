"""
Base LLM Service - Core enhancement logic for all LLM operations

This module contains the fundamental LLM enhancement methods used by both
ContractLLMService (batch processing) and IterativeLLMService (real-time processing).
"""

import json
import re
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal

from app.utils.llm_utils import call_ollama
from app.database import db
from app.database.models import Prospect, InferredProspectData, LLMOutput
from app.services.optimized_prompts import get_naics_prompt, get_value_prompt, get_title_prompt
from app.utils.naics_lookup import get_naics_description, validate_naics_code
from app.services.set_aside_standardization import SetAsideStandardizer, StandardSetAside
from app.utils.logger import logger


class BaseLLMService:
    """
    Base service containing all core LLM enhancement logic.
    This class is designed to be inherited by specialized services.
    """
    
    def __init__(self, model_name: str = 'qwen3:latest'):
        self.model_name = model_name
        self.set_aside_standardizer = SetAsideStandardizer()
    
    def parse_existing_naics(self, naics_str: Optional[str]) -> Dict[str, Optional[str]]:
        """Parse existing NAICS codes from source data formats and standardize them
        
        Handles various formats found across different agencies:
        1. "334516 | Description" (pipe separator - preferred format)
        2. "334516 - Description" (hyphen separator)
        3. "334516 : Description" (colon separator - HHS format)
        4. "334516 Description" (space-separated)
        5. "334516" (just the 6-digit code)
        6. "334516.0" (numeric with decimal point - DOT/SSA format)
        
        Returns dict with 'code', 'description', and 'standardized_format' keys.
        The standardized_format will always be "334516 | Description" format.
        """
        if not naics_str:
            return {'code': None, 'description': None, 'standardized_format': None}
        
        naics_str = str(naics_str).strip()
        
        # Handle TBD placeholder values from data sources
        if naics_str.upper() in ['TBD', 'TO BE DETERMINED', 'N/A', 'NA']:
            return {'code': None, 'description': None, 'standardized_format': None}
        
        # Preprocess: Handle numeric NAICS codes with decimal points (e.g., "336510.0" -> "336510")
        # This fixes issues from data sources that parse NAICS as numeric values
        # Only process valid 6-digit NAICS codes, ignore invalid ones like "0.0", "2025.0", etc.
        if re.match(r'^[1-9]\d{5}\.0+$', naics_str):
            naics_str = naics_str.split('.')[0]
        
        # Handle different NAICS formats from source data - ordered by specificity
        patterns = [
            (r'(\d{6})\s*\|\s*(.*)', 'pipe'),      # "334516 | Description" (already standardized)
            (r'(\d{6})\s*:\s*(.*)', 'colon'),      # "334516 : Description" (HHS format)
            (r'(\d{6})\s*-\s*(.*)', 'hyphen'),     # "334516 - Description"
            (r'(\d{6})\s+([^0-9].*)', 'space'),    # "334516 Description" (space + non-digit)
            (r'(\d{6})$', 'code_only')             # Just the code
        ]
        
        for pattern, format_type in patterns:
            match = re.match(pattern, naics_str)
            if match:
                code = match.group(1)
                description = match.group(2).strip() if len(match.groups()) > 1 and match.group(2) else None
                
                # If no description found, try to get official description from lookup
                if not description:
                    description = get_naics_description(code)
                
                # Create standardized format
                if description:
                    standardized_format = f"{code} | {description}"
                else:
                    standardized_format = code
                
                return {
                    'code': code,
                    'description': description,
                    'standardized_format': standardized_format,
                    'original_format': format_type
                }
        
        # Fallback for unexpected formats - try to get description if it looks like a valid code
        description = None
        if validate_naics_code(naics_str):
            description = get_naics_description(naics_str)
        
        standardized_format = f"{naics_str} | {description}" if description else naics_str
        
        return {
            'code': naics_str,
            'description': description,
            'standardized_format': standardized_format,
            'original_format': 'unknown'
        }
    
    def extract_naics_from_extra_field(self, extra_data: Any) -> Dict[str, Optional[str]]:
        """Extract NAICS information from the extra field JSON data"""
        if not extra_data:
            return {'code': None, 'description': None, 'found_in_extra': False}
        
        # Handle case where extra is stored as JSON string
        if isinstance(extra_data, str):
            try:
                extra_data = json.loads(extra_data)
            except (json.JSONDecodeError, TypeError):
                return {'code': None, 'description': None, 'found_in_extra': False}
        
        if not isinstance(extra_data, dict):
            return {'code': None, 'description': None, 'found_in_extra': False}
        
        code = None
        description = None
        
        # 1. Acquisition Gateway pattern: "naics_code": "236220"
        if 'naics_code' in extra_data and extra_data['naics_code']:
            potential_code = str(extra_data['naics_code']).strip()
            if re.match(r'^\d{6}$', potential_code):
                code = potential_code
                description = None  # Acquisition Gateway doesn't include description
        
        # 2. Health and Human Services pattern: "primary_naics": "334516 : Analytical Laboratory Instrument Manufacturing"
        elif 'primary_naics' in extra_data and extra_data['primary_naics']:
            primary_naics = str(extra_data['primary_naics']).strip()
            if primary_naics.upper() != 'TBD':  # Skip "To Be Determined" entries
                # Use standardized parser for all formats
                parsed = self.parse_existing_naics(primary_naics)
                code = parsed['code']
                description = parsed['description']
        
        # 3. Fallback: Search for other common NAICS field names
        if not code:
            naics_keys = ['naics', 'industry_code', 'classification', 'sector', 'naics_primary']
            for key in naics_keys:
                if key in extra_data and extra_data[key]:
                    potential_value = str(extra_data[key]).strip()
                    
                    # Skip TBD/placeholder values
                    if potential_value.upper() in ['TBD', 'TO BE DETERMINED', 'N/A', 'NULL', '']:
                        continue
                        
                    # Use standardized parser for consistent handling
                    parsed = self.parse_existing_naics(potential_value)
                    if parsed['code']:
                        code = parsed['code']
                        description = parsed['description']
                        break
        
        # 4. Last resort: Search all values for any 6-digit numbers that could be NAICS codes
        if not code:
            for key, value in extra_data.items():
                if isinstance(value, (str, int)):
                    value_str = str(value)
                    # Look for 6-digit numbers
                    matches = re.findall(r'\b(\d{6})\b', value_str)
                    for potential_code in matches:
                        # Basic validation - NAICS codes start with digits 1-9 (not 0)
                        if potential_code[0] in '123456789':
                            # Try to parse the full value to get description if present
                            parsed = self.parse_existing_naics(value_str)
                            if parsed['code'] == potential_code:
                                code = parsed['code']
                                description = parsed['description']
                                break
                            else:
                                # Fallback to just the code
                                code = potential_code
                                break
                
                if code:  # Break outer loop if found
                    break
        
        found_in_extra = code is not None
        return {
            'code': code,
            'description': description,
            'found_in_extra': found_in_extra
        }
    
    def _log_llm_output(self, prospect_id: str, enhancement_type: str, prompt: str, 
                        response: str, parsed_result: Dict, success: bool, 
                        error_message: str = None, processing_time: float = None):
        """Log LLM output to database"""
        try:
            output = LLMOutput(
                prospect_id=prospect_id,
                enhancement_type=enhancement_type,
                prompt=prompt,
                response=response,
                parsed_result=parsed_result,
                success=success,
                error_message=error_message,
                processing_time=processing_time
            )
            db.session.add(output)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to log LLM output: {e}")
            db.session.rollback()
    
    def classify_naics_with_llm(self, title: str, description: str, prospect_id: str = None, 
                               agency: str = None, contract_type: str = None, set_aside: str = None, 
                               estimated_value: str = None, additional_info: str = None) -> Dict:
        """
        NAICS Classification using qwen3:8b with all available prospect information.
        
        New approach:
        1. LLM analyzes ALL available info to determine NAICS codes
        2. Descriptions are looked up from official NAICS database
        3. Separates classification from description for accuracy
        """
        # Build comprehensive prompt with all available information
        prompt = get_naics_prompt(
            title=title,
            description=description,
            agency=agency,
            contract_type=contract_type,
            set_aside=set_aside,
            estimated_value=estimated_value,
            additional_info=additional_info
        )
        
        start_time = time.time()
        response = call_ollama(prompt, self.model_name)
        processing_time = time.time() - start_time
        
        try:
            # Clean response of any think tags
            cleaned_response = response
            if response:
                cleaned_response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE).strip()
            
            # Check if cleaned_response is valid for JSON parsing
            if not cleaned_response:
                self._log_llm_output(prospect_id, 'naics_classification', prompt, response, '[]', False, 'Empty response after cleaning', processing_time)
                return []
                
            parsed = json.loads(cleaned_response)
            
            # Process array response from LLM
            if not isinstance(parsed, list):
                raise ValueError("LLM response must be an array of NAICS codes")
                
            # LLM returned multiple NAICS codes
            codes = sorted(parsed, key=lambda x: x.get('confidence', 0), reverse=True)
            
            # Process each code and get official description
            processed_codes = []
            for code_info in codes[:3]:  # Limit to top 3
                code = code_info.get('code')
                if code and validate_naics_code(code):
                    # Get official description from lookup
                    official_description = get_naics_description(code)
                    processed_codes.append({
                        'code': code,
                        'description': official_description,
                        'confidence': code_info.get('confidence', 0.8)
                    })
            
            # Primary code is the highest confidence valid one
            primary = processed_codes[0] if processed_codes else {'code': None, 'description': None, 'confidence': 0.0}
            result = {
                'code': primary.get('code'),
                'description': primary.get('description'),
                'confidence': primary.get('confidence', 0.0),
                'all_codes': processed_codes
            }
            
            # Log successful output
            if prospect_id:
                self._log_llm_output(
                    prospect_id=prospect_id,
                    enhancement_type='naics_classification',
                    prompt=prompt,
                    response=response,
                    parsed_result=result,
                    success=True,
                    processing_time=processing_time
                )
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse NAICS classification response: {e}")
            error_message = f"JSON parse error: {str(e)}"
            
            # Log failed output
            if prospect_id:
                self._log_llm_output(
                    prospect_id=prospect_id,
                    enhancement_type='naics_classification',
                    prompt=prompt,
                    response=response,
                    parsed_result={},
                    success=False,
                    error_message=error_message,
                    processing_time=processing_time
                )
            
            return {
                'code': None,
                'description': None,
                'confidence': 0.0,
                'all_codes': []
            }
        except Exception as e:
            logger.error(f"Error in NAICS classification: {e}")
            return {
                'code': None,
                'description': None,
                'confidence': 0.0,
                'all_codes': []
            }
    
    def parse_contract_value_with_llm(self, value_text: str, prospect_id: str = None) -> Dict[str, Optional[float]]:
        """
        Parse contract value text using LLM for intelligent understanding.
        Handles complex formats like ranges, estimates, and various text formats.
        
        Returns dict with 'single', 'min', and 'max' values.
        """
        prompt = get_value_prompt(value_text)
        
        start_time = time.time()
        response = call_ollama(prompt, self.model_name)
        processing_time = time.time() - start_time
        
        try:
            # Clean response of any think tags
            cleaned_response = response
            if response:
                cleaned_response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE).strip()
            
            # Check if cleaned_response is valid for JSON parsing
            if not cleaned_response:
                self._log_llm_output(prospect_id, 'naics_classification', prompt, response, '[]', False, 'Empty response after cleaning', processing_time)
                return []
                
            parsed = json.loads(cleaned_response)
            
            # Extract values ensuring they're floats or None
            result = {
                'single': float(parsed.get('single')) if parsed.get('single') is not None else None,
                'min': float(parsed.get('min')) if parsed.get('min') is not None else None,
                'max': float(parsed.get('max')) if parsed.get('max') is not None else None,
                'confidence': parsed.get('confidence', 1.0)
            }
            
            # Validate the results
            if result['single'] is not None and result['single'] < 0:
                result['single'] = None
            if result['min'] is not None and result['min'] < 0:
                result['min'] = None
            if result['max'] is not None and result['max'] < 0:
                result['max'] = None
            
            # Log successful output
            if prospect_id:
                self._log_llm_output(
                    prospect_id=prospect_id,
                    enhancement_type='value_parsing',
                    prompt=prompt,
                    response=response,
                    parsed_result=result,
                    success=True,
                    processing_time=processing_time
                )
            
            return result
            
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse value response: {e}")
            
            # Log failed output
            if prospect_id:
                self._log_llm_output(
                    prospect_id=prospect_id,
                    enhancement_type='value_parsing',
                    prompt=prompt,
                    response=response,
                    parsed_result={},
                    success=False,
                    error_message=str(e),
                    processing_time=processing_time
                )
            
            return {'single': None, 'min': None, 'max': None, 'confidence': 0.0}
    
    def enhance_title_with_llm(self, title: str, description: str, agency: str = "", prospect_id: str = None) -> Dict[str, Any]:
        """
        Enhance a prospect title to be clearer and more descriptive.
        Returns a dict with 'enhanced_title', 'confidence', and 'reasoning'.
        """
        prompt = get_title_prompt(title, description, agency)
        
        start_time = time.time()
        response = call_ollama(prompt, self.model_name)
        processing_time = time.time() - start_time
        
        try:
            # Clean response of any think tags
            cleaned_response = response
            if response:
                cleaned_response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE).strip()
            
            # Check if cleaned_response is valid for JSON parsing
            if not cleaned_response:
                self._log_llm_output(prospect_id, 'naics_classification', prompt, response, '[]', False, 'Empty response after cleaning', processing_time)
                return []
                
            parsed = json.loads(cleaned_response)
            
            result = {
                'enhanced_title': parsed.get('enhanced_title', '').strip(),
                'confidence': parsed.get('confidence', 0.8),
                'reasoning': parsed.get('reasoning', '')
            }
            
            # Validate that we got an actual enhancement
            if not result['enhanced_title'] or result['enhanced_title'] == title:
                result['enhanced_title'] = None
                result['confidence'] = 0.0
            
            # Log successful output
            if prospect_id:
                self._log_llm_output(
                    prospect_id=prospect_id,
                    enhancement_type='title_enhancement',
                    prompt=prompt,
                    response=response,
                    parsed_result=result,
                    success=True,
                    processing_time=processing_time
                )
            
            return result
            
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"Failed to parse title enhancement response: {e}")
            
            # Log failed output
            if prospect_id:
                self._log_llm_output(
                    prospect_id=prospect_id,
                    enhancement_type='title_enhancement',
                    prompt=prompt,
                    response=response,
                    parsed_result={},
                    success=False,
                    error_message=str(e),
                    processing_time=processing_time
                )
            
            return {'enhanced_title': None, 'confidence': 0.0, 'reasoning': ''}
    
    def standardize_set_aside_with_llm(self, set_aside_text: str, prospect_id: str = None, prospect: 'Prospect' = None) -> Optional[StandardSetAside]:
        """
        Standardize set-aside values using pure LLM-based classification.
        This provides intelligent, context-aware categorization for all inputs.
        Now includes additional data sources like DHS small_business_program.
        """
        # Gather comprehensive set-aside data from all available sources
        comprehensive_data = self._get_comprehensive_set_aside_data(set_aside_text, prospect)
        
        if not comprehensive_data or not comprehensive_data.strip():
            return StandardSetAside.NOT_AVAILABLE
            
        try:
            # Use LLM for all set-aside classification with comprehensive data
            llm_result = self._classify_set_aside_with_llm(comprehensive_data, prospect_id)
            if llm_result:
                if prospect_id:
                    logger.info(f"LLM set-aside classification for prospect {prospect_id}: '{comprehensive_data}' -> {llm_result.code}")
                return llm_result
            
            # If LLM fails completely, default to N/A
            logger.warning(f"LLM classification failed for set-aside '{comprehensive_data}', defaulting to N/A")
            return StandardSetAside.NOT_AVAILABLE
            
        except Exception as e:
            logger.error(f"Error in LLM set-aside classification for '{comprehensive_data}': {e}")
            return StandardSetAside.NOT_AVAILABLE
    
    def _get_comprehensive_set_aside_data(self, set_aside_text: str, prospect: Optional['Prospect'] = None) -> str:
        """
        Gather comprehensive set-aside data from all available sources.
        
        For DHS prospects, this includes checking the extra JSON for original_small_business_program
        data that might not have been properly consolidated into the main set_aside field.
        """
        # Start with the main set_aside field
        main_set_aside = (set_aside_text or "").strip()
        
        # Check for additional data sources in prospect.extra
        additional_data = ""
        field_found = None
        if prospect and prospect.extra and isinstance(prospect.extra, dict):
            # Check for DHS small_business_program data
            small_business_program = prospect.extra.get('original_small_business_program', '').strip()
            if small_business_program and small_business_program.lower() not in ['none', 'n/a', 'tbd', '']:
                additional_data = small_business_program
                field_found = 'original_small_business_program'
        
        # Log which field was found for debugging
        if field_found:
            logger.info(f"Found additional set-aside data in field '{field_found}': '{additional_data}'")
        
        # Combine data sources intelligently
        if main_set_aside and additional_data:
            # Both sources have data - combine them
            if main_set_aside.lower() != additional_data.lower():  # Avoid duplicate info
                comprehensive_data = f"Set-aside: {main_set_aside}; Small Business Program: {additional_data}"
                logger.info(f"Combined set-aside data: '{comprehensive_data}'")
                return comprehensive_data
            else:
                logger.info(f"Same data in both sources, using: '{main_set_aside}'")
                return main_set_aside  # Same info, just use one
        elif main_set_aside:
            # Only main field has data
            logger.info(f"Using main set_aside field: '{main_set_aside}'")
            return main_set_aside
        elif additional_data:
            # Only additional source has data (like DHS small_business_program)
            comprehensive_data = f"Small Business Program: {additional_data}"
            logger.info(f"Using additional data source: '{comprehensive_data}'")
            return comprehensive_data
        else:
            # No meaningful data found
            logger.info("No meaningful set-aside data found in any source")
            return ""
    
    def _classify_set_aside_with_llm(self, set_aside_text: str, prospect_id: str = None) -> Optional[StandardSetAside]:
        """
        Use LLM to intelligently classify set-aside values into standardized categories.
        """
        try:
            # Get the LLM prompt from the standardizer
            prompt = self.set_aside_standardizer.get_llm_prompt().format(set_aside_text)
            
            # Call the LLM
            start_time = time.time()
            response = call_ollama(prompt, self.model_name)
            processing_time = time.time() - start_time
            
            if not response:
                logger.warning(f"LLM call failed for set-aside classification: '{set_aside_text}'")
                
                # Log failed output
                if prospect_id:
                    self._log_llm_output(
                        prospect_id=prospect_id,
                        enhancement_type='set_aside_standardization',
                        prompt=prompt,
                        response='',
                        parsed_result={},
                        success=False,
                        error_message="LLM call failed - no response received",
                        processing_time=processing_time
                    )
                return None
                
            # Clean and parse the response
            response_text = self._clean_llm_response(response)
            
            # Map the response back to the enum with fuzzy matching
            result = self._match_response_to_enum(response_text, set_aside_text)
            if result:
                logger.info(f"LLM classified set-aside '{set_aside_text}' as {result.code}")
                
                # Log successful output
                if prospect_id:
                    self._log_llm_output(
                        prospect_id=prospect_id,
                        enhancement_type='set_aside_standardization',
                        prompt=prompt,
                        response=response,
                        parsed_result={
                            'standardized_code': result.code,
                            'standardized_label': result.label,
                            'original_input': set_aside_text,
                            'llm_response': response_text
                        },
                        success=True,
                        processing_time=processing_time
                    )
                
                return result
            
            # If no match found, log the unexpected response
            logger.warning(f"LLM returned unrecognized set-aside classification: '{response_text}' for input '{set_aside_text}'")
            
            # Log failed output for unrecognized response
            if prospect_id:
                self._log_llm_output(
                    prospect_id=prospect_id,
                    enhancement_type='set_aside_standardization',
                    prompt=prompt,
                    response=response,
                    parsed_result={'llm_response': response_text, 'original_input': set_aside_text},
                    success=False,
                    error_message=f"Unrecognized LLM response: '{response_text}'",
                    processing_time=processing_time
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in LLM set-aside classification for '{set_aside_text}': {e}")
            
            # Log failed output for exceptions
            if prospect_id:
                self._log_llm_output(
                    prospect_id=prospect_id,
                    enhancement_type='set_aside_standardization',
                    prompt=prompt if 'prompt' in locals() else '',
                    response=response if 'response' in locals() else '',
                    parsed_result={'original_input': set_aside_text},
                    success=False,
                    error_message=str(e),
                    processing_time=time.time() - start_time if 'start_time' in locals() else None
                )
            
            return None
    
    def _clean_llm_response(self, response: str) -> str:
        """
        Clean LLM response to extract just the classification result.
        """
        response = response.strip()
        
        # Remove common LLM artifacts like thinking tags
        response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
        response = re.sub(r'<thinking>.*?</thinking>', '', response, flags=re.DOTALL)
        
        # Remove extra explanations - keep only the first line if it's a category
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        if lines:
            # Use the first non-empty line
            response = lines[0]
        
        return response.strip()
    
    def _match_response_to_enum(self, response_text: str, original_input: str) -> Optional[StandardSetAside]:
        """
        Match LLM response to StandardSetAside enum with fuzzy matching.
        """
        if not response_text:
            return None
            
        # First try exact match (case-insensitive)
        for set_aside_type in StandardSetAside:
            if set_aside_type.value.lower() == response_text.lower():
                return set_aside_type
        
        # Try fuzzy matching for common variations
        response_lower = response_text.lower()
        
        # Handle common LLM response variations
        if 'small business' in response_lower or response_lower == 'small':
            return StandardSetAside.SMALL_BUSINESS
        elif '8(a)' in response_lower or 'eight a' in response_lower or response_lower == '8a':
            return StandardSetAside.EIGHT_A
        elif 'hubzone' in response_lower or 'hub zone' in response_lower:
            return StandardSetAside.HUBZONE
        elif 'women' in response_lower and 'owned' in response_lower:
            return StandardSetAside.WOMEN_OWNED
        elif 'veteran' in response_lower and 'owned' in response_lower:
            return StandardSetAside.VETERAN_OWNED
        elif 'full and open' in response_lower or response_lower == 'unrestricted':
            return StandardSetAside.FULL_AND_OPEN
        elif 'sole source' in response_lower:
            return StandardSetAside.SOLE_SOURCE
        elif response_lower in ['n/a', 'na', 'not available', 'none', 'unknown']:
            return StandardSetAside.NOT_AVAILABLE
            
        return None
    
    def process_single_prospect_enhancement(self, prospect: Prospect, 
                                          enhancement_type: str = "all",
                                          progress_callback: Optional[callable] = None) -> Dict[str, bool]:
        """
        Process all enhancements for a single prospect.
        
        Args:
            prospect: The prospect to enhance
            enhancement_type: Type of enhancement to perform ("all", "values", "titles", "naics", "set_asides")
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict with enhancement results for each type
        """
        results = {
            'values': False,
            'naics': False,
            'titles': False,
            'set_asides': False
        }
        
        # Ensure extra is a dict
        from app.services.llm_service_utils import ensure_extra_is_dict
        ensure_extra_is_dict(prospect)
        
        # Process value enhancement
        if enhancement_type in ["values", "all"]:
            if progress_callback:
                progress_callback({"status": "processing", "field": "values", "prospect_id": prospect.id})
            
            value_to_parse = None
            if prospect.estimated_value_text and not prospect.estimated_value_single:
                value_to_parse = prospect.estimated_value_text
            elif prospect.estimated_value and not prospect.estimated_value_single:
                value_to_parse = str(prospect.estimated_value)
            
            if value_to_parse:
                parsed_value = self.parse_contract_value_with_llm(value_to_parse, prospect_id=prospect.id)
                if parsed_value['single'] is not None:
                    prospect.estimated_value_single = float(parsed_value['single'])
                    prospect.estimated_value_min = float(parsed_value['min']) if parsed_value['min'] else float(parsed_value['single'])
                    prospect.estimated_value_max = float(parsed_value['max']) if parsed_value['max'] else float(parsed_value['single'])
                    if not prospect.estimated_value_text:
                        prospect.estimated_value_text = value_to_parse
                    results['values'] = True
        
        # Process NAICS classification
        if enhancement_type in ["naics", "all"]:
            if progress_callback:
                progress_callback({"status": "processing", "field": "naics", "prospect_id": prospect.id})
            
            if prospect.description and (not prospect.naics or prospect.naics_source != 'llm_inferred'):
                # First check extra field
                extra_naics = self.extract_naics_from_extra_field(prospect.extra)
                
                if extra_naics['found_in_extra'] and extra_naics['code']:
                    prospect.naics = extra_naics['code']
                    prospect.naics_description = extra_naics['description']
                    prospect.naics_source = 'original'
                    
                    prospect.extra['naics_extracted_from_extra'] = {
                        'extracted_at': datetime.now(timezone.utc).isoformat(),
                        'original_code': extra_naics['code'],
                        'original_description': extra_naics['description']
                    }
                    results['naics'] = True
                else:
                    # Use LLM classification
                    classification = self.classify_naics_with_llm(
                        prospect.title, 
                        prospect.description, 
                        prospect_id=prospect.id,
                        agency=prospect.agency,
                        contract_type=prospect.contract_type,
                        set_aside=prospect.set_aside,
                        estimated_value=prospect.estimated_value_text
                    )
                    
                    if classification['code']:
                        prospect.naics = classification['code']
                        prospect.naics_description = classification['description']
                        prospect.naics_source = 'llm_inferred'
                        
                        prospect.extra['llm_classification'] = {
                            'naics_confidence': classification['confidence'],
                            'model_used': self.model_name,
                            'classified_at': datetime.now(timezone.utc).isoformat()
                        }
                        results['naics'] = True
        
        # Process title enhancement
        if enhancement_type in ["titles", "all"]:
            if progress_callback:
                progress_callback({"status": "processing", "field": "titles", "prospect_id": prospect.id})
            
            if prospect.title and not prospect.ai_enhanced_title:
                enhanced_title = self.enhance_title_with_llm(
                    prospect.title,
                    prospect.description or "",
                    prospect.agency or "",
                    prospect_id=prospect.id
                )
                
                if enhanced_title['enhanced_title']:
                    prospect.ai_enhanced_title = enhanced_title['enhanced_title']
                    
                    prospect.extra['llm_title_enhancement'] = {
                        'confidence': enhanced_title['confidence'],
                        'reasoning': enhanced_title.get('reasoning', ''),
                        'original_title': prospect.title,
                        'enhanced_at': datetime.now(timezone.utc).isoformat(),
                        'model_used': self.model_name
                    }
                    results['titles'] = True
        
        # Process set-aside standardization
        if enhancement_type in ["set_asides", "all"]:
            if progress_callback:
                progress_callback({"status": "processing", "field": "set_asides", "prospect_id": prospect.id})
            
            # Process if not already standardized (includes prospects with NULL set_aside but potential extra data)
            if not prospect.set_aside_standardized:
                # Get comprehensive data BEFORE calling LLM
                comprehensive_data = self._get_comprehensive_set_aside_data(prospect.set_aside, prospect)
                if comprehensive_data:
                    standardized = self.standardize_set_aside_with_llm(comprehensive_data, prospect_id=prospect.id, prospect=prospect)
                    if standardized:
                        prospect.set_aside_standardized = standardized.code
                        prospect.set_aside_standardized_label = standardized.label
                        
                        prospect.extra['set_aside_standardization'] = {
                            'original_set_aside': prospect.set_aside,
                            'comprehensive_data_used': comprehensive_data,
                            'standardized_at': datetime.now(timezone.utc).isoformat()
                        }
                        results['set_asides'] = True
        
        # Update timestamps if any enhancements were made
        if any(results.values()):
            from app.services.llm_service_utils import update_prospect_timestamps
            update_prospect_timestamps(prospect, self.model_name)
        
        return results