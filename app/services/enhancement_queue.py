"""
Simplified Enhancement Queue

Replaces the complex EnhancementQueueService with simple function-based processing.
This maintains the same API but with significantly reduced complexity.
"""

import threading
import time
from datetime import datetime, timezone
from typing import Dict, Optional, List, Literal, Any
from dataclasses import dataclass, field
from enum import Enum

from app.utils.logger import logger
from app.database.models import Prospect, db
from app.services.llm_service import llm_service, EnhancementType


class QueueStatus(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class EnhancementProgress:
    """Simple progress tracking for enhancements"""
    status: QueueStatus = QueueStatus.IDLE
    enhancement_type: Optional[EnhancementType] = None
    processed: int = 0
    total: int = 0
    current_prospect_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)


class MockQueueItem:
    """Mock queue item for backward compatibility with API expectations"""
    def __init__(self, prospect_id: str, user_id: int, enhancement_type: str, processing_type: str, status: str):
        self.prospect_id = prospect_id
        self.user_id = user_id
        self.enhancement_type = enhancement_type
        self.processing_type = processing_type
        self._status = status
    
    @property
    def type(self):
        """Mock type enum with value attribute"""
        class MockType:
            def __init__(self, value):
                self.value = value
        return MockType(self.processing_type)
    
    @property 
    def status(self):
        """Mock status enum with value attribute"""
        class MockStatus:
            def __init__(self, value):
                self.value = value
        return MockStatus(self._status)


