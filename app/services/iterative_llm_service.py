"""
Iterative LLM Enhancement Service

Handles one-by-one processing of prospects with start/stop functionality
and real-time progress tracking.
"""
import asyncio
import threading
from datetime import datetime, timezone
from typing import Dict, Optional, Literal
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from concurrent.futures import ThreadPoolExecutor

from app.database.models import Prospect, AIEnrichmentLog
from app.services.contract_llm_service import ContractLLMService
from app.utils.logger import logger

EnhancementType = Literal["all", "values", "contacts", "naics"]


class IterativeLLMService:
    """Service for iterative one-by-one LLM enhancement with start/stop control"""
    
    def __init__(self):
        self.llm_service = ContractLLMService()
        self._processing = False
        self._current_task: Optional[asyncio.Task] = None
        self._progress: Dict[str, any] = {
            "status": "idle",
            "current_type": None,
            "processed": 0,
            "total": 0,
            "current_prospect": None,
            "started_at": None,
            "errors": []
        }
        self._lock = threading.Lock()
    
    def get_progress(self) -> Dict[str, any]:
        """Get current processing progress"""
        with self._lock:
            return self._progress.copy()
    
    def is_processing(self) -> bool:
        """Check if enhancement is currently running"""
        return self._processing
    
    async def start_enhancement(self, enhancement_type: EnhancementType, db: Session) -> Dict[str, any]:
        """Start iterative enhancement processing"""
        if self._processing:
            return {"status": "error", "message": "Enhancement already in progress"}
        
        self._processing = True
        self._progress.update({
            "status": "processing",
            "current_type": enhancement_type,
            "processed": 0,
            "total": self._count_unprocessed(enhancement_type, db),
            "current_prospect": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "errors": []
        })
        
        # Start processing in background
        self._current_task = asyncio.create_task(
            self._process_iteratively(enhancement_type, db)
        )
        
        return {
            "status": "started",
            "message": f"Started {enhancement_type} enhancement",
            "total_to_process": self._progress["total"]
        }
    
    async def stop_enhancement(self) -> Dict[str, any]:
        """Stop the current enhancement process"""
        if not self._processing:
            return {"status": "error", "message": "No enhancement in progress"}
        
        self._processing = False
        
        # Cancel the current task if it exists
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            try:
                await self._current_task
            except asyncio.CancelledError:
                pass
        
        with self._lock:
            self._progress["status"] = "stopped"
        
        return {
            "status": "stopped",
            "message": "Enhancement process stopped",
            "processed": self._progress["processed"]
        }
    
    def _count_unprocessed(self, enhancement_type: EnhancementType, db: Session) -> int:
        """Count prospects that need processing"""
        query = db.query(Prospect)
        
        if enhancement_type in ["values", "all"]:
            query = query.filter(
                Prospect.estimated_value_text.isnot(None),
                Prospect.estimated_value_single.is_(None)
            )
        elif enhancement_type in ["contacts", "all"]:
            query = query.filter(
                Prospect.extra.isnot(None),
                Prospect.primary_contact_name.is_(None)
            )
        elif enhancement_type in ["naics", "all"]:
            query = query.filter(
                Prospect.description.isnot(None),
                or_(
                    Prospect.naics.is_(None),
                    Prospect.naics_source != 'llm_inferred'
                )
            )
        
        return query.count()
    
    async def _process_iteratively(self, enhancement_type: EnhancementType, db: Session):
        """Process prospects one by one"""
        try:
            while self._processing:
                # Get next unprocessed prospect
                prospect = self._get_next_prospect(enhancement_type, db)
                
                if not prospect:
                    # No more prospects to process
                    with self._lock:
                        self._progress["status"] = "completed"
                    break
                
                # Update current prospect info
                with self._lock:
                    self._progress["current_prospect"] = {
                        "id": prospect.id,
                        "title": prospect.title[:100] if prospect.title else "Untitled"
                    }
                
                # Process single prospect
                try:
                    success = await self._process_single_prospect(prospect, enhancement_type, db)
                    
                    if success:
                        with self._lock:
                            self._progress["processed"] += 1
                    else:
                        with self._lock:
                            self._progress["errors"].append({
                                "prospect_id": prospect.id,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })
                    
                    # Commit after each prospect for real-time updates
                    db.commit()
                    
                    # Log progress
                    logger.info(
                        f"Processed prospect {prospect.id}: "
                        f"{self._progress['processed']}/{self._progress['total']} completed"
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing prospect {prospect.id}: {str(e)}")
                    with self._lock:
                        self._progress["errors"].append({
                            "prospect_id": prospect.id,
                            "error": str(e),
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    db.rollback()
                
                # Small delay to prevent overwhelming the LLM service
                await asyncio.sleep(0.5)
        
        except asyncio.CancelledError:
            logger.info("Enhancement process cancelled")
            raise
        except Exception as e:
            logger.error(f"Enhancement process error: {str(e)}")
            with self._lock:
                self._progress["status"] = "error"
                self._progress["error_message"] = str(e)
        finally:
            self._processing = False
            
            # Log final results
            log_entry = AIEnrichmentLog(
                enhancement_type=enhancement_type,
                status="completed" if self._progress["status"] == "completed" else "stopped",
                processed_count=self._progress["processed"],
                duration=(datetime.now(timezone.utc) - datetime.fromisoformat(self._progress["started_at"])).total_seconds(),
                message=f"Processed {self._progress['processed']} of {self._progress['total']} prospects",
                error=self._progress.get("error_message")
            )
            db.add(log_entry)
            db.commit()
    
    def _get_next_prospect(self, enhancement_type: EnhancementType, db: Session) -> Optional[Prospect]:
        """Get the next unprocessed prospect"""
        query = db.query(Prospect)
        
        if enhancement_type == "values":
            query = query.filter(
                Prospect.estimated_value_text.isnot(None),
                Prospect.estimated_value_single.is_(None)
            )
        elif enhancement_type == "contacts":
            query = query.filter(
                Prospect.extra.isnot(None),
                Prospect.primary_contact_name.is_(None)
            )
        elif enhancement_type == "naics":
            query = query.filter(
                Prospect.description.isnot(None),
                or_(
                    Prospect.naics.is_(None),
                    Prospect.naics_source != 'llm_inferred'
                )
            )
        elif enhancement_type == "all":
            # For "all", prioritize by type: values -> contacts -> naics
            query = query.filter(
                or_(
                    and_(
                        Prospect.estimated_value_text.isnot(None),
                        Prospect.estimated_value_single.is_(None)
                    ),
                    and_(
                        Prospect.extra.isnot(None),
                        Prospect.primary_contact_name.is_(None)
                    ),
                    and_(
                        Prospect.description.isnot(None),
                        or_(
                            Prospect.naics.is_(None),
                            Prospect.naics_source != 'llm_inferred'
                        )
                    )
                )
            )
        
        return query.order_by(Prospect.loaded_at.desc()).first()
    
    async def _process_single_prospect(
        self, 
        prospect: Prospect, 
        enhancement_type: EnhancementType, 
        db: Session
    ) -> bool:
        """Process a single prospect based on enhancement type"""
        try:
            processed = False
            
            # Process based on type
            if enhancement_type in ["values", "all"]:
                if prospect.estimated_value_text and not prospect.estimated_value_single:
                    # Parse contract value
                    parsed_value = self.llm_service.parse_contract_value_with_llm(prospect.estimated_value_text, prospect_id=prospect.id)
                    if parsed_value['single'] is not None:
                        prospect.estimated_value_single = float(parsed_value['single'])
                        prospect.estimated_value_min = float(parsed_value['min']) if parsed_value['min'] else float(parsed_value['single'])
                        prospect.estimated_value_max = float(parsed_value['max']) if parsed_value['max'] else float(parsed_value['single'])
                        prospect.ollama_processed_at = datetime.now(timezone.utc)
                        prospect.ollama_model_version = self.llm_service.model_name
                        processed = True
            
            if enhancement_type in ["contacts", "all"]:
                if prospect.extra and not prospect.primary_contact_name:
                    # Extract contact data from extra field
                    import json
                    extra_data = prospect.extra
                    if isinstance(extra_data, str):
                        try:
                            extra_data = json.loads(extra_data)
                        except (json.JSONDecodeError, TypeError):
                            extra_data = {}
                    
                    # Get contact data from various possible locations
                    if extra_data and 'contacts' in extra_data:
                        contact_data = extra_data['contacts']
                    elif extra_data:
                        contact_data = {
                            'email': extra_data.get('contact_email') or extra_data.get('poc_email'),
                            'name': extra_data.get('contact_name') or extra_data.get('poc_name'),
                            'phone': extra_data.get('contact_phone') or extra_data.get('poc_phone'),
                        }
                    else:
                        contact_data = {}
                    
                    if any(contact_data.values()):
                        extracted_contact = self.llm_service.extract_contact_with_llm(contact_data, prospect_id=prospect.id)
                        
                        if extracted_contact['email'] or extracted_contact['name']:
                            prospect.primary_contact_email = extracted_contact['email']
                            prospect.primary_contact_name = extracted_contact['name']
                            prospect.ollama_processed_at = datetime.now(timezone.utc)
                            prospect.ollama_model_version = self.llm_service.model_name
                            processed = True
            
            if enhancement_type in ["naics", "all"]:
                if prospect.description and (not prospect.naics or prospect.naics_source != 'llm_inferred'):
                    # Classify NAICS
                    classification = self.llm_service.classify_naics_with_llm(prospect.title, prospect.description, prospect_id=prospect.id)
                    
                    if classification['code']:
                        prospect.naics = classification['code']
                        prospect.naics_description = classification['description']
                        prospect.naics_source = 'llm_inferred'
                        prospect.ollama_processed_at = datetime.now(timezone.utc)
                        prospect.ollama_model_version = self.llm_service.model_name
                        
                        # Add confidence to extras
                        import json
                        if not prospect.extra:
                            prospect.extra = {}
                        elif isinstance(prospect.extra, str):
                            try:
                                prospect.extra = json.loads(prospect.extra)
                            except (json.JSONDecodeError, TypeError):
                                prospect.extra = {}
                        
                        # Ensure extra is a dict before assignment
                        if not isinstance(prospect.extra, dict):
                            prospect.extra = {}
                            
                        prospect.extra['llm_classification'] = {
                            'naics_confidence': classification['confidence'],
                            'model_used': self.llm_service.model_name,
                            'classified_at': datetime.now(timezone.utc).isoformat()
                        }
                        processed = True
            
            return processed
            
        except Exception as e:
            logger.error(f"Error in _process_single_prospect: {str(e)}")
            return False


# Global instance for maintaining state across requests
iterative_service = IterativeLLMService()