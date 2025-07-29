"""
Enhancement Queue Service

Manages a priority queue system where individual prospect enhancement requests
take precedence over bulk database enhancement operations.
"""

import threading
import queue
import time
from datetime import datetime, timezone
from typing import Dict, Optional, List, Literal, Any
from dataclasses import dataclass
from enum import Enum

from app.utils.logger import logger
from app.services.contract_llm_service import ContractLLMService
from app.database.models import Prospect, db
from app.database import db as db_instance

EnhancementType = Literal["all", "values", "titles", "naics", "set_asides"]


class QueueItemType(Enum):
    INDIVIDUAL = "individual"
    BULK = "bulk"


class QueueItemStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueueItem:
    """Represents an item in the enhancement queue"""
    id: str
    type: QueueItemType
    priority: int  # Lower number = higher priority (individual = 1, bulk = 10)
    prospect_id: Optional[int] = None
    prospect_ids: Optional[List[int]] = None
    enhancement_type: EnhancementType = "all"
    user_id: Optional[int] = None
    force_redo: bool = False
    status: QueueItemStatus = QueueItemStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    progress: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.progress is None:
            self.progress = {"processed": 0, "total": 1 if self.prospect_id else 0}


class EnhancementQueueService:
    """Service for managing prioritized enhancement queue
    
    Queue Processing Workflow:
    1. Individual requests get priority 1 (highest)
    2. Bulk operations get priority 10 (lower)
    3. Worker thread processes items in priority order
    4. Bulk operations can be interrupted by high-priority individual requests
    
    This ensures responsive UI - users see their individual enhancements
    processed immediately, while bulk operations run in the background.
    """
    
    def __init__(self):
        self.llm_service = ContractLLMService()
        self._queue = queue.PriorityQueue()
        self._processing = False
        self._current_item: Optional[QueueItem] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        # Storage for queue items (for status tracking)
        self._queue_items: Dict[str, QueueItem] = {}
        self._completed_items: List[QueueItem] = []
        
        # Reference to bulk processing service
        self._bulk_service = None  # Will be set by dependency injection
        
    def set_bulk_service(self, bulk_service):
        """Set reference to the bulk processing service for coordination"""
        self._bulk_service = bulk_service
        
    def start_worker(self):
        """Start the queue worker thread"""
        if self._processing:
            return
            
        self._processing = True
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()
        logger.info("Enhancement queue worker started")
        
    def stop_worker(self):
        """Stop the queue worker thread"""
        if not self._processing:
            return
            
        self._stop_event.set()
        self._processing = False
        
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=30)
            
        logger.info("Enhancement queue worker stopped")
        
    def add_individual_enhancement(
        self, 
        prospect_id, 
        enhancement_type: EnhancementType = "all", 
        user_id: Optional[int] = None,
        force_redo: bool = False
    ) -> str:
        """Add an individual prospect enhancement to the queue"""
        
        logger.info(f"ADD_INDIVIDUAL_ENHANCEMENT called for prospect {prospect_id}")
        
        with self._lock:
            # Check if this prospect is already being processed or queued
            logger.info(f"DEDUP_CHECK: Checking for existing queue items for prospect {prospect_id}")
            queue_items_count = len(self._queue_items)
            logger.info(f"DEDUP_CHECK: Total queue items in memory: {queue_items_count}")
            
            for item in self._queue_items.values():
                logger.info(f"DEDUP_CHECK: item {item.id}: prospect={item.prospect_id}, type={item.type.value}, status={item.status.value}")
                if (str(item.prospect_id) == str(prospect_id) and 
                    item.type == QueueItemType.INDIVIDUAL and
                    item.status in [QueueItemStatus.PENDING, QueueItemStatus.PROCESSING]):
                    logger.info(f"DEDUP_FOUND: Prospect {prospect_id} already in queue with ID {item.id}, status {item.status.value}")
                    return item.id
            logger.info(f"DEDUP_CHECK: No existing queue item found for prospect {prospect_id} - creating new one")
        
        # Generate unique item ID
        item_id = f"individual_{prospect_id}_{int(time.time() * 1000)}"
        
        queue_item = QueueItem(
            id=item_id,
            type=QueueItemType.INDIVIDUAL,
            priority=1,  # High priority
            prospect_id=prospect_id,
            enhancement_type=enhancement_type,
            user_id=user_id,
            force_redo=force_redo
        )
        
        with self._lock:
            self._queue_items[item_id] = queue_item
            
        # Add to priority queue (priority, timestamp, item) for stable sorting
        # The timestamp ensures FIFO ordering for items with same priority
        self._queue.put((queue_item.priority, time.time(), queue_item))
        
        # If bulk processing is running and we have high priority item, signal interruption
        # This allows individual requests to "jump the queue" ahead of bulk operations
        if self._bulk_service and self._bulk_service.is_processing():
            logger.info(f"Individual enhancement request added - signaling bulk process to yield")
            # The bulk process should check for high priority items periodically
            
        logger.info(f"Added individual enhancement for prospect {prospect_id} to queue with ID {item_id}")
        return item_id
        
    def add_bulk_enhancement(
        self, 
        prospect_ids: List[int], 
        enhancement_type: EnhancementType = "all",
        user_id: Optional[int] = None
    ) -> str:
        """Add a bulk enhancement operation to the queue"""
        
        item_id = f"bulk_{enhancement_type}_{int(time.time() * 1000)}"
        
        queue_item = QueueItem(
            id=item_id,
            type=QueueItemType.BULK,
            priority=10,  # Lower priority than individual requests (1)
            prospect_ids=prospect_ids,
            enhancement_type=enhancement_type,
            user_id=user_id,
            progress={"processed": 0, "total": len(prospect_ids)}
        )
        
        with self._lock:
            self._queue_items[item_id] = queue_item
            
        self._queue.put((queue_item.priority, time.time(), queue_item))
        
        logger.info(f"Added bulk enhancement for {len(prospect_ids)} prospects to queue with ID {item_id}")
        return item_id
        
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        with self._lock:
            pending_items = [item for item in self._queue_items.values() 
                           if item.status == QueueItemStatus.PENDING]
            
            # Sort by priority and creation time
            pending_items.sort(key=lambda x: (x.priority, x.created_at))
            
            return {
                "worker_running": self._processing,
                "current_item": self._current_item.id if self._current_item else None,
                "queue_size": len(pending_items),
                "pending_items": [
                    {
                        "id": item.id,
                        "type": item.type.value,
                        "priority": item.priority,
                        "prospect_id": item.prospect_id,
                        "prospect_count": len(item.prospect_ids) if item.prospect_ids else 1,
                        "enhancement_type": item.enhancement_type,
                        "created_at": item.created_at.isoformat(),
                        "status": item.status.value
                    }
                    for item in pending_items[:10]  # Show first 10 items
                ],
                "recent_completed": [
                    {
                        "id": item.id,
                        "type": item.type.value,
                        "prospect_id": item.prospect_id,
                        "status": item.status.value,
                        "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                        "error_message": item.error_message
                    }
                    for item in self._completed_items[-5:]  # Show last 5 completed
                ]
            }
            
    def get_item_status(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific queue item"""
        with self._lock:
            item = self._queue_items.get(item_id)
            if not item:
                return None
                
            return {
                "id": item.id,
                "type": item.type.value,
                "status": item.status.value,
                "prospect_id": item.prospect_id,
                "prospect_count": len(item.prospect_ids) if item.prospect_ids else 1,
                "enhancement_type": item.enhancement_type,
                "created_at": item.created_at.isoformat(),
                "started_at": item.started_at.isoformat() if item.started_at else None,
                "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                "progress": item.progress,
                "error_message": item.error_message
            }
            
    def cancel_item(self, item_id: str) -> bool:
        """Cancel a queue item (only if not currently processing)"""
        with self._lock:
            item = self._queue_items.get(item_id)
            if not item:
                return False
                
            if item.status == QueueItemStatus.PROCESSING:
                return False  # Cannot cancel currently processing item
                
            if item.status == QueueItemStatus.PENDING:
                item.status = QueueItemStatus.CANCELLED
                item.completed_at = datetime.now(timezone.utc)
                self._completed_items.append(item)
                return True
                
            return False
            
    def has_high_priority_items(self) -> bool:
        """Check if there are high priority items waiting"""
        with self._lock:
            return any(
                item.status == QueueItemStatus.PENDING and item.priority <= 5
                for item in self._queue_items.values()
            )
            
    def _process_queue(self):
        """Main queue processing loop"""
        from app import create_app
        app = create_app()
        
        with app.app_context():
            while self._processing and not self._stop_event.is_set():
                try:
                    # Get next item from queue (blocks with timeout)
                    try:
                        priority, timestamp, queue_item = self._queue.get(timeout=1.0)
                    except queue.Empty:
                        continue
                        
                    # Check if item was cancelled
                    if queue_item.status == QueueItemStatus.CANCELLED:
                        self._queue.task_done()
                        continue
                        
                    # Process the item
                    with self._lock:
                        self._current_item = queue_item
                        queue_item.status = QueueItemStatus.PROCESSING
                        queue_item.started_at = datetime.now(timezone.utc)
                        
                    logger.info(f"Processing queue item {queue_item.id} (type: {queue_item.type.value})")
                    
                    try:
                        if queue_item.type == QueueItemType.INDIVIDUAL:
                            self._process_individual_item(queue_item)
                        else:
                            self._process_bulk_item(queue_item)
                            
                        queue_item.status = QueueItemStatus.COMPLETED
                        
                    except Exception as e:
                        logger.error(f"Error processing queue item {queue_item.id}: {e}", exc_info=True)
                        queue_item.status = QueueItemStatus.FAILED
                        queue_item.error_message = str(e)
                        
                    finally:
                        queue_item.completed_at = datetime.now(timezone.utc)
                        
                        with self._lock:
                            self._current_item = None
                            self._completed_items.append(queue_item)
                            
                            # Keep only last 50 completed items
                            if len(self._completed_items) > 50:
                                self._completed_items = self._completed_items[-50:]
                                
                        self._queue.task_done()
                        
                        logger.info(f"Completed queue item {queue_item.id} with status {queue_item.status.value}")
                        
                except Exception as e:
                    logger.error(f"Error in queue processing loop: {e}", exc_info=True)
                    time.sleep(1)  # Brief pause before retrying
                    
        logger.info("Queue processing loop ended")
        
    def _process_individual_item(self, queue_item: QueueItem):
        """Process an individual prospect enhancement"""
        from app.api.llm_processing import (
            _process_value_enhancement,
            _process_naics_enhancement,
            _process_title_enhancement,
            _process_set_aside_enhancement,
            _ensure_extra_is_dict,
            emit_enhancement_progress
        )
        
        prospect = db_instance.session.query(Prospect).get(queue_item.prospect_id)
        if not prospect:
            raise ValueError(f"Prospect {queue_item.prospect_id} not found")
            
        # Check for concurrency conflicts
        if prospect.enhancement_status == 'in_progress' and prospect.enhancement_user_id != queue_item.user_id:
            raise ValueError(f"Prospect is being enhanced by another user")
            
        # Lock the prospect
        prospect.enhancement_status = 'in_progress'
        prospect.enhancement_started_at = datetime.now(timezone.utc)
        prospect.enhancement_user_id = queue_item.user_id
        db_instance.session.commit()
        
        try:
            processed = False
            enhancements = []
            
            # Process each enhancement type based on queue_item.enhancement_type
            requested_types = []
            if queue_item.enhancement_type == "all":
                requested_types = ["titles", "values", "naics", "set_asides"]
            else:
                # Parse comma-separated enhancement types
                requested_types = [t.strip() for t in queue_item.enhancement_type.split(',')]
            
            # Process in order: Title → Value → NAICS → Set-Asides
            if "titles" in requested_types:
                if _process_title_enhancement(prospect, self.llm_service, queue_item.force_redo):
                    processed = True
                    enhancements.append('titles')
                    
            if "values" in requested_types:
                if _process_value_enhancement(prospect, self.llm_service, queue_item.force_redo):
                    processed = True
                    enhancements.append('values')
                    
            if "naics" in requested_types:
                if _process_naics_enhancement(prospect, self.llm_service, queue_item.force_redo):
                    processed = True
                    enhancements.append('naics')
                    
            if "set_asides" in requested_types:
                if _process_set_aside_enhancement(prospect, self.llm_service, queue_item.force_redo):
                    processed = True
                    enhancements.append('set_asides')
                
            # Finalize
            if processed or queue_item.force_redo:
                prospect.ollama_processed_at = datetime.now(timezone.utc)
                prospect.ollama_model_version = self.llm_service.model_name
                
            # Update progress
            queue_item.progress = {
                "processed": 1,
                "total": 1,
                "enhancements": enhancements
            }
            
        finally:
            # Always unlock the prospect
            prospect.enhancement_status = 'idle'
            prospect.enhancement_started_at = None
            prospect.enhancement_user_id = None
            db_instance.session.commit()
            
            # Emit completion event (similar to _finalize_enhancement)
            if processed or queue_item.force_redo:
                emit_enhancement_progress(prospect.id, 'completed', {
                    'status': 'completed',
                    'processed': True,
                    'enhancements': enhancements,
                    'ollama_processed_at': prospect.ollama_processed_at.isoformat() if prospect.ollama_processed_at else None,
                    'model_version': prospect.ollama_model_version
                })
            else:
                # Emit completion event for cases where no processing was needed
                emit_enhancement_progress(prospect.id, 'completed', {
                    'status': 'completed',
                    'processed': False,
                    'enhancements': [],
                    'ollama_processed_at': prospect.ollama_processed_at.isoformat() if prospect.ollama_processed_at else None,
                    'reason': 'Already fully enhanced or no data to enhance'
                })
            
    def _process_bulk_item(self, queue_item: QueueItem):
        """Process a bulk enhancement operation with interruptibility"""
        from app.api.llm_processing import (
            _process_value_enhancement,
            _process_naics_enhancement, 
            _process_title_enhancement,
            _process_set_aside_enhancement
        )
        
        if not queue_item.prospect_ids:
            return
            
        processed_count = 0
        
        for i, prospect_id in enumerate(queue_item.prospect_ids):
            # Check if we should yield to higher priority items
            if self.has_high_priority_items():
                logger.info(f"Yielding bulk processing to higher priority items at {i}/{len(queue_item.prospect_ids)}")
                # Re-queue remaining items
                remaining_ids = queue_item.prospect_ids[i:]
                if remaining_ids:
                    self.add_bulk_enhancement(
                        remaining_ids, 
                        queue_item.enhancement_type,
                        queue_item.user_id
                    )
                break
                
            # Check stop event
            if self._stop_event.is_set():
                logger.info("Stop event detected in bulk processing")
                break
                
            try:
                prospect = db_instance.session.query(Prospect).get(prospect_id)
                if not prospect:
                    continue
                    
                # Skip if being processed by someone else
                if prospect.enhancement_status == 'in_progress':
                    continue
                    
                # Process prospect
                processed = False
                
                # Process in new order: Title → Value → NAICS
                # Process based on enhancement type
                requested_types = []
                if queue_item.enhancement_type == "all":
                    requested_types = ["titles", "values", "naics", "set_asides"]
                else:
                    requested_types = [t.strip() for t in queue_item.enhancement_type.split(',')]
                
                if "titles" in requested_types:
                    if _process_title_enhancement(prospect, self.llm_service, False):
                        processed = True
                        
                if "values" in requested_types:
                    if _process_value_enhancement(prospect, self.llm_service, False):
                        processed = True
                        
                if "naics" in requested_types:
                    if _process_naics_enhancement(prospect, self.llm_service, False):
                        processed = True
                        
                if "set_asides" in requested_types:
                    if _process_set_aside_enhancement(prospect, self.llm_service, False):
                        processed = True
                    
                if processed:
                    prospect.ollama_processed_at = datetime.now(timezone.utc)
                    prospect.ollama_model_version = self.llm_service.model_name
                    processed_count += 1
                    
                db_instance.session.commit()
                
                # Update progress
                queue_item.progress["processed"] = processed_count
                
                logger.info(f"Bulk processed prospect {prospect_id}: {processed_count}/{len(queue_item.prospect_ids)}")
                
            except Exception as e:
                logger.error(f"Error processing prospect {prospect_id} in bulk: {e}")
                continue
                
        queue_item.progress["processed"] = processed_count


# Global instance
enhancement_queue_service = EnhancementQueueService()