import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from typing import Optional, List, Dict, Any # Added Dict, Any
import datetime 
import os 
import hashlib # For id_hash pre-calculation

from app.core.scrapers.treasury_scraper import TreasuryScraper
from app.core.scrapers.configs.treasury_config import TreasuryConfig, DataProcessingRules
from app.exceptions import ScraperError
from app.config import active_config
from app.models import Prospect
from app.utils.scraper_utils import generate_id_hash # For id_hash pre-calculation
from sqlalchemy import select


# --- Helper for ID Hash ---
def precalculate_treasury_id_hash(record: Dict, config: TreasuryConfig) -> str:
    """Pre-calculates id_hash for an expected record based on Treasury config."""
    # fields_for_id_hash from TreasuryConfig:
    # ['native_id_final', 'naics_intermediate', 'title_intermediate', 
    #  'description_final', 'agency_intermediate', 'place_city', 
    #  'place_state', 'row_index']
    # The `record` dict passed here has final model field names.
    # We need to map these back to the intermediate names used for hashing if they differ.
    
    data_for_hash = {
        'native_id_final': str(record.get('native_id', '')),
        'naics_intermediate': str(record.get('naics', '')), # Assuming 'naics' in record maps to 'naics_intermediate'
        'title_intermediate': str(record.get('title', '')), # Assuming 'title' in record maps to 'title_intermediate'
        'description_final': str(record.get('description', '')), # Should be None for Treasury
        'agency_intermediate': str(record.get('agency', '')), # Assuming 'agency' in record maps to 'agency_intermediate'
        'place_city': str(record.get('place_city', '')), # Direct match
        'place_state': str(record.get('place_state', '')), # Direct match
        'row_index': record.get('row_index') # Direct match, ensure it's passed in record
    }
    # Ensure all fields expected by fields_for_id_hash are present in data_for_hash
    # This mapping needs to be robust based on how config_params.fields_for_id_hash is structured
    # and what names are present in the DataFrame *before* db_column_rename_map.
    # The TreasuryConfig.fields_for_id_hash uses a mix of intermediate and final-looking names.
    # For this helper, we'll assume the keys in `record` can be directly used if they match the conceptual field.
    
    temp_df_data = {key: data_for_hash.get(key) for key in config.data_processing_rules.fields_for_id_hash}
    temp_df = pd.DataFrame([temp_df_data])
    id_hash_series = generate_id_hash(temp_df, config.data_processing_rules.fields_for_id_hash, prefix=config.source_name)
    return id_hash_series[0]


# --- Expected Data ---
EXPECTED_TREASURY_PROSPECTS_BASE = [
    {
        "native_id": "TREAS-001", "agency": "Fiscal Service", "title": "R408", # PSC as title
        "description": None, "place_city": "Washington", "place_state": "DC", "place_country": "USA",
        "contract_type": "FFP", "naics": "541511", "estimated_value": 100000.0,
        "est_value_unit": "K USD", "set_aside": "Small Business",
        "award_date": datetime.date(2023, 10, 1), "award_fiscal_year": 2024, # 2024 Q1
        "release_date": datetime.date(2023, 10, 1), "row_index": 0,
        "extra_data": {'type_of_requirement_extra': 'Support Services'}
    },
    {
        "native_id": "TREAS-002", "agency": "IRS", "title": "D302",
        "description": None, "place_city": "Remote", "place_state": None, "place_country": "USA",
        "contract_type": "T&M", "naics": "541512", "estimated_value": 1000000.0,
        "est_value_unit": "M USD", "set_aside": "None", # "None" string from sample
        "award_date": datetime.date(2024, 1, 1), "award_fiscal_year": 2024, # 2024 Q2
        "release_date": datetime.date(2024, 1, 15), "row_index": 1,
        "extra_data": {'type_of_requirement_extra': 'IT System'}
    },
    { # Third record from HTML sample
        "native_id": "TREAS-003", "agency": "OCIO", "title": "F123",
        "description": None, "place_city": "New Carrollton", "place_state": "MD", "place_country": "USA",
        "contract_type": "LH", "naics": "541611", "estimated_value": 500000.0,
        "est_value_unit": None, "set_aside": "WOSB", # Assuming direct mapping
        "award_date": datetime.date(2024, 4, 1), "award_fiscal_year": 2024, # 2024 Q3
        "release_date": datetime.date(2024, 4, 1), "row_index": 2,
        "extra_data": {'type_of_requirement_extra': 'Consulting'}
    }
]


# --- Fixtures ---
@pytest.fixture
def treasury_full_test_config():
    conf = TreasuryConfig(source_name="Treasury Integration Test") # Use specific name for test DB isolation
    # Ensure the data_processing_rules from the actual config are used
    conf.data_processing_rules = TreasuryConfig().data_processing_rules
    # Map 'Type of Requirement' to an extra field for testing extra_data
    conf.data_processing_rules.raw_column_rename_map['Type of Requirement'] = 'type_of_requirement_extra'
    return conf

@pytest.fixture
def treasury_unit_test_config():
    return TreasuryConfig(source_name="Treasury Unit Test", data_processing_rules=DataProcessingRules(fields_for_id_hash=['native_id_final'])) # Simplified

@pytest.fixture
def mock_treasury_dependencies(mocker): # For unit tests
    mocker.patch.object(TreasuryScraper, 'navigate_to_url', return_value=None)
    mocker.patch.object(TreasuryScraper, 'wait_for_load_state', return_value=None)
    mocker.patch.object(TreasuryScraper, 'wait_for_selector', return_value=None)
    mocker.patch.object(TreasuryScraper, 'click_element', return_value=None) 
    mocker.patch.object(TreasuryScraper, '_handle_download_event', return_value=None)
    mocker.patch.object(TreasuryScraper, 'setup_browser', return_value=None)
    mocker.patch.object(TreasuryScraper, 'cleanup_browser', return_value=None)

