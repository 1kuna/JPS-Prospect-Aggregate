"""
Modular LLM Service for Contract Data Enhancement
Uses qwen3:8b via Ollama for optional data enrichment
"""

import json
import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal

from app.utils.llm_utils import call_ollama
from app.database import db
from app.database.models import Prospect, InferredProspectData, LLMOutput
from app.services.optimized_prompts import get_naics_prompt, get_value_prompt, get_contact_prompt, get_title_prompt
from app.utils.naics_lookup import get_naics_description, validate_naics_code
import time

logger = logging.getLogger(__name__)


class ContractLLMService:
    """
    Service for enhancing contract data using qwen3:8b LLM.
    Designed to be modular and optional - can run independently of core data.
    """
    
    def __init__(self, model_name: str = 'qwen3:latest'):
        self.model_name = model_name
        self.batch_size = 50
    
    def _update_prospect_timestamp(self, prospect: Prospect):
        """Update prospect's ollama_processed_at timestamp for polling detection"""
        try:
            prospect.ollama_processed_at = datetime.now(timezone.utc)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to update prospect timestamp: {e}")
            db.session.rollback()
        
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
            
            parsed = json.loads(cleaned_response)
            
            # Handle both array response (new) and single object (backward compatibility)
            if isinstance(parsed, list):
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
            else:
                # Single code response (backward compatibility)
                code = parsed.get('code')
                if code and validate_naics_code(code):
                    official_description = get_naics_description(code)
                    confidence = parsed.get('confidence', 0.8)
                    
                    result = {
                        'code': code,
                        'description': official_description,
                        'confidence': confidence,
                        'all_codes': [{'code': code, 'description': official_description, 'confidence': confidence}]
                    }
                else:
                    result = {
                        'code': None,
                        'description': None,
                        'confidence': 0.0,
                        'all_codes': []
                    }
            
            # Log successful output
            if prospect_id:
                self._log_llm_output(prospect_id, 'naics', prompt, response, result, True, processing_time=processing_time)
            
            return result
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Error parsing NAICS response: {e}")
            error_result = {'code': None, 'description': None, 'confidence': 0.0, 'all_codes': []}
            
            # Log failed output
            if prospect_id:
                self._log_llm_output(prospect_id, 'naics', prompt, response, error_result, False, 
                                   error_message=str(e), processing_time=processing_time)
            
            return error_result
    
    def parse_contract_value_with_llm(self, value_text: str, prospect_id: str = None) -> Dict:
        """Value parsing using qwen3:8b
        
        Extracts contract values from messy text formats. Handles:
        - Range values: "$100K - $500K" -> {min: 100000, max: 500000}
        - Single values: "$250,000" -> {single: 250000}
        - Complex formats: "between 100 and 500 thousand" -> {min: 100000, max: 500000}
        
        The LLM is trained to understand various number formats, abbreviations (K, M, B),
        and contextual clues to extract accurate dollar amounts.
        """
        if not value_text:
            return {'min': None, 'max': None, 'single': None}

        prompt = get_value_prompt(value_text)
        start_time = time.time()
        response = call_ollama(prompt, self.model_name)
        processing_time = time.time() - start_time
        
        try:
            # Clean response of any think tags
            cleaned_response = response
            if response:
                cleaned_response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE).strip()
                
            parsed = json.loads(cleaned_response)
            result = {
                'min': parsed.get('min'),
                'max': parsed.get('max'),
                'single': parsed.get('single')
            }
            
            # Log successful output
            if prospect_id:
                self._log_llm_output(prospect_id, 'values', prompt, response, result, True, processing_time=processing_time)
            
            return result
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Error parsing value response: {e}")
            error_result = {'min': None, 'max': None, 'single': None}
            
            # Log failed output
            if prospect_id:
                self._log_llm_output(prospect_id, 'values', prompt, response, error_result, False,
                                   error_message=str(e), processing_time=processing_time)
            
            return error_result
    
    def extract_contact_with_llm(self, contact_data: Dict, prospect_id: str = None) -> Dict:
        """Contact extraction using qwen3:8b"""
        prompt = get_contact_prompt(contact_data)
        start_time = time.time()
        response = call_ollama(prompt, self.model_name)
        processing_time = time.time() - start_time
        
        try:
            # Clean response of any think tags
            cleaned_response = response
            if response:
                cleaned_response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE).strip()
                
            parsed = json.loads(cleaned_response)
            result = {
                'email': parsed.get('email'),
                'name': parsed.get('name'),
                'confidence': parsed.get('confidence', 0.8)
            }
            
            # Log successful output
            if prospect_id:
                self._log_llm_output(prospect_id, 'contacts', prompt, response, result, True, processing_time=processing_time)
            
            return result
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Error parsing contact response: {e}")
            error_result = {'email': None, 'name': None, 'confidence': 0.0}
            
            # Log failed output
            if prospect_id:
                self._log_llm_output(prospect_id, 'contacts', prompt, response, error_result, False,
                                   error_message=str(e), processing_time=processing_time)
            
            return error_result
    
    def enhance_title_with_llm(self, title: str, description: str, agency: str, prospect_id: str = None) -> Dict:
        """Title enhancement using qwen3:8b"""
        prompt = get_title_prompt(title, description, agency)
        start_time = time.time()
        response = call_ollama(prompt, self.model_name)
        processing_time = time.time() - start_time
        
        try:
            # Clean response of any think tags
            cleaned_response = response
            if response:
                cleaned_response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE).strip()
                
            parsed = json.loads(cleaned_response)
            result = {
                'enhanced_title': parsed.get('enhanced_title'),
                'confidence': parsed.get('confidence', 0.8),
                'reasoning': parsed.get('reasoning', '')
            }
            
            # Log successful output
            if prospect_id:
                self._log_llm_output(prospect_id, 'titles', prompt, response, result, True, processing_time=processing_time)
            
            return result
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Error parsing title response: {e}")
            error_result = {'enhanced_title': None, 'confidence': 0.0, 'reasoning': ''}
            
            # Log failed output
            if prospect_id:
                self._log_llm_output(prospect_id, 'titles', prompt, response, error_result, False,
                                   error_message=str(e), processing_time=processing_time)
            
            return error_result
    
    def _process_enhancement_batch(self, prospects: List[Prospect], enhancement_name: str, 
                                 processor_func, commit_batch_size: int = 100, emit_updates: bool = True) -> int:
        """
        Template method for processing enhancement batches.
        processor_func should take a prospect and return True if processed successfully.
        """
        logger.info(f"Starting {enhancement_name} for {len(prospects)} prospects...")
        processed_count = 0
        
        for i in range(0, len(prospects), self.batch_size):
            batch = prospects[i:i + self.batch_size]
            logger.info(f"Processing {enhancement_name} batch {i//self.batch_size + 1}/{(len(prospects) + self.batch_size - 1)//self.batch_size}")
            
            for prospect in batch:
                try:
                    if processor_func(prospect):
                        processed_count += 1
                        
                        # Commit immediately for real-time updates if enabled
                        if emit_updates:
                            try:
                                db.session.commit()
                                logger.debug(f"Committed {enhancement_name} for prospect {prospect.id}")
                            except Exception as e:
                                logger.error(f"Error committing individual update: {e}")
                                db.session.rollback()
                                continue
                except Exception as e:
                    logger.error(f"Error processing prospect {prospect.id}: {e}")
                    continue
            
            # Batch commit for non-real-time updates
            if not emit_updates and processed_count > 0 and processed_count % commit_batch_size == 0:
                try:
                    db.session.commit()
                    logger.info(f"Committed {processed_count} {enhancement_name} enhancements")
                except Exception as e:
                    logger.error(f"Error committing batch: {e}")
                    db.session.rollback()
        
        # Final commit
        try:
            db.session.commit()
            logger.info(f"Completed {enhancement_name} enhancement. Total processed: {processed_count}")
        except Exception as e:
            logger.error(f"Error in final commit: {e}")
            db.session.rollback()
            
        return processed_count
    
    def enhance_prospect_values(self, prospects: List[Prospect], commit_batch_size: int = 100) -> int:
        """
        Enhance prospects with parsed contract values.
        Returns count of successfully processed prospects.
        """
        def process_value_enhancement(prospect: Prospect) -> bool:
            # Skip if already processed
            if prospect.estimated_value_min is not None:
                return False
            
            # Try to parse from estimated_value_text first, then extra data
            value_text = prospect.estimated_value_text
            if not value_text and prospect.extra:
                extra_data = prospect.extra
                if isinstance(extra_data, str):
                    # Handle case where extra is stored as JSON string
                    try:
                        extra_data = json.loads(extra_data)
                    except (json.JSONDecodeError, TypeError):
                        extra_data = {}
                value_text = extra_data.get('estimated_value_text', '') if extra_data else ''
            
            if value_text:
                parsed_value = self.parse_contract_value_with_llm(value_text)
                
                if parsed_value['single'] is not None:
                    prospect.estimated_value_min = Decimal(str(parsed_value['min'])) if parsed_value['min'] else None
                    prospect.estimated_value_max = Decimal(str(parsed_value['max'])) if parsed_value['max'] else None
                    prospect.estimated_value_single = Decimal(str(parsed_value['single']))
                    prospect.ollama_processed_at = datetime.now(timezone.utc)
                    prospect.ollama_model_version = self.model_name
                    
                    # Update timestamp for polling detection
                    self._update_prospect_timestamp(prospect)
                    
                    return True
            
            return False
        
        return self._process_enhancement_batch(prospects, "value parsing", process_value_enhancement, commit_batch_size)
    
    def enhance_prospect_contacts(self, prospects: List[Prospect], commit_batch_size: int = 100) -> int:
        """
        Enhance prospects with extracted contact information.
        Returns count of successfully processed prospects.
        """
        def process_contact_enhancement(prospect: Prospect) -> bool:
            # Skip if already processed
            if prospect.primary_contact_email is not None:
                return False
            
            # Extract contact data from extra field
            extra_data = prospect.extra
            if isinstance(extra_data, str):
                # Handle case where extra is stored as JSON string
                try:
                    extra_data = json.loads(extra_data)
                except (json.JSONDecodeError, TypeError):
                    extra_data = {}
            
            if extra_data and 'contacts' in extra_data:
                contact_data = extra_data['contacts']
            elif extra_data:
                # Try to find contact info in extra data
                contact_data = {
                    'email': extra_data.get('contact_email') or extra_data.get('poc_email'),
                    'name': extra_data.get('contact_name') or extra_data.get('poc_name'),
                    'phone': extra_data.get('contact_phone') or extra_data.get('poc_phone'),
                }
            else:
                return False
            
            if any(contact_data.values()):
                extracted_contact = self.extract_contact_with_llm(contact_data)
                
                if extracted_contact['email'] or extracted_contact['name']:
                    prospect.primary_contact_email = extracted_contact['email']
                    prospect.primary_contact_name = extracted_contact['name']
                    prospect.ollama_processed_at = datetime.now(timezone.utc)
                    prospect.ollama_model_version = self.model_name
                    
                    # Update timestamp for polling detection
                    self._update_prospect_timestamp(prospect)
                    
                    return True
            
            return False
        
        return self._process_enhancement_batch(prospects, "contact extraction", process_contact_enhancement, commit_batch_size)
    
    def enhance_prospect_naics(self, prospects: List[Prospect], commit_batch_size: int = 100) -> int:
        """
        Enhance prospects with NAICS classification.
        First checks extra field for existing NAICS data, then uses LLM if needed.
        Returns count of successfully processed prospects.
        """
        # First pass: Check extra field for existing NAICS data
        prospects_with_extra_naics = 0
        prospects_after_extra_check = []
        
        for prospect in prospects:
            # Skip if already has NAICS in main field
            if prospect.naics:
                continue
                
            # Check extra field for NAICS information
            extra_naics = self.extract_naics_from_extra_field(prospect.extra)
            
            if extra_naics['found_in_extra'] and extra_naics['code']:
                # Found NAICS in extra field - populate main fields
                prospect.naics = extra_naics['code']
                prospect.naics_description = extra_naics['description']
                prospect.naics_source = 'original'  # Mark as original since it was in source data
                prospect.ollama_processed_at = datetime.now(timezone.utc)
                prospect.ollama_model_version = self.model_name
                
                # Mark in extra field to prevent future AI enhancement
                if not prospect.extra:
                    prospect.extra = {}
                elif isinstance(prospect.extra, str):
                    try:
                        prospect.extra = json.loads(prospect.extra)
                    except (json.JSONDecodeError, TypeError):
                        prospect.extra = {}
                
                prospect.extra['naics_extracted_from_extra'] = {
                    'extracted_at': datetime.now(timezone.utc).isoformat(),
                    'extracted_by': 'llm_service_extra_field_check',
                    'original_code': extra_naics['code'],
                    'original_description': extra_naics['description']
                }
                
                prospects_with_extra_naics += 1
                logger.info(f"Found NAICS {extra_naics['code']} in extra field for prospect {prospect.id[:8]}...")
                
                # Update timestamp for polling detection
                self._update_prospect_timestamp(prospect)
            else:
                # No NAICS in extra field, will need LLM classification
                prospects_after_extra_check.append(prospect)
        
        # Log results of extra field check
        prospects_with_main_naics = len(prospects) - len(prospects_after_extra_check) - prospects_with_extra_naics
        logger.info(f"NAICS Status after extra field check:")
        logger.info(f"  Already have NAICS in main field: {prospects_with_main_naics}")
        logger.info(f"  Found NAICS in extra field: {prospects_with_extra_naics}")
        logger.info(f"  Still need LLM classification: {len(prospects_after_extra_check)}")
        
        # Commit the extra field extractions first
        if prospects_with_extra_naics > 0:
            try:
                db.session.commit()
                logger.info(f"Successfully extracted {prospects_with_extra_naics} NAICS codes from extra fields")
            except Exception as e:
                logger.error(f"Failed to commit extra field NAICS extractions: {e}")
                db.session.rollback()
        
        # Second pass: LLM classification for remaining prospects
        if not prospects_after_extra_check:
            logger.info("All prospects now have NAICS codes - skipping LLM classification")
            return prospects_with_extra_naics
        
        logger.info(f"Starting LLM classification for {len(prospects_after_extra_check)} prospects...")
        
        def process_naics_enhancement(prospect: Prospect) -> bool:
            if not prospect.title or not prospect.description:
                return False
            
            # Gather all available information for enhanced classification
            agency = prospect.agency or (prospect.extra.get('agency') if prospect.extra else None)
            contract_type = prospect.contract_type
            set_aside = prospect.set_aside
            estimated_value = prospect.estimated_value_text or prospect.estimated_value
            
            # Build additional info from extra field
            additional_info = ""
            if prospect.extra:
                extra_data = prospect.extra
                if isinstance(extra_data, str):
                    try:
                        extra_data = json.loads(extra_data)
                    except (json.JSONDecodeError, TypeError):
                        extra_data = {}
                
                # Extract relevant fields that might help classification
                info_fields = []
                for key in ['summary', 'scope', 'requirements', 'keywords', 'technology', 'industry']:
                    if key in extra_data and extra_data[key]:
                        info_fields.append(f"{key}: {extra_data[key]}")
                
                additional_info = " | ".join(info_fields)
            
            classification = self.classify_naics_with_llm(
                title=prospect.title,
                description=prospect.description,
                prospect_id=prospect.id,
                agency=agency,
                contract_type=contract_type,
                set_aside=set_aside,
                estimated_value=estimated_value,
                additional_info=additional_info
            )
            
            if classification['code']:
                prospect.naics = classification['code']
                prospect.naics_description = classification['description']
                prospect.naics_source = 'llm_inferred'
                prospect.ollama_processed_at = datetime.now(timezone.utc)
                prospect.ollama_model_version = self.model_name
                
                # Add confidence to extras
                if not prospect.extra:
                    prospect.extra = {}
                elif isinstance(prospect.extra, str):
                    # Handle case where extra is stored as JSON string
                    try:
                        prospect.extra = json.loads(prospect.extra)
                    except (json.JSONDecodeError, TypeError):
                        prospect.extra = {}
                
                prospect.extra['llm_classification'] = {
                    'naics_confidence': classification['confidence'],
                    'model_used': self.model_name,
                    'classified_at': datetime.now(timezone.utc).isoformat(),
                    'all_codes': classification['all_codes']  # Store all suggested codes
                }
                
                # Update timestamp for polling detection
                self._update_prospect_timestamp(prospect)
                
                return True
            
            return False
        
        llm_enhanced = self._process_enhancement_batch(prospects_after_extra_check, "NAICS classification", process_naics_enhancement, commit_batch_size)
        
        total_enhanced = prospects_with_extra_naics + llm_enhanced
        logger.info(f"Total NAICS enhancement complete: {prospects_with_extra_naics} from extra field + {llm_enhanced} from LLM = {total_enhanced}")
        
        return total_enhanced
    
    def backfill_naics_descriptions(self, prospects: List[Prospect]) -> int:
        """
        Backfill missing NAICS descriptions for prospects that have codes but no descriptions.
        Uses official NAICS lookup to ensure standardized descriptions.
        """
        backfilled_count = 0
        
        for prospect in prospects:
            # Skip if no NAICS code or already has description
            if not prospect.naics or prospect.naics_description:
                continue
            
            # Get official description from lookup
            official_description = get_naics_description(prospect.naics)
            
            if official_description:
                prospect.naics_description = official_description
                
                # Mark as processed if not already marked
                if not prospect.ollama_processed_at:
                    prospect.ollama_processed_at = datetime.now(timezone.utc)
                    prospect.ollama_model_version = self.model_name
                
                # Add to extra field to track backfill
                if not prospect.extra:
                    prospect.extra = {}
                elif isinstance(prospect.extra, str):
                    try:
                        prospect.extra = json.loads(prospect.extra)
                    except (json.JSONDecodeError, TypeError):
                        prospect.extra = {}
                
                prospect.extra['naics_description_backfilled'] = {
                    'backfilled_at': datetime.now(timezone.utc).isoformat(),
                    'backfilled_by': 'naics_lookup_service',
                    'original_source': prospect.naics_source or 'unknown'
                }
                
                backfilled_count += 1
                logger.info(f"Backfilled NAICS description for {prospect.naics}: {official_description}")
        
        # Commit all backfills
        if backfilled_count > 0:
            try:
                db.session.commit()
                logger.info(f"Successfully backfilled {backfilled_count} NAICS descriptions")
            except Exception as e:
                logger.error(f"Error committing NAICS description backfills: {e}")
                db.session.rollback()
                backfilled_count = 0
        
        return backfilled_count
    
    def enhance_all_prospects(self, limit: Optional[int] = None) -> Dict[str, int]:
        """
        Run all enhancement modules on prospects.
        Returns dict with counts for each enhancement type.
        """
        # Query prospects that haven't been LLM processed yet
        query = Prospect.query.filter(Prospect.ollama_processed_at.is_(None))
        
        if limit:
            query = query.limit(limit)
            
        prospects = query.all()
        
        logger.info(f"Found {len(prospects)} prospects to enhance")
        
        results = {
            'total_prospects': len(prospects),
            'values_enhanced': 0,
            'contacts_enhanced': 0,
            'naics_enhanced': 0,
            'naics_descriptions_backfilled': 0
        }
        
        if not prospects:
            return results
        
        # Run enhancement modules
        results['values_enhanced'] = self.enhance_prospect_values(prospects)
        results['contacts_enhanced'] = self.enhance_prospect_contacts(prospects)
        results['naics_enhanced'] = self.enhance_prospect_naics(prospects)
        
        # Backfill missing NAICS descriptions for all prospects (not just unprocessed ones)
        all_prospects = Prospect.query.filter(
            Prospect.naics.isnot(None),
            Prospect.naics_description.is_(None)
        ).all()
        
        if all_prospects:
            results['naics_descriptions_backfilled'] = self.backfill_naics_descriptions(all_prospects)
        
        return results