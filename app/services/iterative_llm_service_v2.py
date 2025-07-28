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
from app.services.base_llm_service import BaseLLMService
from app.services.llm_service_utils import (
    ensure_extra_is_dict, 
    update_prospect_timestamps, 
    emit_field_update,
    should_skip_prospect
)
from app.utils.logger import logger
from app.database import db

EnhancementType = Literal["all", "values", "titles", "naics", "set_asides"]


class IterativeLLMServiceV2:
    """Service for iterative one-by-one LLM enhancement with start/stop control"""
    
    def __init__(self):
        self.base_service = BaseLLMService()
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
        self._emit_callback = None  # For real-time field updates
    
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
    
    def set_emit_callback(self, emit_callback):
        """Set callback for real-time field updates"""
        self._emit_callback = emit_callback

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
                        "message": f"Added {len(prospect_ids)} prospects to queue",
                        "total_to_process": len(prospect_ids),
                        "queue_item_id": queue_item_id
                    }
                else:
                    # Fallback to direct processing if no queue service
                    return self._start_direct_processing(enhancement_type, app)
                    
            finally:
                db_session.close()

    def stop_enhancement(self) -> Dict[str, any]:
        """Stop the current enhancement process"""
        if not self._processing:
            return {"status": "idle", "message": "No enhancement process running"}
        
        self._stop_event.set()
        
        # Wait for thread to finish with timeout
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)  # 10 second timeout
        
        with self._lock:
            self._processing = False
            self._progress["status"] = "stopped"
        
        return {"status": "stopped", "message": "Enhancement process stopped"}

    def _build_enhancement_filter(self, enhancement_type: EnhancementType, skip_existing: bool = True):
        """Build SQLAlchemy filter for prospects that need enhancement"""
        if not skip_existing:
            # Process all prospects that have any data for enhancement
            return or_(
                Prospect.estimated_value_text.isnot(None),
                Prospect.estimated_value.isnot(None),
                Prospect.extra.isnot(None),
                Prospect.description.isnot(None),
                Prospect.title.isnot(None)
            )
        
        if enhancement_type == "values":
            return and_(
                or_(
                    Prospect.estimated_value_text.isnot(None),
                    Prospect.estimated_value.isnot(None)
                ),
                Prospect.estimated_value_single.is_(None)
            )
        elif enhancement_type == "naics":
            return and_(
                Prospect.description.isnot(None),
                or_(
                    Prospect.naics.is_(None),
                    Prospect.naics_source != 'llm_inferred'
                )
            )
        elif enhancement_type == "titles":
            return and_(
                Prospect.title.isnot(None),
                Prospect.ai_enhanced_title.is_(None)
            )
        elif enhancement_type == "set_asides":
            return and_(
                Prospect.set_aside.isnot(None),
                Prospect.set_aside_standardized.is_(None)
            )
        elif enhancement_type == "all":
            # Skip prospects that need any enhancement
            return or_(
                # Needs value parsing
                and_(
                    or_(
                        and_(
                            Prospect.estimated_value_text.isnot(None),
                            Prospect.estimated_value_single.is_(None)
                        ),
                        and_(
                            Prospect.estimated_value.isnot(None),
                            Prospect.estimated_value_single.is_(None)
                        )
                    )
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
                ),
                # Needs set-aside standardization
                and_(
                    Prospect.set_aside.isnot(None),
                    Prospect.set_aside_standardized.is_(None)
                )
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
                    
                    # Process single prospect using the base service
                    try:
                        def progress_callback(update):
                            """Callback for progress updates during enhancement"""
                            if self._emit_callback:
                                emit_field_update(
                                    prospect_id=update.get("prospect_id"),
                                    field_type=update.get("field", "unknown"),
                                    field_data=update,
                                    emit_callback=self._emit_callback
                                )
                        
                        results = self.base_service.process_single_prospect_enhancement(
                            prospect=prospect,
                            enhancement_type=enhancement_type,
                            progress_callback=progress_callback
                        )
                        
                        success = any(results.values())
                        
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


# Module-level instance for backward compatibility
iterative_service_v2 = IterativeLLMServiceV2()