import os
import sys
import datetime
import pandas as pd
from pathlib import Path

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import get_session, close_session
from src.database.models import Proposal, DataSource
from src.utils.logger import logger

# Set up logging using the centralized utility
logger = logger.bind(name="process_ssa_excel")

def parse_date(date_str):
    """Parse a date string into a datetime object"""
    if date_str is None:
        return None
    
    # Convert to string if it's a numeric type
    if isinstance(date_str, (int, float)):
        date_str = str(date_str)
    
    # If it's empty after conversion, return None
    if not date_str or str(date_str).strip() == "":
        return None
    
    # Try different date formats
    date_formats = [
        "%m/%d/%Y",
        "%m/%d/%y",
        "%Y-%m-%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%m-%d-%Y",
        "%m-%d-%y"
    ]
    
    # Clean up the date string
    date_str = str(date_str).strip()
    
    # Try each format
    for date_format in date_formats:
        try:
            return datetime.datetime.strptime(date_str, date_format)
        except ValueError:
            continue
    
    # If we get here, none of the formats worked
    logger.warning(f"Could not parse date: {date_str}")
    return None

def parse_value(value_str):
    """Parse a value string into a float"""
    if value_str is None:
        return None
    
    # If it's already a numeric type, return it
    if isinstance(value_str, (int, float)):
        return float(value_str)
    
    # Convert to string if needed
    value_str = str(value_str)
    
    # If it's empty after conversion, return None
    if not value_str or value_str.strip() == "":
        return None
    
    # Remove any non-numeric characters except for decimal points
    import re
    value_str = re.sub(r'[^\d.]', '', value_str)
    
    # Try to convert to float
    try:
        return float(value_str)
    except ValueError:
        logger.warning(f"Could not parse value: {value_str}")
        return None

