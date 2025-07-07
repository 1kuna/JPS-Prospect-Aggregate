#!/usr/bin/env python3
"""
Export Go/No-Go decisions with prospect data for LLM training.

This script exports prospect data along with user decisions in a format
suitable for fine-tuning an LLM to understand company preferences.
"""

import os
import sys
import json
import argparse
import datetime
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from app.database.models import db, Prospect, GoNoGoDecision
from app.database.user_models import User
from app import create_app
from app.utils.logger import logger

def export_decisions_to_jsonl(output_file: str, include_reasons_only: bool = False):
    """
    Export decisions to JSONL format for LLM training.
    
    Args:
        output_file: Path to output JSONL file
        include_reasons_only: If True, only export decisions with reasons
    """
    app = create_app()
    
    with app.app_context():
        logger.info("Starting export of decisions for LLM training")
        
        # Query for decisions with prospect data (users are in separate database)
        query = db.session.query(GoNoGoDecision, Prospect).join(
            Prospect, GoNoGoDecision.prospect_id == Prospect.id
        ).order_by(GoNoGoDecision.created_at.desc())
        
        if include_reasons_only:
            query = query.filter(GoNoGoDecision.reason.isnot(None))
        
        decisions = query.all()
        
        logger.info(f"Found {len(decisions)} decisions to export")
        
        # Get all unique user IDs and fetch user data from separate database
        user_ids = list(set([decision.user_id for decision, prospect in decisions]))
        users = db.session.query(User).filter(User.id.in_(user_ids)).all()
        users_dict = {user.id: user for user in users}
        
        exported_count = 0
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for decision, prospect in decisions:
                user = users_dict.get(decision.user_id)
                # Create training example
                training_example = {
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an AI assistant helping evaluate government contracting opportunities. Based on the prospect details, determine if this is a 'go' or 'no-go' opportunity for the company."
                        },
                        {
                            "role": "user",
                            "content": create_prospect_prompt(prospect)
                        },
                        {
                            "role": "assistant",
                            "content": create_decision_response(decision)
                        }
                    ],
                    "metadata": {
                        "prospect_id": prospect.id,
                        "decision_id": decision.id,
                        "user_email": user.email,
                        "user_first_name": user.first_name,
                        "decision_date": decision.created_at.isoformat(),
                        "prospect_agency": prospect.agency,
                        "prospect_naics": prospect.naics,
                        "estimated_value": str(prospect.estimated_value_single) if prospect.estimated_value_single else None
                    }
                }
                
                f.write(json.dumps(training_example, ensure_ascii=False) + '\n')
                exported_count += 1
        
        logger.info(f"Successfully exported {exported_count} training examples to {output_file}")
        return exported_count

def create_prospect_prompt(prospect: Prospect) -> str:
    """Create a prompt describing the prospect for the LLM."""
    prompt_parts = []
    
    # Title and description
    if prospect.title:
        prompt_parts.append(f"Title: {prospect.title}")
    
    if prospect.ai_enhanced_title and prospect.ai_enhanced_title != prospect.title:
        prompt_parts.append(f"Enhanced Title: {prospect.ai_enhanced_title}")
    
    if prospect.description:
        # Truncate very long descriptions
        description = prospect.description
        if len(description) > 1000:
            description = description[:1000] + "..."
        prompt_parts.append(f"Description: {description}")
    
    # Agency and classification
    if prospect.agency:
        prompt_parts.append(f"Agency: {prospect.agency}")
    
    if prospect.naics:
        naics_info = f"NAICS Code: {prospect.naics}"
        if prospect.naics_description:
            naics_info += f" ({prospect.naics_description})"
        prompt_parts.append(naics_info)
    
    # Value information
    value_info = []
    if prospect.estimated_value_single:
        value_info.append(f"Estimated Value: ${prospect.estimated_value_single:,.2f}")
    elif prospect.estimated_value_min and prospect.estimated_value_max:
        value_info.append(f"Estimated Value Range: ${prospect.estimated_value_min:,.2f} - ${prospect.estimated_value_max:,.2f}")
    elif prospect.estimated_value_text:
        value_info.append(f"Estimated Value: {prospect.estimated_value_text}")
    
    if value_info:
        prompt_parts.extend(value_info)
    
    # Dates
    if prospect.release_date:
        prompt_parts.append(f"Release Date: {prospect.release_date.strftime('%Y-%m-%d')}")
    
    if prospect.award_date:
        prompt_parts.append(f"Award Date: {prospect.award_date.strftime('%Y-%m-%d')}")
    
    # Location
    location_parts = []
    if prospect.place_city:
        location_parts.append(prospect.place_city)
    if prospect.place_state:
        location_parts.append(prospect.place_state)
    if prospect.place_country and prospect.place_country.upper() != 'USA':
        location_parts.append(prospect.place_country)
    
    if location_parts:
        prompt_parts.append(f"Location: {', '.join(location_parts)}")
    
    # Contract details
    if prospect.contract_type:
        prompt_parts.append(f"Contract Type: {prospect.contract_type}")
    
    if prospect.set_aside:
        prompt_parts.append(f"Set Aside: {prospect.set_aside}")
    
    # Contact information
    if prospect.primary_contact_email:
        prompt_parts.append(f"Primary Contact: {prospect.primary_contact_email}")
        if prospect.primary_contact_name:
            prompt_parts[-1] += f" ({prospect.primary_contact_name})"
    
    return "\n".join(prompt_parts)

