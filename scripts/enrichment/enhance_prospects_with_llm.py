#!/usr/bin/env python
"""
Script to enhance prospects with LLM-based data extraction and classification.
Uses qwen3:8b via Ollama for modular enhancement.
"""

import sys
import logging
import argparse
from pathlib import Path
from typing import Optional

# Add project root to sys.path
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from app import create_app
from app.database import db
from app.database.models import Prospect
from app.services.contract_llm_service import ContractLLMService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_ollama_status(model_name: str = 'qwen3:8b') -> bool:
    """Check if Ollama is running and model is available"""
    try:
        from app.utils.llm_utils import call_ollama
        response = call_ollama("Test", model_name)
        if response:
            logger.info(f"✓ Ollama is running with {model_name} model")
            return True
        else:
            logger.error(f"✗ Ollama is not responding or {model_name} model is not available")
            return False
    except Exception as e:
        logger.error(f"✗ Error checking Ollama: {e}")
        return False


def get_enhancement_stats() -> dict:
    """Get statistics about prospects needing enhancement"""
    stats = {
        'total_prospects': Prospect.query.count(),
        'already_processed': Prospect.query.filter(
            Prospect.ollama_processed_at.isnot(None)
        ).count(),
        'missing_naics': Prospect.query.filter(
            Prospect.naics.is_(None)
        ).count(),
        'missing_value_parsing': Prospect.query.filter(
            Prospect.estimated_value_text.isnot(None),
            Prospect.estimated_value_single.is_(None)
        ).count(),
        'missing_contact': Prospect.query.filter(
            Prospect.primary_contact_email.is_(None),
            Prospect.extra.isnot(None)
        ).count()
    }
    
    stats['needs_processing'] = stats['total_prospects'] - stats['already_processed']
    
    return stats


def run_targeted_enhancement(
    enhancement_type: str,
    limit: Optional[int] = None,
    batch_size: int = 50
) -> int:
    """
    Run a specific type of enhancement.
    
    Args:
        enhancement_type: One of 'values', 'contacts', 'naics', or 'all'
        limit: Maximum number of prospects to process
        batch_size: Number of prospects to process per batch
    
    Returns:
        Number of prospects enhanced
    """
    llm_service = ContractLLMService()
    llm_service.batch_size = batch_size
    
    # Build query based on enhancement type
    if enhancement_type == 'values':
        query = Prospect.query.filter(
            Prospect.estimated_value_text.isnot(None),
            Prospect.estimated_value_single.is_(None)
        )
    elif enhancement_type == 'contacts':
        query = Prospect.query.filter(
            Prospect.primary_contact_email.is_(None),
            Prospect.extra.isnot(None)
        )
    elif enhancement_type == 'naics':
        query = Prospect.query.filter(
            Prospect.naics.is_(None)
        )
    elif enhancement_type == 'all':
        query = Prospect.query.filter(
            Prospect.ollama_processed_at.is_(None)
        )
    else:
        raise ValueError(f"Unknown enhancement type: {enhancement_type}")
    
    if limit:
        query = query.limit(limit)
    
    prospects = query.all()
    logger.info(f"Found {len(prospects)} prospects for {enhancement_type} enhancement")
    
    if not prospects:
        return 0
    
    # Run enhancement based on type
    if enhancement_type == 'values':
        return llm_service.enhance_prospect_values(prospects)
    elif enhancement_type == 'contacts':
        return llm_service.enhance_prospect_contacts(prospects)
    elif enhancement_type == 'naics':
        return llm_service.enhance_prospect_naics(prospects)
    elif enhancement_type == 'all':
        results = llm_service.enhance_all_prospects(limit=limit)
        return sum(results.values()) - results['total_prospects']


def main():
    parser = argparse.ArgumentParser(
        description='Enhance prospects with LLM-based data extraction'
    )
    parser.add_argument(
        'enhancement_type',
        choices=['values', 'contacts', 'naics', 'all'],
        help='Type of enhancement to run'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of prospects to process'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Number of prospects to process per batch (default: 50)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show statistics only, do not run enhancement'
    )
    parser.add_argument(
        '--skip-check',
        action='store_true',
        help='Skip Ollama availability check'
    )
    
    args = parser.parse_args()
    
    app = create_app()
    with app.app_context():
        # Show statistics
        if args.stats:
            stats = get_enhancement_stats()
            logger.info("\nProspect Enhancement Statistics:")
            logger.info(f"  Total prospects: {stats['total_prospects']:,}")
            logger.info(f"  Already processed: {stats['already_processed']:,}")
            logger.info(f"  Needs processing: {stats['needs_processing']:,}")
            logger.info(f"  Missing NAICS: {stats['missing_naics']:,}")
            logger.info(f"  Missing value parsing: {stats['missing_value_parsing']:,}")
            logger.info(f"  Missing contact extraction: {stats['missing_contact']:,}")
            return
        
        # Check Ollama status
        if not args.skip_check:
            if not check_ollama_status():
                logger.error("\nPlease ensure Ollama is running and qwen3:8b model is available:")
                logger.error("  1. Start Ollama: ollama serve")
                logger.error("  2. Pull model: ollama pull qwen3:8b")
                return
        
        # Run enhancement
        logger.info(f"\nStarting {args.enhancement_type} enhancement...")
        enhanced_count = run_targeted_enhancement(
            args.enhancement_type,
            limit=args.limit,
            batch_size=args.batch_size
        )
        
        logger.info(f"\nEnhancement complete!")
        logger.info(f"Successfully enhanced {enhanced_count} prospects")
        
        # Show updated statistics
        stats = get_enhancement_stats()
        logger.info(f"\nUpdated statistics:")
        logger.info(f"  Processed prospects: {stats['already_processed']:,}")
        logger.info(f"  Remaining to process: {stats['needs_processing']:,}")


if __name__ == "__main__":
    main()