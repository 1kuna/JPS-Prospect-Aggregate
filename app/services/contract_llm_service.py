"""
Modular LLM Service for Contract Data Enhancement
Uses qwen3:8b via Ollama for optional data enrichment
"""

import json
import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal

from app.utils.llm_utils import call_ollama
from app.database import db
from app.database.models import Prospect, InferredProspectData, LLMOutput
from app.services.optimized_prompts import get_naics_prompt, get_value_prompt, get_contact_prompt, get_title_prompt
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
        
    def parse_existing_naics(self, naics_str: Optional[str]) -> Dict[str, Optional[str]]:
        """Parse existing NAICS codes from source data formats"""
        if not naics_str:
            return {'code': None, 'description': None}
        
        # Handle different NAICS formats from source data
        patterns = [
            r'(\d{6})\s*[|\-]\s*(.*)',  # "334516 | Description" or "334516 - Description"
            r'(\d{6})\s+(.*)',          # "334516 Description"
            r'(\d{6})'                  # Just the code
        ]
        
        for pattern in patterns:
            match = re.match(pattern, str(naics_str).strip())
            if match:
                return {
                    'code': match.group(1),
                    'description': match.group(2).strip() if len(match.groups()) > 1 else None
                }
        
        return {'code': str(naics_str), 'description': None}
    
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
    
    def classify_naics_with_llm(self, title: str, description: str, prospect_id: str = None) -> Dict:
        """NAICS Classification using qwen3:8b"""
        prompt = get_naics_prompt(title, description)
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
                'code': parsed.get('code'),
                'description': parsed.get('description'),
                'confidence': parsed.get('confidence', 0.8)
            }
            
            # Log successful output
            if prospect_id:
                self._log_llm_output(prospect_id, 'naics', prompt, response, result, True, processing_time=processing_time)
            
            return result
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Error parsing NAICS response: {e}")
            error_result = {'code': None, 'description': None, 'confidence': 0.0}
            
            # Log failed output
            if prospect_id:
                self._log_llm_output(prospect_id, 'naics', prompt, response, error_result, False, 
                                   error_message=str(e), processing_time=processing_time)
            
            return error_result
    
    def parse_contract_value_with_llm(self, value_text: str, prospect_id: str = None) -> Dict:
        """Value parsing using qwen3:8b"""
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
    
    def enhance_prospect_values(self, prospects: List[Prospect], commit_batch_size: int = 100) -> int:
        """
        Enhance prospects with parsed contract values.
        Returns count of successfully processed prospects.
        """
        logger.info(f"Starting value parsing for {len(prospects)} prospects...")
        processed_count = 0
        
        for i in range(0, len(prospects), self.batch_size):
            batch = prospects[i:i + self.batch_size]
            logger.info(f"Processing value batch {i//self.batch_size + 1}/{(len(prospects) + self.batch_size - 1)//self.batch_size}")
            
            for prospect in batch:
                try:
                    # Skip if already processed
                    if prospect.estimated_value_min is not None:
                        continue
                    
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
                            prospect.ollama_processed_at = datetime.utcnow()
                            prospect.ollama_model_version = self.model_name
                            processed_count += 1
                            
                except Exception as e:
                    logger.error(f"Error processing prospect {prospect.id}: {e}")
                    continue
            
            # Commit batch
            if processed_count > 0 and processed_count % commit_batch_size == 0:
                try:
                    db.session.commit()
                    logger.info(f"Committed {processed_count} value enhancements")
                except Exception as e:
                    logger.error(f"Error committing batch: {e}")
                    db.session.rollback()
        
        # Final commit
        try:
            db.session.commit()
            logger.info(f"Completed value enhancement. Total processed: {processed_count}")
        except Exception as e:
            logger.error(f"Error in final commit: {e}")
            db.session.rollback()
            
        return processed_count
    
    def enhance_prospect_contacts(self, prospects: List[Prospect], commit_batch_size: int = 100) -> int:
        """
        Enhance prospects with extracted contact information.
        Returns count of successfully processed prospects.
        """
        logger.info(f"Starting contact extraction for {len(prospects)} prospects...")
        processed_count = 0
        
        for i in range(0, len(prospects), self.batch_size):
            batch = prospects[i:i + self.batch_size]
            logger.info(f"Processing contact batch {i//self.batch_size + 1}/{(len(prospects) + self.batch_size - 1)//self.batch_size}")
            
            for prospect in batch:
                try:
                    # Skip if already processed
                    if prospect.primary_contact_email is not None:
                        continue
                    
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
                        continue
                    
                    if any(contact_data.values()):
                        extracted_contact = self.extract_contact_with_llm(contact_data)
                        
                        if extracted_contact['email'] or extracted_contact['name']:
                            prospect.primary_contact_email = extracted_contact['email']
                            prospect.primary_contact_name = extracted_contact['name']
                            prospect.ollama_processed_at = datetime.utcnow()
                            prospect.ollama_model_version = self.model_name
                            processed_count += 1
                            
                except Exception as e:
                    logger.error(f"Error processing prospect {prospect.id}: {e}")
                    continue
            
            # Commit batch
            if processed_count > 0 and processed_count % commit_batch_size == 0:
                try:
                    db.session.commit()
                    logger.info(f"Committed {processed_count} contact enhancements")
                except Exception as e:
                    logger.error(f"Error committing batch: {e}")
                    db.session.rollback()
        
        # Final commit
        try:
            db.session.commit()
            logger.info(f"Completed contact enhancement. Total processed: {processed_count}")
        except Exception as e:
            logger.error(f"Error in final commit: {e}")
            db.session.rollback()
            
        return processed_count
    
    def enhance_prospect_naics(self, prospects: List[Prospect], commit_batch_size: int = 100) -> int:
        """
        Enhance prospects with NAICS classification (only for missing NAICS).
        Returns count of successfully processed prospects.
        """
        # Filter prospects needing NAICS
        prospects_needing_naics = [p for p in prospects if not p.naics]
        prospects_with_naics = len(prospects) - len(prospects_needing_naics)
        
        logger.info(f"NAICS Status: {prospects_with_naics} prospects already have NAICS codes")
        logger.info(f"Processing {len(prospects_needing_naics)} prospects that need NAICS classification...")
        
        if not prospects_needing_naics:
            logger.info("All prospects already have NAICS codes - skipping LLM classification")
            return 0
        
        processed_count = 0
        
        for i in range(0, len(prospects_needing_naics), self.batch_size):
            batch = prospects_needing_naics[i:i + self.batch_size]
            logger.info(f"Processing NAICS batch {i//self.batch_size + 1}/{(len(prospects_needing_naics) + self.batch_size - 1)//self.batch_size}")
            
            for prospect in batch:
                try:
                    if not prospect.title or not prospect.description:
                        continue
                    
                    classification = self.classify_naics_with_llm(prospect.title, prospect.description)
                    
                    if classification['code']:
                        prospect.naics = classification['code']
                        prospect.naics_description = classification['description']
                        prospect.naics_source = 'llm_inferred'
                        prospect.ollama_processed_at = datetime.utcnow()
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
                            'classified_at': datetime.utcnow().isoformat()
                        }
                        
                        processed_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing prospect {prospect.id}: {e}")
                    continue
            
            # Commit batch
            if processed_count > 0 and processed_count % commit_batch_size == 0:
                try:
                    db.session.commit()
                    logger.info(f"Committed {processed_count} NAICS enhancements")
                except Exception as e:
                    logger.error(f"Error committing batch: {e}")
                    db.session.rollback()
        
        # Final commit
        try:
            db.session.commit()
            logger.info(f"Completed NAICS enhancement. Total processed: {processed_count}")
        except Exception as e:
            logger.error(f"Error in final commit: {e}")
            db.session.rollback()
            
        return processed_count
    
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
            'naics_enhanced': 0
        }
        
        if not prospects:
            return results
        
        # Run enhancement modules
        results['values_enhanced'] = self.enhance_prospect_values(prospects)
        results['contacts_enhanced'] = self.enhance_prospect_contacts(prospects)
        results['naics_enhanced'] = self.enhance_prospect_naics(prospects)
        
        return results