class SimpleEnhancementQueue:
    """
    Simplified enhancement queue that handles both individual and bulk processing
    without the complexity of priority queues and multiple thread management.
    """
    
    def __init__(self):
        self._progress = EnhancementProgress()
        self._processing = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Track current enhancement details for API compatibility
        self._current_prospect_id: Optional[str] = None
        self._current_user_id: Optional[int] = None
        self._current_enhancement_type: Optional[str] = None
        self._current_processing_type: str = "individual"  # 'individual' or 'bulk'
    
    def get_status(self) -> Dict[str, Any]:
        """Get current processing status"""
        with self._lock:
            return {
                "status": self._progress.status.value,
                "enhancement_type": self._progress.enhancement_type,
                "processed": self._progress.processed,
                "total": self._progress.total,
                "current_prospect_id": self._progress.current_prospect_id,
                "started_at": self._progress.started_at.isoformat() if self._progress.started_at else None,
                "completed_at": self._progress.completed_at.isoformat() if self._progress.completed_at else None,
                "errors": self._progress.errors[-10:],  # Keep only last 10 errors
                "is_processing": self._processing
            }
    
    def is_processing(self) -> bool:
        """Check if currently processing"""
        return self._processing
    
    def enhance_single_prospect(self, prospect_id: str, enhancement_type: EnhancementType = "all", user_id: Optional[int] = None, force_redo: bool = False) -> Dict[str, Any]:
        """
        Enhance a single prospect immediately (synchronous).
        This is for real-time UI updates.
        """
        try:
            prospect = Prospect.query.get(prospect_id)
            if not prospect:
                return {"status": "error", "message": f"Prospect {prospect_id} not found"}
            
            # Track current enhancement details for API compatibility
            with self._lock:
                self._current_prospect_id = prospect_id
                self._current_user_id = user_id
                self._current_enhancement_type = enhancement_type
                self._current_processing_type = "individual"
                self._processing = True
            
            logger.info(f"Starting individual enhancement for prospect {prospect_id[:8]}... ({enhancement_type}, force_redo={force_redo})")
            
            # Note: force_redo parameter not yet implemented in LLM service
            # For now, LLM service will use its default enhancement logic
            results = llm_service.enhance_single_prospect(prospect, enhancement_type)
            
            if any(results.values()):
                db.session.commit()
                logger.info(f"Successfully enhanced prospect {prospect_id[:8]}... - {results}")
                return {
                    "status": "completed",
                    "prospect_id": prospect_id,
                    "enhancements": results,
                    "message": f"Enhanced {sum(results.values())} fields"
                }
            else:
                return {
                    "status": "no_changes",
                    "prospect_id": prospect_id,
                    "message": "No enhancements needed or possible"
                }
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error enhancing single prospect {prospect_id}: {e}")
            return {
                "status": "error", 
                "prospect_id": prospect_id,
                "message": str(e)
            }
        finally:
            # Clear current enhancement tracking
            with self._lock:
                self._current_prospect_id = None
                self._current_user_id = None
                self._current_enhancement_type = None
                self._processing = False
    
    def start_bulk_enhancement(self, enhancement_type: EnhancementType = "all", 
                             prospect_ids: Optional[List[str]] = None,
                             skip_existing: bool = True) -> Dict[str, Any]:
        """
        Start bulk enhancement processing in background thread.
        """
        if self._processing:
            return {"status": "error", "message": "Enhancement already in progress"}
        
        # Get prospects to process
        if prospect_ids:
            prospects = Prospect.query.filter(Prospect.id.in_(prospect_ids)).all()
        else:
            prospects = self._get_prospects_needing_enhancement(enhancement_type, skip_existing)
        
        if not prospects:
            return {
                "status": "completed",
                "message": "No prospects need enhancement",
                "total": 0
            }
        
        # Initialize progress
        with self._lock:
            self._progress = EnhancementProgress(
                status=QueueStatus.PROCESSING,
                enhancement_type=enhancement_type,
                total=len(prospects),
                started_at=datetime.now(timezone.utc)
            )
        
        self._processing = True
        self._stop_event.clear()
        
        # Start background thread
        self._thread = threading.Thread(
            target=self._bulk_processing_worker,
            args=(prospects, enhancement_type),
            daemon=True
        )
        self._thread.start()
        
        logger.info(f"Started bulk enhancement: {len(prospects)} prospects for {enhancement_type}")
        
        return {
            "status": "started",
            "enhancement_type": enhancement_type,
            "total": len(prospects),
            "message": f"Started bulk enhancement of {len(prospects)} prospects"
        }
    
    def stop_processing(self) -> Dict[str, Any]:
        """Stop current processing"""
        if not self._processing:
            return {"status": "error", "message": "No processing currently running"}
        
        logger.info("Stopping enhancement processing...")
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        
        with self._lock:
            self._progress.status = QueueStatus.STOPPED
            self._progress.completed_at = datetime.now(timezone.utc)
        
        self._processing = False
        
        return {"status": "stopped", "message": "Enhancement processing stopped"}
    
    # Backward compatibility methods for API
    def get_queue_status(self) -> Dict[str, Any]:
        """Alias for get_status for backward compatibility"""
        return self.get_status()
    
    def get_item_status(self, item_id: str) -> Dict[str, Any]:
        """Get status of a specific item (simplified implementation)"""
        status = self.get_status()
        return {
            "item_id": item_id,
            "status": status.get("status", "unknown"),
            "progress": status.get("progress", {}),
            "message": f"Status for item {item_id}"
        }
    
    def cancel_item(self, item_id: str) -> bool:
        """Cancel a specific item (simplified - just stops current processing)"""
        if self._processing:
            self.stop_processing()
            return True
        return False
    
    def start_worker(self) -> Dict[str, Any]:
        """Start worker (no-op for simplified implementation)"""
        return {"status": "ready", "message": "Worker ready"}
    
    def stop_worker(self) -> Dict[str, Any]:
        """Stop worker (alias for stop_processing)"""
        return self.stop_processing()
    
    @property
    def _queue_items(self) -> Dict[str, MockQueueItem]:
        """Backward compatibility for queue items access"""
        with self._lock:
            if self._processing and self._current_prospect_id:
                # Create mock queue item with expected attributes
                mock_item = MockQueueItem(
                    prospect_id=self._current_prospect_id,
                    user_id=self._current_user_id or 1,
                    enhancement_type=self._current_enhancement_type or "all",
                    processing_type=self._current_processing_type,
                    status="processing" if self._processing else "pending"
                )
                return {"current": mock_item}
            else:
                return {}
    
    def _get_prospects_needing_enhancement(self, enhancement_type: EnhancementType, skip_existing: bool) -> List[Prospect]:
        """Get prospects that need the specified enhancement type"""
        query = Prospect.query
        
        if skip_existing:
            if enhancement_type == "values":
                query = query.filter(Prospect.estimated_value_single.is_(None))
            elif enhancement_type == "naics":
                query = query.filter(
                    (Prospect.naics.is_(None)) | 
                    (Prospect.naics_source != 'llm_inferred')
                )
            elif enhancement_type == "titles":
                query = query.filter(Prospect.ai_enhanced_title.is_(None))
            elif enhancement_type == "set_asides":
                query = query.filter(Prospect.set_aside_standardized.is_(None))
            # For "all", we don't filter - check each enhancement individually
        
        return query.limit(10000).all()  # Reasonable limit to prevent memory issues
    
    def _bulk_processing_worker(self, prospects: List[Prospect], enhancement_type: EnhancementType):
        """Worker thread for bulk processing"""
        logger.info(f"Bulk processing worker started: {len(prospects)} prospects")
        
        try:
            for i, prospect in enumerate(prospects):
                if self._stop_event.is_set():
                    logger.info("Bulk processing stopped by user request")
                    break
                
                # Update progress
                with self._lock:
                    self._progress.current_prospect_id = prospect.id
                
                try:
                    results = llm_service.enhance_single_prospect(prospect, enhancement_type)
                    
                    if any(results.values()):
                        db.session.commit()
                        logger.debug(f"Enhanced prospect {prospect.id[:8]}... - {results}")
                    
                    with self._lock:
                        self._progress.processed = i + 1
                        
                except Exception as e:
                    logger.error(f"Error processing prospect {prospect.id}: {e}")
                    with self._lock:
                        self._progress.errors.append(f"Prospect {prospect.id[:8]}...: {str(e)}")
                        self._progress.processed = i + 1  # Still count as processed
                
                # Brief pause to prevent overwhelming the system
                if not self._stop_event.wait(0.1):  # 100ms delay, but can be interrupted
                    continue
                else:
                    break
            
            # Mark as completed
            with self._lock:
                if not self._stop_event.is_set():
                    self._progress.status = QueueStatus.COMPLETED
                    logger.info(f"Bulk processing completed: {self._progress.processed}/{self._progress.total} prospects")
                else:
                    self._progress.status = QueueStatus.STOPPED
                    logger.info(f"Bulk processing stopped: {self._progress.processed}/{self._progress.total} prospects")
                
                self._progress.completed_at = datetime.now(timezone.utc)
                    
        except Exception as e:
            logger.error(f"Error in bulk processing worker: {e}")
            with self._lock:
                self._progress.status = QueueStatus.FAILED
                self._progress.errors.append(f"Worker error: {str(e)}")
                self._progress.completed_at = datetime.now(timezone.utc)
        finally:
            self._processing = False