def process_excel_file(excel_file_path):
    """Process the SSA Excel file and insert data into the database"""
    logger.info(f"Processing Excel file: {excel_file_path}")
    
    # Check if the file exists
    if not os.path.exists(excel_file_path):
        logger.error(f"File not found: {excel_file_path}")
        return False
    
    # Get a database session
    session = get_session()
    
    try:
        # Get or create the SSA Contract Forecast data source
        data_source = session.query(DataSource).filter_by(name="SSA Contract Forecast").first()
        if not data_source:
            logger.info("Creating SSA Contract Forecast data source")
            data_source = DataSource(
                name="SSA Contract Forecast",
                url="https://www.ssa.gov/osdbu/contract-forecast-intro.html",
                description="Social Security Administration Contract Forecast"
            )
            session.add(data_source)
            session.commit()
        
        # Load the workbook using pandas
        logger.info("Loading workbook with pandas")
        df = pd.read_excel(excel_file_path)
        
        # Find the header row
        header_row = None
        header_keywords = ['Site Type', 'App #', 'Requirement Type', 'Description', 'Est. Cost']
        
        for row_idx in range(1, min(20, len(df))):
            row_values = df.iloc[row_idx].tolist()
            row_text = ' '.join(str(val) for val in row_values).lower()
            
            # Check if this row contains multiple header keywords
            matches = sum(1 for keyword in header_keywords if keyword.lower() in row_text)
            if matches >= 3:
                header_row = row_idx
                logger.info(f"Found header row at index {header_row}")
                break
        
        if not header_row:
            logger.error("Could not find header row")
            return False
        
        # Get the header values
        header_values = df.iloc[header_row].tolist()
        logger.info(f"Header values: {header_values}")
        
        # Process the data rows
        proposals_added = 0
        
        for row_idx in range(header_row + 1, len(df)):
            try:
                # Get the row values
                row_values = df.iloc[row_idx].tolist()
                
                # Skip empty rows
                if not any(row_values):
                    continue
                
                # Extract values
                site_type = row_values[0] if len(row_values) > 0 else None
                app_num = row_values[1] if len(row_values) > 1 else None
                requirement_type = row_values[2] if len(row_values) > 2 else None
                description = row_values[3] if len(row_values) > 3 else None
                est_cost = row_values[4] if len(row_values) > 4 else None
                award_date_str = row_values[5] if len(row_values) > 5 else None
                existing_award = row_values[6] if len(row_values) > 6 else None
                contract_type = row_values[7] if len(row_values) > 7 else None
                incumbent = row_values[8] if len(row_values) > 8 else None
                naics_code = row_values[9] if len(row_values) > 9 else None
                naics_desc = row_values[10] if len(row_values) > 10 else None
                competition_type = row_values[11] if len(row_values) > 11 else None
                obligated_amt = row_values[12] if len(row_values) > 12 else None
                place_of_performance = row_values[13] if len(row_values) > 13 else None
                completion_date = row_values[14] if len(row_values) > 14 else None
                
                # Skip rows without a description
                if not description:
                    continue
                
                # Parse dates
                release_date = None
                response_date = None
                award_date = parse_date(award_date_str)
                
                # Parse estimated value
                estimated_value = parse_value(est_cost)
                
                # Create a unique external ID
                external_id = f"SSA_{app_num}" if app_num else None
                
                # Check if this proposal already exists
                existing_proposal = None
                if external_id:
                    existing_proposal = session.query(Proposal).filter(
                        Proposal.external_id == external_id,
                        Proposal.source_id == data_source.id,
                        Proposal.is_latest == True
                    ).first()
                
                if existing_proposal:
                    # Update existing proposal
                    logger.info(f"Updating existing proposal: {external_id}")
                    existing_proposal.title = description
                    existing_proposal.office = site_type
                    existing_proposal.description = description
                    existing_proposal.naics_code = naics_code
                    existing_proposal.estimated_value = estimated_value
                    existing_proposal.award_date = award_date
                    existing_proposal.contract_type = contract_type
                    existing_proposal.competition_type = competition_type
                    existing_proposal.place_of_performance = place_of_performance
                    existing_proposal.incumbent = incumbent
                    existing_proposal.last_updated = datetime.datetime.utcnow()
                    session.add(existing_proposal)
                else:
                    # Create a new proposal
                    logger.info(f"Adding new proposal: {description}")
                    proposal = Proposal(
                        source_id=data_source.id,
                        external_id=external_id,
                        title=description,
                        agency="Social Security Administration",
                        office=site_type,
                        description=description,
                        naics_code=naics_code,
                        estimated_value=estimated_value,
                        release_date=release_date,
                        response_date=response_date,
                        contact_info=None,
                        url="https://www.ssa.gov/osdbu/contract-forecast-intro.html",
                        status=None,
                        contract_type=contract_type,
                        set_aside=None,
                        competition_type=competition_type,
                        solicitation_number=app_num,
                        award_date=award_date,
                        place_of_performance=place_of_performance,
                        incumbent=incumbent,
                        is_latest=True
                    )
                    session.add(proposal)
                
                proposals_added += 1
                
                # Commit every 100 proposals to avoid large transactions
                if proposals_added % 100 == 0:
                    session.commit()
                    logger.info(f"Committed {proposals_added} proposals so far")
            
            except Exception as e:
                logger.error(f"Error processing row {row_idx}: {e}")
                continue
        
        # Final commit
        session.commit()
        
        # Update the data source last_scraped timestamp
        data_source.last_scraped = datetime.datetime.utcnow()
        session.add(data_source)
        session.commit()
        
        logger.info(f"Successfully processed {proposals_added} proposals")
        return True
    
    except Exception as e:
        logger.error(f"Error processing Excel file: {e}")
        session.rollback()
        return False
    
    finally:
        close_session(session)

if __name__ == "__main__":
    # Get the Excel file path from command line arguments or use default
    if len(sys.argv) > 1:
        excel_file_path = sys.argv[1]
    else:
        # Use the default path
        excel_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'downloads', 'SBF_SSASy_Report_01072025 (1).xlsm'
        )
    
    # Process the Excel file
    success = process_excel_file(excel_file_path)
    
    if success:
        logger.info("Excel file processed successfully")
    else:
        logger.error("Failed to process Excel file")
        sys.exit(1) 