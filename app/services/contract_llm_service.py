"""
Batch LLM Service for Contract Data Enhancement
Handles bulk processing of prospects using the base LLM service
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from decimal import Decimal

from app.database import db
from app.database.models import Prospect, InferredProspectData
from app.services.base_llm_service import BaseLLMService
from app.services.llm_service_utils import ensure_extra_is_dict, update_prospect_timestamps
from app.utils.logger import logger


class ContractLLMService(BaseLLMService):
    """
    Batch service for enhancing contract data using LLM.
    Inherits core enhancement logic from BaseLLMService.
    """
    
    def __init__(self, model_name: str = 'qwen3:latest'):
        super().__init__(model_name)
        self.batch_size = 50
    
    def _update_prospect_timestamp(self, prospect: Prospect):
        """Update prospect's ollama_processed_at timestamp for polling detection"""
        try:
            update_prospect_timestamps(prospect, self.model_name)
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to update prospect timestamp: {e}")
            db.session.rollback()
    
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
            # Skip if already processed (check for either min/max or single)
            if prospect.estimated_value_min is not None or prospect.estimated_value_single is not None:
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
                parsed_value = self.parse_contract_value_with_llm(value_text, prospect.id)
                
                # Check if we got valid results (either range or single)
                has_range = parsed_value['min'] is not None and parsed_value['max'] is not None
                has_single = parsed_value['single'] is not None
                
                if has_range or has_single:
                    # IMPORTANT: If we have both min and max, it's ALWAYS a range
                    # regardless of is_range flag or presence of single value
                    if has_range:
                        prospect.estimated_value_min = Decimal(str(parsed_value['min']))
                        prospect.estimated_value_max = Decimal(str(parsed_value['max']))
                        prospect.estimated_value_single = None  # Always null for ranges
                    # Only treat as single value if we have single but NOT min/max
                    elif has_single and not has_range:
                        prospect.estimated_value_min = None
                        prospect.estimated_value_max = None
                        prospect.estimated_value_single = Decimal(str(parsed_value['single']))
                    
                    prospect.ollama_processed_at = datetime.now(timezone.utc)
                    prospect.ollama_model_version = self.model_name
                    
                    # Update timestamp for polling detection
                    self._update_prospect_timestamp(prospect)
                    
                    return True
            
            return False
        
        return self._process_enhancement_batch(prospects, "value enhancement", process_value_enhancement, commit_batch_size)
    
    def enhance_prospect_titles(self, prospects: List[Prospect], commit_batch_size: int = 100) -> int:
        """
        Enhance prospects with improved titles.
        Returns count of successfully processed prospects.
        """
        def process_title_enhancement(prospect: Prospect) -> bool:
            # Skip if already processed
            if prospect.ai_enhanced_title:
                return False
                
            if prospect.title and prospect.description:
                enhanced_title = self.enhance_title_with_llm(
                    prospect.title, 
                    prospect.description, 
                    prospect.agency or "",
                    prospect_id=prospect.id
                )
                
                if enhanced_title['enhanced_title']:
                    prospect.ai_enhanced_title = enhanced_title['enhanced_title']
                    
                    # Store additional metadata in extra field
                    ensure_extra_is_dict(prospect)
                    prospect.extra['llm_title_enhancement'] = {
                        'confidence': enhanced_title['confidence'],
                        'reasoning': enhanced_title.get('reasoning', ''),
                        'original_title': prospect.title,
                        'enhanced_at': datetime.now(timezone.utc).isoformat(),
                        'model_used': self.model_name
                    }
                    
                    prospect.ollama_processed_at = datetime.now(timezone.utc)
                    prospect.ollama_model_version = self.model_name
                    
                    # Update timestamp for polling detection
                    self._update_prospect_timestamp(prospect)
                    
                    return True
            
            return False
        
        return self._process_enhancement_batch(prospects, "title enhancement", process_title_enhancement, commit_batch_size)
    
    def enhance_prospect_naics(self, prospects: List[Prospect], commit_batch_size: int = 100) -> int:
        """
        Enhance prospects with NAICS classifications.
        Returns count of successfully processed prospects.
        """
        def process_naics_enhancement(prospect: Prospect) -> bool:
            # Skip if already has LLM-inferred NAICS
            if prospect.naics and prospect.naics_source == 'llm_inferred':
                return False
            
            if prospect.description:
                # First check extra field for existing NAICS data
                extra_naics = self.extract_naics_from_extra_field(prospect.extra)
                
                if extra_naics['found_in_extra'] and extra_naics['code']:
                    # Found NAICS in extra field - populate main fields with standardized format
                    prospect.naics = extra_naics['code']
                    prospect.naics_description = extra_naics['description']
                    prospect.naics_source = 'original'  # Mark as original since it was in source data
                    
                    # Mark in extra field to prevent future AI enhancement
                    ensure_extra_is_dict(prospect)
                    prospect.extra['naics_extracted_from_extra'] = {
                        'extracted_at': datetime.now(timezone.utc).isoformat(),
                        'extracted_by': 'contract_llm_service_extra_field_check',
                        'original_code': extra_naics['code'],
                        'original_description': extra_naics['description']
                    }
                    
                    logger.info(f"Found NAICS {extra_naics['code']} in extra field for prospect {prospect.id[:8]}...")
                    
                    self._update_prospect_timestamp(prospect)
                    return True
                
                # No NAICS in extra field, proceed with LLM classification
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
                    
                    # Add confidence to extras
                    ensure_extra_is_dict(prospect)
                    prospect.extra['llm_classification'] = {
                        'naics_confidence': classification['confidence'],
                        'model_used': self.model_name,
                        'classified_at': datetime.now(timezone.utc).isoformat()
                    }
                    
                    self._update_prospect_timestamp(prospect)
                    return True
            
            return False
        
        return self._process_enhancement_batch(prospects, "NAICS classification", process_naics_enhancement, commit_batch_size)
    
    def enhance_prospect_set_asides(self, prospects: List[Prospect], commit_batch_size: int = 100, force_redo: bool = False) -> int:
        """
        Enhance prospects with standardized set-aside values.
        Returns count of successfully processed prospects.
        """
        def process_set_aside_enhancement(prospect: Prospect) -> bool:
            # Skip if already processed unless forced
            if not force_redo and prospect.set_aside_standardized:
                logger.debug(f"Skipping prospect {prospect.id[:8]}... - already standardized and force_redo=False")
                return False
            
            # Debug logging for force_redo scenarios
            if force_redo:
                logger.info(f"Force redo set-aside enhancement for prospect {prospect.id[:8]}... (current: {prospect.set_aside_standardized})")
            
            # Process prospects with set_aside data OR potential extra data (like DHS small_business_program)
            comprehensive_data = self._get_comprehensive_set_aside_data(prospect.set_aside, prospect)
            if comprehensive_data:
                logger.debug(f"Processing set-aside with comprehensive data: '{comprehensive_data}'")
                
                # Use comprehensive_data (which includes DHS small_business_program) instead of just prospect.set_aside
                standardized = self.standardize_set_aside_with_llm(comprehensive_data, prospect_id=prospect.id, prospect=prospect)
                if standardized:
                    # Store previous values for comparison
                    previous_code = prospect.set_aside_standardized
                    previous_label = prospect.set_aside_standardized_label
                    
                    # Update fields
                    prospect.set_aside_standardized = standardized.code
                    prospect.set_aside_standardized_label = standardized.label
                    
                    # Also populate inferred_set_aside for frontend compatibility
                    prospect.inferred_set_aside = standardized.label
                    
                    # Store metadata in extra field
                    ensure_extra_is_dict(prospect)
                    prospect.extra['set_aside_standardization'] = {
                        'original': prospect.set_aside,
                        'standardized_at': datetime.now(timezone.utc).isoformat(),
                        'force_redo': force_redo,
                        'previous_code': previous_code,
                        'new_code': standardized.code
                    }
                    
                    self._update_prospect_timestamp(prospect)
                    
                    # Always count force_redo as successful processing, even if result is the same
                    if force_redo:
                        logger.info(f"Force redo completed for prospect {prospect.id[:8]}... - "
                                   f"result: {previous_code} -> {standardized.code}")
                        return True
                    # For non-force redo, only count as processed if values actually changed
                    elif previous_code != standardized.code:
                        logger.info(f"Set-aside standardized for prospect {prospect.id[:8]}... - "
                                   f"{previous_code} -> {standardized.code}")
                        return True
                    else:
                        logger.debug(f"Set-aside unchanged for prospect {prospect.id[:8]}... - {standardized.code}")
                        return False
                else:
                    logger.warning(f"Standardization failed for prospect {prospect.id[:8]}... with data: '{comprehensive_data}'")
            else:
                logger.debug(f"No comprehensive data for prospect {prospect.id[:8]}... - skipping")
            
            return False
        
        return self._process_enhancement_batch(prospects, "set-aside standardization", process_set_aside_enhancement, commit_batch_size)
    
    def _emit_field_update(self, prospect_id: str, field_type: str, field_data: Dict[str, Any]):
        """
        Emit field update for real-time processing compatibility.
        This is a no-op for batch processing but maintained for API compatibility.
        """
        pass  # Batch processing doesn't need real-time updates