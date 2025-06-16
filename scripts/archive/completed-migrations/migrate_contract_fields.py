#!/usr/bin/env python
"""
Script to migrate existing prospects to populate new contract mapping fields.
Extracts data from extra JSON fields and populates standardized fields.
"""

import sys
import logging
from pathlib import Path
from typing import Optional

# Add project root to sys.path
_project_root = Path(__file__).resolve().parents[1]
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


def migrate_existing_naics_data():
    """
    Migrate existing NAICS data from the naics field to new fields.
    Parses NAICS codes and descriptions from various formats.
    """
    logger.info("Starting NAICS data migration...")
    
    # Get prospects with NAICS but no naics_source
    prospects = Prospect.query.filter(
        Prospect.naics.isnot(None),
        Prospect.naics_source.is_(None)
    ).all()
    
    logger.info(f"Found {len(prospects)} prospects with NAICS to migrate")
    
    llm_service = ContractLLMService()
    migrated_count = 0
    
    for i, prospect in enumerate(prospects):
        try:
            # Parse existing NAICS
            parsed = llm_service.parse_existing_naics(prospect.naics)
            
            if parsed['code']:
                prospect.naics = parsed['code']
                prospect.naics_description = parsed['description']
                prospect.naics_source = 'original'
                migrated_count += 1
            
            # Commit every 100 records
            if (i + 1) % 100 == 0:
                db.session.commit()
                logger.info(f"Processed {i + 1} prospects...")
                
        except Exception as e:
            logger.error(f"Error migrating prospect {prospect.id}: {e}")
            continue
    
    # Final commit
    db.session.commit()
    logger.info(f"Migrated NAICS data for {migrated_count} prospects")
    return migrated_count


def migrate_value_text_from_extra():
    """
    Extract estimated_value_text from extra JSON fields.
    Different sources store this in different places.
    """
    logger.info("Starting value text migration from extra fields...")
    
    # Get prospects with no estimated_value_text but have extra data
    prospects = Prospect.query.filter(
        Prospect.estimated_value_text.is_(None),
        Prospect.extra.isnot(None)
    ).all()
    
    logger.info(f"Found {len(prospects)} prospects to check for value text")
    
    value_fields = [
        'estimated_value_text',
        'estimated_value',
        'dollar_range',
        'total_contract_range',
        'estimated_value_range',
        'contract_value',
        'value'
    ]
    
    migrated_count = 0
    
    for i, prospect in enumerate(prospects):
        try:
            if not prospect.extra:
                continue
                
            # Look for value text in various fields
            value_text = None
            for field in value_fields:
                if field in prospect.extra:
                    value_text = str(prospect.extra[field])
                    break
            
            # Also check nested financial section
            if not value_text and 'financial' in prospect.extra:
                financial = prospect.extra['financial']
                for field in value_fields:
                    if field in financial:
                        value_text = str(financial[field])
                        break
            
            if value_text:
                prospect.estimated_value_text = value_text[:100]  # Limit to 100 chars
                migrated_count += 1
            
            # Commit every 100 records
            if (i + 1) % 100 == 0:
                db.session.commit()
                logger.info(f"Processed {i + 1} prospects...")
                
        except Exception as e:
            logger.error(f"Error migrating prospect {prospect.id}: {e}")
            continue
    
    # Final commit
    db.session.commit()
    logger.info(f"Migrated value text for {migrated_count} prospects")
    return migrated_count


def migrate_contact_info_to_extra():
    """
    Ensure contact information is properly structured in extra JSON.
    This prepares data for LLM contact extraction.
    """
    logger.info("Starting contact info restructuring...")
    
    # Get all prospects with extra data
    prospects = Prospect.query.filter(
        Prospect.extra.isnot(None)
    ).all()
    
    logger.info(f"Found {len(prospects)} prospects to check for contact info")
    
    contact_fields = {
        'email': ['contact_email', 'poc_email', 'primary_contact_email', 'email'],
        'name': ['contact_name', 'poc_name', 'primary_contact_name', 'name'],
        'phone': ['contact_phone', 'poc_phone', 'primary_contact_phone', 'phone']
    }
    
    restructured_count = 0
    
    for i, prospect in enumerate(prospects):
        try:
            if not prospect.extra:
                continue
            
            # Check if contacts section exists
            if 'contacts' not in prospect.extra:
                prospect.extra['contacts'] = {}
            
            contacts = prospect.extra['contacts']
            updated = False
            
            # Extract contact info from various fields
            for contact_type, field_names in contact_fields.items():
                if f'original_contact_{contact_type}' not in contacts:
                    for field in field_names:
                        if field in prospect.extra and prospect.extra[field]:
                            contacts[f'original_contact_{contact_type}'] = prospect.extra[field]
                            updated = True
                            break
            
            if updated:
                restructured_count += 1
                # Force SQLAlchemy to detect the change
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(prospect, 'extra')
            
            # Commit every 100 records
            if (i + 1) % 100 == 0:
                db.session.commit()
                logger.info(f"Processed {i + 1} prospects...")
                
        except Exception as e:
            logger.error(f"Error restructuring prospect {prospect.id}: {e}")
            continue
    
    # Final commit
    db.session.commit()
    logger.info(f"Restructured contact info for {restructured_count} prospects")
    return restructured_count


def run_migration(run_llm_enhancement: bool = False):
    """
    Run all migration steps.
    
    Args:
        run_llm_enhancement: If True, also run LLM enhancement after migration
    """
    logger.info("Starting contract field migration...")
    
    # Run migration steps
    naics_count = migrate_existing_naics_data()
    value_count = migrate_value_text_from_extra()
    contact_count = migrate_contact_info_to_extra()
    
    logger.info(f"Migration complete:")
    logger.info(f"  - Migrated NAICS data: {naics_count} records")
    logger.info(f"  - Migrated value text: {value_count} records")
    logger.info(f"  - Restructured contacts: {contact_count} records")
    
    if run_llm_enhancement:
        logger.info("\nRunning LLM enhancement...")
        llm_service = ContractLLMService()
        
        # Run enhancement on a limited set first
        results = llm_service.enhance_all_prospects(limit=100)
        
        logger.info(f"LLM Enhancement results:")
        logger.info(f"  - Values enhanced: {results['values_enhanced']}")
        logger.info(f"  - Contacts enhanced: {results['contacts_enhanced']}")
        logger.info(f"  - NAICS enhanced: {results['naics_enhanced']}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate contract fields for existing prospects')
    parser.add_argument(
        '--with-llm',
        action='store_true',
        help='Also run LLM enhancement after migration (requires Ollama with qwen3:8b)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of records to process (for testing)'
    )
    
    args = parser.parse_args()
    
    app = create_app()
    with app.app_context():
        run_migration(run_llm_enhancement=args.with_llm)