@pytest.fixture
def treasury_scraper_unit_instance(treasury_unit_test_config, mock_treasury_dependencies, mocker):
    mocker.patch.object(TreasuryScraper, 'read_file_to_dataframe', return_value=pd.DataFrame()) # Empty for some unit tests
    mocker.patch.object(TreasuryScraper, 'prepare_and_load_data', return_value=0) # Mock for unit tests
    scraper = TreasuryScraper(config=treasury_unit_test_config, debug_mode=True)
    scraper.page = MagicMock(); scraper.page.expect_download.return_value.__enter__.return_value.value = MagicMock(path=lambda: "/tmp/fake.xls")
    scraper.logger = MagicMock(); scraper._last_download_path = "/tmp/fake.xls" 
    return scraper

@pytest.fixture
def treasury_scraper_for_integration(treasury_full_test_config, db_session, mocker):
    mocker.patch.object(TreasuryScraper, 'setup_browser', return_value=None)
    mocker.patch.object(TreasuryScraper, 'cleanup_browser', return_value=None)
    mocker.patch.object(TreasuryScraper, 'navigate_to_url', return_value=None)
    mocker.patch.object(TreasuryScraper, 'click_element', return_value=None)
    mocker.patch.object(TreasuryScraper, '_handle_download_event', return_value=None)
    mocker.patch.object(TreasuryScraper, 'wait_for_selector', return_value=None)
    mocker.patch.object(TreasuryScraper, 'wait_for_load_state', return_value=None)
    scraper = TreasuryScraper(config=treasury_full_test_config, debug_mode=True)
    scraper.logger = MagicMock()
    return scraper

# --- Basic Tests ---
def test_treasury_scraper_instantiation(treasury_unit_test_config):
    try: scraper = TreasuryScraper(config=treasury_unit_test_config); assert scraper.config == treasury_unit_test_config
    except Exception as e: pytest.fail(f"TreasuryScraper instantiation failed: {e}")

# --- Integration Test for _process_method with DB Validation ---
def test_treasury_process_method_integration(treasury_scraper_for_integration, treasury_full_test_config, db_session):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    golden_file_path = os.path.join(current_dir, "..", "..", "fixtures", "golden_files", "treasury_scraper", "treasury_sample.html")

    if not os.path.exists(golden_file_path):
        pytest.fail(f"Golden file not found: {golden_file_path}")

    expected_prospects = []
    for record_base in EXPECTED_TREASURY_PROSPECTS_BASE:
        record = record_base.copy()
        record["source_name"] = treasury_full_test_config.source_name 
        # Prepare record with keys matching those used in fields_for_id_hash *before* db_column_rename_map
        # This is tricky because fields_for_id_hash uses a mix.
        # native_id_final, naics_intermediate, title_intermediate, description_final, agency_intermediate, place_city, place_state, row_index
        record_for_hash = {
            'native_id_final': record.get('native_id'),
            'naics_intermediate': record.get('naics'),
            'title_intermediate': record.get('title'),
            'description_final': record.get('description'), # Will be None
            'agency_intermediate': record.get('agency'),
            'place_city': record.get('place_city'),
            'place_state': record.get('place_state'),
            'row_index': record.get('row_index')
        }
        record["id_hash"] = precalculate_treasury_id_hash(record_for_hash, treasury_full_test_config)
        expected_prospects.append(record)
    
    # Call the method under test - this will now attempt real DB writes
    loaded_count = treasury_scraper_for_integration._process_method(golden_file_path)

    assert loaded_count == len(expected_prospects)
    
    stmt = select(Prospect).where(Prospect.source_name == treasury_full_test_config.source_name).order_by(Prospect.native_id, Prospect.row_index)
    retrieved_prospects = db_session.execute(stmt).scalars().all()

    assert len(retrieved_prospects) == len(expected_prospects)

    # Sort expected by native_id and row_index for comparison
    expected_prospects_sorted = sorted(expected_prospects, key=lambda x: (x['native_id'], x.get('row_index', -1)))

    for retrieved, expected in zip(retrieved_prospects, expected_prospects_sorted):
        assert retrieved.native_id == expected['native_id']
        assert retrieved.title == expected['title']
        assert retrieved.description == expected['description'] # Should be None
        assert retrieved.agency == expected['agency']
        assert retrieved.naics == expected['naics']
        assert retrieved.estimated_value == expected['estimated_value']
        assert retrieved.est_value_unit == expected['est_value_unit']
        assert retrieved.release_date == expected['release_date']
        assert retrieved.award_date == expected['award_date']
        assert retrieved.award_fiscal_year == expected['award_fiscal_year']
        assert retrieved.place_city == expected['place_city']
        assert (retrieved.place_state == expected['place_state']) or (pd.isna(retrieved.place_state) and pd.isna(expected['place_state']))
        assert retrieved.place_country == expected['place_country']
        assert retrieved.contract_type == expected['contract_type']
        assert (retrieved.set_aside == expected['set_aside']) or (retrieved.set_aside == "None" and expected['set_aside'] is None) # Handle "None" string vs None
        assert retrieved.id_hash == expected['id_hash']
        assert retrieved.source_name == expected['source_name']
        assert retrieved.row_index == expected['row_index'] # Verify row_index was stored
        
        retrieved_extra = retrieved.extra_data if isinstance(retrieved.extra_data, dict) else {}
        expected_extra = expected.get('extra_data', {}) if isinstance(expected.get('extra_data'), dict) else {}
        assert retrieved_extra == expected_extra
        assert retrieved.loaded_at is not None
