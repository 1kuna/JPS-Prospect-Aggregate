"""
Iterative LLM Enhancement Service V2

Handles one-by-one processing of prospects with start/stop functionality
and real-time progress tracking using threading instead of asyncio.
"""
import threading
from datetime import datetime, timezone
from typing import Dict, Optional, Literal
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.database.models import Prospect, AIEnrichmentLog
from app.services.contract_llm_service import ContractLLMService
from app.utils.logger import logger
from app.database import db

EnhancementType = Literal["all", "values", "titles", "naics", "set_asides"]


class IterativeLLMServiceV2:
    """Service for iterative one-by-one LLM enhancement with start/stop control"""
    
    def __init__(self):
        self.llm_service = ContractLLMService()
        self._processing = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
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
        self._queue_service = None  # Will be set by dependency injection
    
    def get_progress(self) -> Dict[str, any]:
        """Get current processing progress"""
        with self._lock:
            return self._progress.copy()
    
    def is_processing(self) -> bool:
        """Check if enhancement is currently running"""
        return self._processing
    
    def set_queue_service(self, queue_service):
        """Set reference to the queue service for coordination"""
        self._queue_service = queue_service

    def start_enhancement(self, enhancement_type: EnhancementType, skip_existing: bool = True) -> Dict[str, any]:
        """Start iterative enhancement processing using the queue system"""
        if self._processing:
            return {"status": "error", "message": "Enhancement already in progress"}
        
        # Create new session for thread
        from app import create_app
        app = create_app()
        
        with app.app_context():
            # Create a new session for thread safety
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=db.engine)
            db_session = Session()
            
            try:
                # Get all prospects that need processing
                prospects_to_process = self._get_prospects_to_process(enhancement_type, db_session, skip_existing)
                prospect_ids = [p.id for p in prospects_to_process]
                
                if not prospect_ids:
                    return {
                        "status": "completed",
                        "message": "No prospects need enhancement",
                        "total_to_process": 0
                    }
                
                # Add to queue system instead of processing directly
                if self._queue_service:
                    queue_item_id = self._queue_service.add_bulk_enhancement(
                        prospect_ids=prospect_ids,
                        enhancement_type=enhancement_type
                    )
                    
                    self._processing = True
                    self._progress.update({
                        "status": "queued",
                        "current_type": enhancement_type,
                        "processed": 0,
                        "total": len(prospect_ids),
                        "current_prospect": None,
                        "started_at": datetime.now(timezone.utc).isoformat(),
                        "errors": [],
                        "queue_item_id": queue_item_id
                    })
                    
                    # Start monitoring thread to update progress
                    self._thread = threading.Thread(
                        target=self._monitor_queue_progress,
                        args=(queue_item_id,),
                        daemon=True
                    )
                    self._thread.start()
                    
                    return {
                        "status": "queued",
                        "message": f"Added {enhancement_type} enhancement to queue",
                        "total_to_process": len(prospect_ids),
                        "queue_item_id": queue_item_id
                    }
                else:
                    # Fallback to direct processing if queue service not available
                    return self._start_direct_processing(enhancement_type, app)
                    
            finally:
                db_session.close()
    
    def stop_enhancement(self) -> Dict[str, any]:
        """Stop the current enhancement process"""
        if not self._processing:
            return {"status": "error", "message": "No enhancement in progress"}
        
        # Signal the thread to stop
        self._stop_event.set()
        
        # Immediately mark as stopping for UI feedback
        with self._lock:
            self._progress["status"] = "stopping"
        
        # Wait for thread to finish (with timeout)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)  # Increased timeout to allow current LLM call to finish
        
        with self._lock:
            self._progress["status"] = "stopped"
        
        self._processing = False
        
        return {
            "status": "stopping",  # Return stopping status immediately
            "message": "Stopping enhancement process (waiting for current LLM call to complete)...",
            "processed": self._progress["processed"]
        }
    
    def _build_enhancement_filter(self, enhancement_type: EnhancementType, skip_existing: bool = True):
        """Build SQLAlchemy filter conditions for enhancement types"""
        if enhancement_type == "values":
            if skip_existing:
                return or_(
                    and_(
                        Prospect.estimated_value_text.isnot(None),
                        Prospect.estimated_value_single.is_(None)
                    ),
                    and_(
                        Prospect.estimated_value.isnot(None),
                        Prospect.estimated_value_single.is_(None)
                    )
                )
            else:
                return or_(
                    Prospect.estimated_value_text.isnot(None),
                    Prospect.estimated_value.isnot(None)
                )
        elif enhancement_type == "titles":
            if skip_existing:
                return and_(
                    Prospect.title.isnot(None),
                    Prospect.description.isnot(None)
                )
            else:
                return and_(
                    Prospect.title.isnot(None),
                    Prospect.description.isnot(None)
                )
        elif enhancement_type == "naics":
            if skip_existing:
                return and_(
                    Prospect.description.isnot(None),
                    or_(
                        Prospect.naics.is_(None),
                        Prospect.naics_source != 'llm_inferred'
                    )
                )
            else:
                return Prospect.description.isnot(None)
        elif enhancement_type == "set_asides":
            if skip_existing:
                return Prospect.set_aside.isnot(None)
            else:
                return Prospect.set_aside.isnot(None)
        elif enhancement_type == "all":
            if skip_existing:
                # Prospects that need ANY type of enhancement
                return or_(
                    # Needs value parsing
                    or_(
                        and_(
                            Prospect.estimated_value_text.isnot(None),
                            Prospect.estimated_value_single.is_(None)
                        ),
                        and_(
                            Prospect.estimated_value.isnot(None),
                            Prospect.estimated_value_single.is_(None)
                        )
                    ),
                    # Needs contact extraction
                    and_(
                        Prospect.extra.isnot(None),
                        Prospect.primary_contact_name.is_(None)
                    ),
                    # Needs NAICS classification
                    and_(
                        Prospect.description.isnot(None),
                        or_(
                            Prospect.naics.is_(None),
                            Prospect.naics_source != 'llm_inferred'
                        )
                    ),
                    # Needs title enhancement
                    and_(
                        Prospect.title.isnot(None),
                        Prospect.ai_enhanced_title.is_(None)
                    )
                )
            else:
                # Process all prospects that have any data for enhancement
                return or_(
                    Prospect.estimated_value_text.isnot(None),
                    Prospect.estimated_value.isnot(None),
                    Prospect.extra.isnot(None),
                    Prospect.description.isnot(None),
                    Prospect.title.isnot(None)
                )
        
        return None

    def _get_prospects_to_process(self, enhancement_type: EnhancementType, db_session: Session, skip_existing: bool = True):
        """Get all prospects that need processing for the given enhancement type"""
        filter_condition = self._build_enhancement_filter(enhancement_type, skip_existing)
        if filter_condition is not None:
            return db_session.query(Prospect).filter(filter_condition).order_by(Prospect.loaded_at.desc()).all()
        return []

    def _monitor_queue_progress(self, queue_item_id: str):
        """Monitor queue progress and update local progress"""
        import time
        while self._processing and not self._stop_event.is_set():
            if self._queue_service:
                item_status = self._queue_service.get_item_status(queue_item_id)
                if item_status:
                    with self._lock:
                        self._progress.update({
                            "status": item_status["status"],
                            "processed": item_status["progress"]["processed"],
                            "total": item_status["progress"]["total"]
                        })
                        
                    if item_status["status"] in ["completed", "failed", "cancelled"]:
                        with self._lock:
                            self._processing = False
                        break
                        
            time.sleep(1)  # Check every second

    def _start_direct_processing(self, enhancement_type: EnhancementType, app):
        """Fallback method for direct processing (original implementation)"""
        # Create new session for thread
        with app.app_context():
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=db.engine)
            db_session = Session()
            
            try:
                self._processing = True
                self._stop_event.clear()
                
                total_count = self._count_unprocessed(enhancement_type, db_session)
                
                self._progress.update({
                    "status": "processing",
                    "current_type": enhancement_type,
                    "processed": 0,
                    "total": total_count,
                    "current_prospect": None,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "errors": []
                })
                
                # Start processing in background thread
                self._thread = threading.Thread(
                    target=self._process_iteratively,
                    args=(enhancement_type, app),
                    daemon=True
                )
                self._thread.start()
                
                return {
                    "status": "started",
                    "message": f"Started {enhancement_type} enhancement",
                    "total_to_process": total_count
                }
            finally:
                db_session.close()
    
    def _count_unprocessed(self, enhancement_type: EnhancementType, db_session: Session) -> int:
        """Count prospects that need processing"""
        filter_condition = self._build_enhancement_filter(enhancement_type)
        if filter_condition is not None:
            return db_session.query(Prospect).filter(filter_condition).count()
        return 0
    
    def _process_iteratively(self, enhancement_type: EnhancementType, app):
        """Process prospects one by one in a thread"""
        with app.app_context():
            # Create a new session for this thread to avoid sharing sessions across threads
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=db.engine)
            db_session = Session()
            
            try:
                while not self._stop_event.is_set() and self._processing:
                    # Get next unprocessed prospect
                    prospect = self._get_next_prospect(enhancement_type, db_session)
                    
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
                    
                    # Check stop event again before starting LLM processing
                    if self._stop_event.is_set():
                        logger.info("Stop event detected before processing prospect, breaking")
                        break
                    
                    # Process single prospect
                    try:
                        success = self._process_single_prospect(prospect, enhancement_type, db_session)
                        
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
                        db_session.commit()
                        
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
                        db_session.rollback()
                
            except Exception as e:
                logger.error(f"Enhancement process error: {str(e)}")
                with self._lock:
                    self._progress["status"] = "error"
                    self._progress["error_message"] = str(e)
            finally:
                self._processing = False
                
                # Log final results
                try:
                    log_entry = AIEnrichmentLog(
                        enhancement_type=enhancement_type,
                        status="completed" if self._progress["status"] == "completed" else "stopped",
                        processed_count=self._progress["processed"],
                        duration=(datetime.now(timezone.utc) - datetime.fromisoformat(self._progress["started_at"])).total_seconds(),
                        message=f"Processed {self._progress['processed']} of {self._progress['total']} prospects",
                        error=self._progress.get("error_message")
                    )
                    db_session.add(log_entry)
                    db_session.commit()
                except Exception as e:
                    logger.error(f"Failed to log final results: {e}")
                
                db_session.close()
    
    def _get_next_prospect(self, enhancement_type: EnhancementType, db_session: Session) -> Optional[Prospect]:
        """Get the next unprocessed prospect"""
        filter_condition = self._build_enhancement_filter(enhancement_type)
        if filter_condition is not None:
            return db_session.query(Prospect).filter(filter_condition).order_by(Prospect.loaded_at.desc()).first()
        return None
    
    def _ensure_extra_is_dict_iterative(self, prospect):
        """Ensure prospect.extra is a dictionary for iterative processing."""
        import json
        if not prospect.extra:
            prospect.extra = {}
        elif isinstance(prospect.extra, str):
            try:
                prospect.extra = json.loads(prospect.extra)
            except (json.JSONDecodeError, TypeError):
                prospect.extra = {}
        
        if not isinstance(prospect.extra, dict):
            prospect.extra = {}
    
    def _update_prospect_timestamps(self, prospect):
        """Update prospect timestamps and model version."""
        prospect.ollama_processed_at = datetime.now(timezone.utc)
        prospect.ollama_model_version = self.llm_service.model_name
    
    def _process_titles_for_iterative(self, prospect, enhancement_type):
        """Process title enhancement for iterative enhancement."""
        if enhancement_type not in ["titles", "all"]:
            return False
            
        if prospect.title and prospect.description:
            # Check if already enhanced (look for enhanced title in extra field)
            extra_data = prospect.extra
            if isinstance(extra_data, str):
                try:
                    import json
                    extra_data = json.loads(extra_data)
                except (json.JSONDecodeError, TypeError):
                    extra_data = {}
            
            if extra_data and extra_data.get('llm_enhanced_title'):
                return False  # Already enhanced
            
            enhanced_title = self.llm_service.enhance_title_with_llm(
                prospect.title, 
                prospect.description,
                prospect.agency or "",
                prospect_id=prospect.id
            )
            
            if enhanced_title['enhanced_title']:
                # Store enhanced title in extra field
                if not prospect.extra:
                    prospect.extra = {}
                elif isinstance(prospect.extra, str):
                    try:
                        import json
                        prospect.extra = json.loads(prospect.extra)
                    except (json.JSONDecodeError, TypeError):
                        prospect.extra = {}
                
                prospect.extra['llm_enhanced_title'] = {
                    'enhanced_title': enhanced_title['enhanced_title'],
                    'confidence': enhanced_title['confidence'],
                    'reasoning': enhanced_title.get('reasoning', ''),
                    'original_title': prospect.title,
                    'enhanced_at': datetime.now(timezone.utc).isoformat(),
                    'model_used': self.llm_service.model_name
                }
                
                self._update_prospect_timestamps(prospect)
                return True
        
        return False
    
    def _process_values_for_iterative(self, prospect, enhancement_type):
        """Process value parsing for iterative enhancement."""
        if enhancement_type not in ["values", "all"]:
            return False
            
        value_to_parse = None
        if prospect.estimated_value_text and not prospect.estimated_value_single:
            value_to_parse = prospect.estimated_value_text
        elif prospect.estimated_value and not prospect.estimated_value_single:
            # Convert numeric value to text for LLM processing
            value_to_parse = str(prospect.estimated_value)
        
        if value_to_parse:
            # Parse contract value
            parsed_value = self.llm_service.parse_contract_value_with_llm(value_to_parse, prospect_id=prospect.id)
            if parsed_value['single'] is not None:
                prospect.estimated_value_single = float(parsed_value['single'])
                prospect.estimated_value_min = float(parsed_value['min']) if parsed_value['min'] else float(parsed_value['single'])
                prospect.estimated_value_max = float(parsed_value['max']) if parsed_value['max'] else float(parsed_value['single'])
                # Store the text version if it didn't exist
                if not prospect.estimated_value_text:
                    prospect.estimated_value_text = value_to_parse
                self._update_prospect_timestamps(prospect)
                
                # Emit real-time update
                self.llm_service._emit_field_update(prospect.id, 'values', {
                    'estimated_value_min': float(prospect.estimated_value_min) if prospect.estimated_value_min else None,
                    'estimated_value_max': float(prospect.estimated_value_max) if prospect.estimated_value_max else None,
                    'estimated_value_single': float(prospect.estimated_value_single) if prospect.estimated_value_single else None
                })
                
                return True
        
        return False
    
    def _process_naics_for_iterative(self, prospect, enhancement_type):
        """Process NAICS classification for iterative enhancement."""
        if enhancement_type not in ["naics", "all"]:
            return False
            
        if prospect.description and (not prospect.naics or prospect.naics_source != 'llm_inferred'):
            # First check extra field for existing NAICS data
            extra_naics = self.llm_service.extract_naics_from_extra_field(prospect.extra)
            
            if extra_naics['found_in_extra'] and extra_naics['code']:
                # Found NAICS in extra field - populate main fields with standardized format
                prospect.naics = extra_naics['code']
                prospect.naics_description = extra_naics['description']
                prospect.naics_source = 'original'  # Mark as original since it was in source data
                self._update_prospect_timestamps(prospect)
                
                # Mark in extra field to prevent future AI enhancement
                self._ensure_extra_is_dict_iterative(prospect)
                prospect.extra['naics_extracted_from_extra'] = {
                    'extracted_at': datetime.now(timezone.utc).isoformat(),
                    'extracted_by': 'iterative_llm_service_extra_field_check',
                    'original_code': extra_naics['code'],
                    'original_description': extra_naics['description']
                }
                
                logger.info(f"Found NAICS {extra_naics['code']} in extra field for prospect {prospect.id[:8]}...")
                
                # Emit real-time update
                self.llm_service._emit_field_update(prospect.id, 'naics', {
                    'naics': prospect.naics,
                    'naics_description': prospect.naics_description,
                    'naics_source': prospect.naics_source
                })
                
                return True
            
            # No NAICS in extra field, proceed with LLM classification
            classification = self.llm_service.classify_naics_with_llm(prospect.title, prospect.description, prospect_id=prospect.id)
            
            if classification['code']:
                prospect.naics = classification['code']
                prospect.naics_description = classification['description']
                prospect.naics_source = 'llm_inferred'
                self._update_prospect_timestamps(prospect)
                
                # Add confidence to extras
                self._ensure_extra_is_dict_iterative(prospect)
                prospect.extra['llm_classification'] = {
                    'naics_confidence': classification['confidence'],
                    'model_used': self.llm_service.model_name,
                    'classified_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Emit real-time update
                self.llm_service._emit_field_update(prospect.id, 'naics', {
                    'naics': prospect.naics,
                    'naics_description': prospect.naics_description,
                    'naics_source': prospect.naics_source
                })
                
                return True
        
        return False
    
    def _process_titles_for_iterative(self, prospect, enhancement_type):
        """Process title enhancement for iterative enhancement."""
        if enhancement_type not in ["titles", "all"]:
            return False
            
        if prospect.title and not prospect.ai_enhanced_title:
            # Enhance title with LLM
            enhanced_title = self.llm_service.enhance_title_with_llm(
                prospect.title, 
                prospect.description or "",
                prospect.agency or "",
                prospect_id=prospect.id
            )
            
            if enhanced_title['enhanced_title']:
                prospect.ai_enhanced_title = enhanced_title['enhanced_title']
                self._update_prospect_timestamps(prospect)
                
                # Add confidence and reasoning to extras
                self._ensure_extra_is_dict_iterative(prospect)
                prospect.extra['llm_title_enhancement'] = {
                    'confidence': enhanced_title['confidence'],
                    'reasoning': enhanced_title.get('reasoning', ''),
                    'original_title': prospect.title,
                    'model_used': self.llm_service.model_name,
                    'enhanced_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Emit real-time update
                self.llm_service._emit_field_update(prospect.id, 'titles', {
                    'ai_enhanced_title': prospect.ai_enhanced_title
                })
                
                return True
        
        return False
    
    def _process_set_asides_for_iterative(self, prospect: Prospect, enhancement_type: EnhancementType) -> bool:
        """Process set-aside enhancement for a single prospect"""
        if enhancement_type not in ["set_asides", "all"]:
            return False
        
        if not prospect.set_aside or not prospect.set_aside.strip():
            return False
        
        # Check if already processed
        if prospect.inferred_data and prospect.inferred_data.inferred_set_aside:
            return False
        
        try:
            # Use the set-aside enhancement from the LLM service
            enhanced_count = self.llm_service.enhance_prospect_set_asides([prospect])
            
            if enhanced_count > 0:
                # Emit real-time update if we have the method
                if hasattr(self.llm_service, '_emit_field_update'):
                    self.llm_service._emit_field_update(prospect.id, 'set_asides', {
                        'inferred_set_aside': prospect.inferred_data.inferred_set_aside if prospect.inferred_data else None
                    })
                
                return True
        
        except Exception as e:
            logger.error(f"Error processing set-aside for prospect {prospect.id}: {e}")
        
        return False
    
    def _process_single_prospect(
        self, 
        prospect: Prospect, 
        enhancement_type: EnhancementType, 
        db_session: Session
    ) -> bool:
        """Process a single prospect based on enhancement type"""
        try:
            processed = False
            
            # Process each enhancement type
            # Process in new order: Title → Value → NAICS → Set-Asides
            if self._process_titles_for_iterative(prospect, enhancement_type):
                processed = True
            
            if self._process_values_for_iterative(prospect, enhancement_type):
                processed = True
            
            if self._process_naics_for_iterative(prospect, enhancement_type):
                processed = True
            
            if self._process_set_asides_for_iterative(prospect, enhancement_type):
                processed = True
            
            return processed
            
        except Exception as e:
            logger.error(f"Error in _process_single_prospect: {str(e)}")
            return False


# Global instance for maintaining state across requests
iterative_service_v2 = IterativeLLMServiceV2()