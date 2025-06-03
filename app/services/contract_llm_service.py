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
from app.database.models import Prospect, InferredProspectData

logger = logging.getLogger(__name__)


class ContractLLMService:
    """
    Service for enhancing contract data using qwen3:8b LLM.
    Designed to be modular and optional - can run independently of core data.
    """
    
    def __init__(self, model_name: str = 'qwen3:8b'):
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
    
    def classify_naics_with_llm(self, title: str, description: str) -> Dict:
        """NAICS Classification using qwen3:8b"""
        prompt = f"""Classify the following government contract into a NAICS code and description.

Title: {title}
Description: {description}

Return only a JSON object with this exact format:
{{"code": "XXXXXX", "description": "Industry Name", "confidence": 0.95}}

Focus on the primary industry or service being procured. Use standard NAICS 2022 codes."""

        response = call_ollama(prompt, self.model_name)
        
        try:
            # Clean response of any think tags
            if response:
                response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE).strip()
            
            parsed = json.loads(response)
            return {
                'code': parsed.get('code'),
                'description': parsed.get('description'),
                'confidence': parsed.get('confidence', 0.8)
            }
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Error parsing NAICS response: {e}")
            return {'code': None, 'description': None, 'confidence': 0.0}
    
    def parse_contract_value_with_llm(self, value_text: str) -> Dict:
        """Value parsing using qwen3:8b"""
        if not value_text:
            return {'min': None, 'max': None, 'single': None}

        prompt = f"""Parse the following contract value text into structured amounts.

Value Text: "{value_text}"

Return only a JSON object with this exact format:
{{"min": 1000000, "max": 5000000, "single": 3000000}}

Rules:
- Convert all amounts to numbers (no commas, no currency symbols)
- If it's a range, provide min and max
- Always provide a single best estimate value
- If only one value given, use it for all three fields
- Handle abbreviations: K=thousand, M=million, B=billion

Examples:
"$1M-$5M" → {{"min": 1000000, "max": 5000000, "single": 3000000}}
"> $250K to < $750K" → {{"min": 250000, "max": 750000, "single": 500000}}
"$2.5 million" → {{"min": 2500000, "max": 2500000, "single": 2500000}}"""

        response = call_ollama(prompt, self.model_name)
        
        try:
            # Clean response of any think tags
            if response:
                response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE).strip()
                
            parsed = json.loads(response)
            return {
                'min': parsed.get('min'),
                'max': parsed.get('max'),
                'single': parsed.get('single')
            }
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Error parsing value response: {e}")
            return {'min': None, 'max': None, 'single': None}
    
    def extract_contact_with_llm(self, contact_data: Dict) -> Dict:
        """Contact extraction using qwen3:8b"""
        prompt = f"""Extract the primary contact information from this government contract data.

Contact Data: {json.dumps(contact_data, indent=2)}

Return only a JSON object with this exact format:
{{"email": "primary@agency.gov", "name": "John Smith", "confidence": 0.9}}

Rules:
- Choose the most likely primary point of contact
- Prefer program/requirement POCs over administrative contacts
- If multiple contacts, pick the one most relevant to the procurement
- Return null for missing information"""

        response = call_ollama(prompt, self.model_name)
        
        try:
            # Clean response of any think tags
            if response:
                response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE).strip()
                
            parsed = json.loads(response)
            return {
                'email': parsed.get('email'),
                'name': parsed.get('name'),
                'confidence': parsed.get('confidence', 0.8)
            }
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Error parsing contact response: {e}")
            return {'email': None, 'name': None, 'confidence': 0.0}
    
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
                        value_text = prospect.extra.get('estimated_value_text', '')
                    
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
                    if prospect.extra and 'contacts' in prospect.extra:
                        contact_data = prospect.extra['contacts']
                    elif prospect.extra:
                        # Try to find contact info in extra data
                        contact_data = {
                            'email': prospect.extra.get('contact_email') or prospect.extra.get('poc_email'),
                            'name': prospect.extra.get('contact_name') or prospect.extra.get('poc_name'),
                            'phone': prospect.extra.get('contact_phone') or prospect.extra.get('poc_phone'),
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