def create_decision_response(decision: GoNoGoDecision) -> str:
    """Create the assistant's response based on the decision."""
    response = f"Decision: {decision.decision.upper()}"
    
    if decision.reason:
        response += f"\n\nReasoning: {decision.reason}"
    
    return response

def export_decisions_to_csv(output_file: str):
    """Export decisions to CSV format for analysis."""
    import csv
    
    app = create_app()
    
    with app.app_context():
        logger.info("Starting CSV export of decisions")
        
        # Query for decisions with prospect data (users are in separate database)
        decisions = db.session.query(GoNoGoDecision, Prospect).join(
            Prospect, GoNoGoDecision.prospect_id == Prospect.id
        ).order_by(GoNoGoDecision.created_at.desc()).all()
        
        # Get all unique user IDs and fetch user data from separate database
        user_ids = list(set([decision.user_id for decision, prospect in decisions]))
        users = db.session.query(User).filter(User.id.in_(user_ids)).all()
        users_dict = {user.id: user for user in users}
        
        logger.info(f"Found {len(decisions)} decisions to export")
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'decision_id', 'prospect_id', 'user_email', 'user_first_name',
                'decision', 'reason', 'decision_date',
                'prospect_title', 'prospect_agency', 'prospect_naics', 'prospect_naics_description',
                'estimated_value_single', 'estimated_value_min', 'estimated_value_max',
                'release_date', 'award_date', 'place_city', 'place_state',
                'contract_type', 'set_aside'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for decision, prospect in decisions:
                user = users_dict.get(decision.user_id)
                writer.writerow({
                    'decision_id': decision.id,
                    'prospect_id': prospect.id,
                    'user_email': user.email if user else 'Unknown',
                    'user_first_name': user.first_name if user else 'Unknown',
                    'decision': decision.decision,
                    'reason': decision.reason,
                    'decision_date': decision.created_at.isoformat(),
                    'prospect_title': prospect.title,
                    'prospect_agency': prospect.agency,
                    'prospect_naics': prospect.naics,
                    'prospect_naics_description': prospect.naics_description,
                    'estimated_value_single': prospect.estimated_value_single,
                    'estimated_value_min': prospect.estimated_value_min,
                    'estimated_value_max': prospect.estimated_value_max,
                    'release_date': prospect.release_date.isoformat() if prospect.release_date else None,
                    'award_date': prospect.award_date.isoformat() if prospect.award_date else None,
                    'place_city': prospect.place_city,
                    'place_state': prospect.place_state,
                    'contract_type': prospect.contract_type,
                    'set_aside': prospect.set_aside
                })
        
        logger.info(f"Successfully exported {len(decisions)} decisions to {output_file}")
        return len(decisions)

def main():
    parser = argparse.ArgumentParser(description='Export Go/No-Go decisions for LLM training')
    parser.add_argument('--format', choices=['jsonl', 'csv', 'both'], default='jsonl',
                        help='Export format (default: jsonl)')
    parser.add_argument('--output-dir', default='./data/llm_training',
                        help='Output directory (default: ./data/llm_training)')
    parser.add_argument('--reasons-only', action='store_true',
                        help='Only export decisions with reasons')
    parser.add_argument('--filename-prefix', default='go_no_go_decisions',
                        help='Filename prefix (default: go_no_go_decisions)')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp for filename
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    reasons_suffix = "_with_reasons" if args.reasons_only else ""
    
    exported_files = []
    
    if args.format in ['jsonl', 'both']:
        jsonl_file = output_dir / f"{args.filename_prefix}{reasons_suffix}_{timestamp}.jsonl"
        count = export_decisions_to_jsonl(str(jsonl_file), args.reasons_only)
        exported_files.append((str(jsonl_file), count, 'JSONL'))
    
    if args.format in ['csv', 'both']:
        csv_file = output_dir / f"{args.filename_prefix}_{timestamp}.csv"
        count = export_decisions_to_csv(str(csv_file))
        exported_files.append((str(csv_file), count, 'CSV'))
    
    logger.info("\nExport Summary:")
    logger.info("=" * 50)
    for file_path, count, format_type in exported_files:
        logger.info(f"{format_type}: {count} records exported to {file_path}")
    
    if exported_files:
        logger.success(f"\nFiles ready for LLM training!")
        if args.format in ['jsonl', 'both']:
            logger.info("\nFor LLM fine-tuning, use the JSONL file with frameworks like:")
            logger.info("- OpenAI fine-tuning API")
            logger.info("- Hugging Face transformers")
            logger.info("- Local fine-tuning with qwen3 or similar models")

if __name__ == '__main__':
    main()