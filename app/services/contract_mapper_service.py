"""
Contract Data Mapper Service
Handles mapping from various government contract sources to standardized schema
"""

import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import hashlib
import json

from app.database import db
from app.database.models import Prospect, DataSource
from app.services.contract_llm_service import ContractLLMService
from app.utils.logger import logger


class ContractMapperService:
    """
    Service for mapping contract data from various sources to standardized format.
    Supports immediate NAICS extraction from source data where available.
    """
    
    def __init__(self):
        self.llm_service = ContractLLMService()
        
    def generate_prospect_id(self, data: Dict) -> str:
        """Generate unique ID for prospect based on key fields"""
        # Create a unique hash based on title, agency, and source
        key_parts = [
            str(data.get('title', '')),
            str(data.get('agency', '')),
            str(data.get('source_file', '')),
            str(data.get('native_id', ''))
        ]
        key_string = '|'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def map_universal_fields(self, record: Dict, source_file: str, source_mapping: Dict) -> Dict:
        """
        Map source-specific fields to universal schema.
        Immediately extracts NAICS from source data where available.
        """
        # Extract core fields using source-specific mapping
        mapped_data = {
            'title': record.get(source_mapping.get('title_field')),
            'description': record.get(source_mapping.get('description_field')),
            'agency': record.get(source_mapping.get('agency_field')) or source_mapping.get('default_agency'),
            'estimated_value_text': record.get(source_mapping.get('value_field')),
            'source_file': source_file,
            'native_id': record.get(source_mapping.get('id_field', 'id'))
        }
        
        # Handle NAICS extraction if present in source
        naics_field = source_mapping.get('naics_field')
        if naics_field and record.get(naics_field):
            parsed_naics = self.llm_service.parse_existing_naics(record.get(naics_field))
            mapped_data['naics'] = parsed_naics['code']
            mapped_data['naics_description'] = parsed_naics['description']
            mapped_data['naics_source'] = 'original'
        else:
            mapped_data['naics'] = None
            mapped_data['naics_description'] = None
            mapped_data['naics_source'] = None
        
        # Map other standard fields
        mapped_data.update({
            'release_date': self._parse_date(record.get(source_mapping.get('release_date_field'))),
            'award_date': self._parse_date(record.get(source_mapping.get('award_date_field'))),
            'place_city': record.get(source_mapping.get('place_city_field')),
            'place_state': record.get(source_mapping.get('place_state_field')),
            'place_country': record.get(source_mapping.get('place_country_field', 'United States')),
            'contract_type': record.get(source_mapping.get('contract_type_field')),
            'set_aside': record.get(source_mapping.get('set_aside_field')),
        })
        
        # Generate ID
        mapped_data['id'] = self.generate_prospect_id(mapped_data)
        
        # Store all other fields in extra
        extra_fields = {}
        for key, value in record.items():
            if key not in source_mapping.values() and value is not None:
                extra_fields[key] = value
        
        # Add source-specific extras
        if 'extras' in source_mapping:
            for extra_key, field_name in source_mapping['extras'].items():
                if record.get(field_name) is not None:
                    extra_fields[extra_key] = record.get(field_name)
        
        # Structure extras similar to contract mapping analysis
        mapped_data['extra'] = self._structure_extras(extra_fields, record, source_mapping)
        
        return mapped_data
    
    def _structure_extras(self, extra_fields: Dict, record: Dict, source_mapping: Dict) -> Dict:
        """Structure extra fields into categorized JSON format"""
        structured = {
            'source_file': source_mapping.get('source_file'),
            'financial': {},
            'location': {},
            'contacts': {},
            'timeline': {},
            'procurement': {},
            'classification': {},
            'requirements': {},
            'status': {},
            'source_specific': extra_fields
        }
        
        # Map contact information
        if source_mapping.get('contact_email_field'):
            structured['contacts']['original_contact_email'] = record.get(source_mapping['contact_email_field'])
        if source_mapping.get('contact_name_field'):
            structured['contacts']['original_contact_name'] = record.get(source_mapping['contact_name_field'])
        if source_mapping.get('contact_phone_field'):
            structured['contacts']['original_contact_phone'] = record.get(source_mapping['contact_phone_field'])
            
        # Map timeline information
        if source_mapping.get('solicitation_date_field'):
            structured['timeline']['target_solicitation_date'] = record.get(source_mapping['solicitation_date_field'])
        if source_mapping.get('performance_start_field'):
            structured['timeline']['performance_start'] = record.get(source_mapping['performance_start_field'])
        if source_mapping.get('performance_end_field'):
            structured['timeline']['performance_end'] = record.get(source_mapping['performance_end_field'])
            
        # Map procurement information
        if source_mapping.get('incumbent_field'):
            structured['procurement']['incumbent_contractor'] = record.get(source_mapping['incumbent_field'])
        if source_mapping.get('vehicle_field'):
            structured['procurement']['contract_vehicle'] = record.get(source_mapping['vehicle_field'])
        if source_mapping.get('competition_field'):
            structured['procurement']['competition_type'] = record.get(source_mapping['competition_field'])
            
        # Store original NAICS in classification
        if source_mapping.get('naics_field') and record.get(source_mapping['naics_field']):
            structured['classification']['original_naics'] = record.get(source_mapping['naics_field'])
            
        return structured
    
    def _parse_date(self, date_value: Any) -> Optional[datetime]:
        """Parse various date formats to datetime"""
        if not date_value:
            return None
            
        if isinstance(date_value, datetime):
            return date_value.date()
            
        # Try common date formats
        date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%m/%d/%y',
            '%Y/%m/%d',
            '%d-%m-%Y',
            '%d/%m/%Y'
        ]
        
        date_str = str(date_value).strip()
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
                
        logger.warning(f"Could not parse date: {date_value}")
        return None
    
    # Source-specific mapping configurations
    def get_dot_mapping(self) -> Dict:
        """DOT.CSV mapping configuration"""
        return {
            'source_file': 'dot.csv',
            'title_field': 'Project Title',
            'description_field': 'Description',
            'agency_field': 'Agency',
            'value_field': 'Estimated Value',
            'naics_field': 'NAICS',
            'release_date_field': 'Release Date',
            'award_date_field': 'Anticipated Award Date',
            'place_state_field': 'Place of Performance',
            'contract_type_field': 'Competition Type',
            'set_aside_field': 'Set Aside',
            'contact_email_field': 'Contact Email',
            'contact_name_field': 'Contact Name',
            'contact_phone_field': 'Contact Phone',
            'incumbent_field': 'Incumbent Contractor',
            'vehicle_field': 'Contract Vehicle',
            'competition_field': 'Competition Type',
            'extras': {
                'procurement_office': 'Procurement Office',
                'procurement_category': 'Procurement Category',
                'rfp_quarter': 'RFP Quarter',
                'bil_opportunity': 'Bipartisan Infrastructure Law (BIL) Opportunity',
                'fiscal_year': 'FY'
            }
        }
    
    def get_dhs_mapping(self) -> Dict:
        """DHS.CSV mapping configuration"""
        return {
            'source_file': 'dhs.csv',
            'title_field': 'Title',
            'description_field': 'Description',
            'agency_field': 'Component',
            'default_agency': 'Department of Homeland Security',
            'value_field': 'Dollar Range',
            'naics_field': 'NAICS',
            'place_state_field': 'Place of Performance State',
            'place_city_field': 'Place of Performance City',
            'contact_email_field': 'Primary Contact Email',
            'extras': {
                'apfs_number': 'APFS Number',
                'component': 'Component',
                'contact_first_name': 'Primary Contact First Name',
                'contact_last_name': 'Primary Contact Last Name',
                'contact_phone': 'Primary Contact Phone'
            }
        }
    
    def get_hhs_mapping(self) -> Dict:
        """HHS.CSV mapping configuration"""
        return {
            'source_file': 'hhs.csv',
            'title_field': 'Title',
            'description_field': 'Description',
            'default_agency': 'Department of Health and Human Services',
            'value_field': 'Total Contract Range',
            'naics_field': 'Primary NAICS',
            'contact_email_field': 'Program Office POC Email',
            'extras': {
                'operating_division': 'Operating Division',
                'poc_first_name': 'Program Office POC First Name',
                'poc_last_name': 'Program Office POC Last Name'
            }
        }
    
    def get_doc_mapping(self) -> Dict:
        """DOC.XLSX mapping configuration"""
        return {
            'source_file': 'doc.xlsx',
            'title_field': 'Title',
            'description_field': 'Description',
            'default_agency': 'Department of Commerce',
            'value_field': 'Estimated Value Range',
            'naics_field': 'Naics Code',  # Format: "334516 | Description"
            'place_state_field': 'Place Of Performance State',
            'place_city_field': 'Place Of Performance City',
            'contact_email_field': 'Point Of Contact Email',
            'contact_name_field': 'Point Of Contact Name',
            'extras': {
                'forecast_id': 'Forecast ID',
                'organization': 'Organization',
                'office': 'Office'
            }
        }
    
    def get_ssa_mapping(self) -> Dict:
        """SSA.XLSX mapping configuration"""
        return {
            'source_file': 'ssa.xlsx',
            'title_field': 'DESCRIPTION',
            'description_field': 'DESCRIPTION',
            'default_agency': 'Social Security Administration',
            'value_field': 'EST COST PER FY',
            'naics_field': None,  # No NAICS in SSA data
            'award_date_field': 'PLANNED AWARD DATE',
            'extras': {
                'site_type': 'SITE Type',
                'app_number': 'APP #',
                'requirement_type': 'REQUIREMENT TYPE'
            }
        }
    
    def get_dos_mapping(self) -> Dict:
        """DOS.XLSX mapping configuration"""
        return {
            'source_file': 'dos.xlsx',
            'title_field': 'Requirement Title',
            'description_field': 'Requirement Description',
            'agency_field': 'Program Funding Agency',
            'value_field': 'Estimated Value',
            'naics_field': None,  # No NAICS in DOS data
            'place_state_field': 'Place of Performance State',
            'place_city_field': 'Place of Performance City',
            'extras': {
                'office_symbol': 'Office Symbol',
                'fiscal_year': 'Fiscal Year'
            }
        }
    
    def get_doj_mapping(self) -> Dict:
        """DOJ.XLSX mapping configuration"""
        return {
            'source_file': 'doj.xlsx',
            'title_field': 'Contract Name',
            'description_field': 'Description of Requirement',
            'agency_field': 'Bureau',
            'default_agency': 'Department of Justice',
            'value_field': 'Estimated Total Contract Value (Range)',
            'naics_field': 'NAICS Code',
            'extras': {
                'bureau': 'Bureau'
            }
        }
    
    def get_treasury_mapping(self) -> Dict:
        """TREASURY.XLSX mapping configuration"""
        return {
            'source_file': 'treasury.xlsx',
            'title_field': 'ShopCart/req',  # May need custom handling
            'description_field': 'Description',
            'agency_field': 'Bureau',
            'default_agency': 'Department of Treasury',
            'value_field': 'Estimated Total Contract Value',
            'naics_field': 'NAICS',
            'extras': {
                'bureau': 'Bureau',
                'contact_name': 'Contact Name',
                'contact_email': 'Contact Email'
            }
        }
    
    def get_acqgateway_mapping(self) -> Dict:
        """ACQGATEWAY.CSV mapping configuration"""
        return {
            'source_file': 'acqgateway.csv',
            'title_field': 'Title',
            'description_field': 'Description',  # May need to combine with 'Body'
            'agency_field': 'Agency',
            'value_field': 'Estimated Contract Value',
            'naics_field': 'NAICS Code',
            'extras': {
                'body': 'Body',  # Additional description content
                'posted_date': 'Posted Date'
            }
        }
    
    def get_mapping_for_source(self, source_file: str) -> Optional[Dict]:
        """Get mapping configuration for a given source file"""
        source_lower = source_file.lower()
        
        mapping_functions = {
            'dot.csv': self.get_dot_mapping,
            'dhs.csv': self.get_dhs_mapping,
            'hhs.csv': self.get_hhs_mapping,
            'doc.xlsx': self.get_doc_mapping,
            'ssa.xlsx': self.get_ssa_mapping,
            'dos.xlsx': self.get_dos_mapping,
            'doj.xlsx': self.get_doj_mapping,
            'treasury.xlsx': self.get_treasury_mapping,
            'acqgateway.csv': self.get_acqgateway_mapping
        }
        
        for pattern, func in mapping_functions.items():
            if pattern in source_lower:
                return func()
                
        logger.warning(f"No mapping found for source: {source_file}")
        return None
    
    def map_records_from_source(self, records: List[Dict], source_file: str) -> List[Dict]:
        """Map a list of records from a specific source"""
        mapping = self.get_mapping_for_source(source_file)
        if not mapping:
            return []
            
        mapped_records = []
        for record in records:
            try:
                mapped = self.map_universal_fields(record, source_file, mapping)
                mapped_records.append(mapped)
            except Exception as e:
                logger.error(f"Error mapping record from {source_file}: {e}")
                continue
                
        return mapped_records
    
    def save_mapped_prospects(self, mapped_records: List[Dict], data_source_id: Optional[int] = None) -> int:
        """
        Save mapped records to database as Prospect objects.
        Returns count of successfully saved records.
        """
        saved_count = 0
        
        for record in mapped_records:
            try:
                # Check if prospect already exists
                existing = Prospect.query.filter_by(id=record['id']).first()
                
                if existing:
                    # Update existing record
                    for key, value in record.items():
                        if hasattr(existing, key) and key != 'id':
                            setattr(existing, key, value)
                    existing.loaded_at = datetime.now(timezone.utc)
                else:
                    # Create new prospect
                    prospect = Prospect(**record)
                    if data_source_id:
                        prospect.source_id = data_source_id
                    db.session.add(prospect)
                
                saved_count += 1
                
                # Commit in batches
                if saved_count % 100 == 0:
                    db.session.commit()
                    logger.info(f"Saved {saved_count} prospects...")
                    
            except Exception as e:
                logger.error(f"Error saving prospect: {e}")
                db.session.rollback()
                continue
        
        # Final commit
        try:
            db.session.commit()
            logger.info(f"Successfully saved {saved_count} prospects")
        except Exception as e:
            logger.error(f"Error in final commit: {e}")
            db.session.rollback()
            
        return saved_count