# Global instance
enhancement_queue = SimpleEnhancementQueue()


# Backward compatibility functions
def add_individual_enhancement(prospect_id: str, enhancement_type: EnhancementType = "all", user_id: Optional[int] = None, force_redo: bool = False) -> Dict[str, Any]:
    """Add individual prospect enhancement (immediate processing)"""
    result = enhancement_queue.enhance_single_prospect(prospect_id, enhancement_type, user_id, force_redo)
    
    queue_item_id = f"individual_{prospect_id}_{int(time.time())}"
    
    return {
        "queue_item_id": queue_item_id,
        "was_existing": False,  # For individual enhancements, always treat as new
        "status": result.get("status", "completed"),
        "message": result.get("message", "Enhancement completed"),
        "prospect_id": prospect_id,
        "enhancements": result.get("enhancements", {})
    }


def add_bulk_enhancement(prospect_ids: List[str], enhancement_type: EnhancementType = "all") -> str:
    """Add bulk enhancement (background processing)"""
    enhancement_queue.start_bulk_enhancement(enhancement_type, prospect_ids)
    return f"bulk_{enhancement_type}_{int(time.time())}"


def get_queue_status() -> Dict[str, Any]:
    """Get current queue status"""
    return enhancement_queue.get_status()


def stop_processing() -> Dict[str, Any]:
    """Stop current processing"""
    return enhancement_queue.stop_processing()