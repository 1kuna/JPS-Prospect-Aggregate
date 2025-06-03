import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from typing import Optional, Dict, Any # Added Dict, Any
import datetime 
import os 
import hashlib # For id_hash pre-calculation

from app.core.scrapers.hhs_forecast import HHSForecastScraper
from app.core.scrapers.configs.hhs_config import HHSConfig, DataProcessingRules
from app.exceptions import ScraperError
from app.config import active_config
from app.models import Prospect
from app.utils.scraper_utils import generate_id_hash # For id_hash pre-calculation
from sqlalchemy import select


# --- Helper for ID Hash ---
def precalculate_hhs_id_hash(record: Dict, config: HHSConfig) -> str:
    """Pre-calculates id_hash for an expected record based on HHS config."""
    # fields_for_id_hash from HHSConfig:
    # ['native_id_raw', 'naics_raw', 'title_raw', 'description_raw', 
    #  'agency_raw', 'place_city_raw', 'place_state_raw', 'contract_type_raw', 
    #  'set_aside_raw', 'estimated_value', 'award_date', 'release_date', 'row_index']
    # The `record` dict passed here has final model field names.
    
    # Map final field names from `record` to the intermediate/final names used in fields_for_id_hash
    # Most are _raw from initial rename, but estimated_value, award_date, release_date are post-parsing.
    data_for_hash = {
        'native_id_raw': str(record.get('native_id', '')),
        'naics_raw': str(record.get('naics', '')),
        'title_raw': str(record.get('title', '')),
        'description_raw': str(record.get('description', '')),
        'agency_raw': str(record.get('agency', '')),
        'place_city_raw': str(record.get('place_city', '')),
        'place_state_raw': str(record.get('place_state', '')),
        'contract_type_raw': str(record.get('contract_type', '')),
        'set_aside_raw': str(record.get('set_aside', '')),
        'estimated_value': record.get('estimated_value'), # This is post-parsing
        'award_date': record.get('award_date'), # This is post-parsing
        'release_date': record.get('release_date'), # This is post-parsing
        'row_index': record.get('row_index')
    }
    temp_df_data = {key: str(data_for_hash.get(key)) if pd.notna(data_for_hash.get(key)) else '' 
                    for key in config.data_processing_rules.fields_for_id_hash}
    temp_df = pd.DataFrame([temp_df_data])
    id_hash_series = generate_id_hash(temp_df, config.data_processing_rules.fields_for_id_hash, prefix=config.source_name)
    return id_hash_series[0]

# --- Expected Data ---
EXPECTED_HHS_PROSPECTS_BASE = [
    {
        "native_id": "HHS-001", "agency": "NIH", "title": "IT Support",
        "description": "General IT support services", "naics": "541511",
        "contract_vehicle": "GSA MAS", # Goes to extra_data
        "contract_type": "FFP", "estimated_value": 1000000.0, "est_value_unit": "M USD",
        "award_date": datetime.date(2023, 10, 15), "award_fiscal_year": 2023,
        "release_date": datetime.date(2023, 8, 1), "set_aside": "Small Business",
        "place_city": "Bethesda", "place_state": "MD", "place_country": "USA",
        "row_index": 0,
        "extra_data": {'contract_vehicle_extra': 'GSA MAS'} # Mapped from raw_column_rename_map
    },
    {
        "native_id": "HHS-002", "agency": "CDC", "title": "Lab Equipment",
        "description": "Purchase of new lab equipment", "naics": "334516",
        "contract_vehicle": "SEWP", # Goes to extra_data
        "contract_type": "FIRM FIXED PRICE", "estimated_value": 250000.0, "est_value_unit": "K USD",
        "award_date": datetime.date(2023, 11, 20), "award_fiscal_year": 2023,
        "release_date": datetime.date(2023, 9, 5), "set_aside": "None", # "None" string
        "place_city": "Atlanta", "place_state": "GA", "place_country": "USA",
        "row_index": 1,
        "extra_data": {'contract_vehicle_extra': 'SEWP'}
    },
]

# --- Fixtures ---
@pytest.fixture
def hhs_full_test_config(): 
    conf = HHSConfig(source_name="HHS Integration Test")
    conf.data_processing_rules = HHSConfig().data_processing_rules # Use default full rules
    return conf

@pytest.fixture
def hhs_unit_test_config(): 
    return HHSConfig(
        source_name="HHS Unit Test",
        data_processing_rules=DataProcessingRules( 
            custom_transform_functions=["_custom_hhs_transforms"],
            raw_column_rename_map={'Procurement Number': 'native_id_raw', 'Place of Performance Country': 'place_country_raw'},
            db_column_rename_map={'native_id_raw': 'native_id', 'row_index': 'row_index', 'place_country_final': 'place_country'},
            fields_for_id_hash=['native_id_raw', 'row_index']
        )
    )

@pytest.fixture
def mock_hhs_dependencies(mocker): # For unit tests
    mocker.patch.object(HHSForecastScraper, 'navigate_to_url', return_value=None)
    mocker.patch.object(HHSForecastScraper, 'click_element', return_value=None) 
    mocker.patch.object(HHSForecastScraper, 'wait_for_timeout', return_value=None) 
    mocker.patch.object(HHSForecastScraper, 'wait_for_load_state', return_value=None) 
    mocker.patch.object(HHSForecastScraper, 'download_file_via_click', return_value="/fake/hhs.csv")
    mocker.patch.object(HHSForecastScraper, 'setup_browser', return_value=None)
    mocker.patch.object(HHSForecastScraper, 'cleanup_browser', return_value=None)

@pytest.fixture
def hhs_scraper_unit_instance(hhs_unit_test_config, mock_hhs_dependencies, mocker): # Renamed
    mocker.patch.object(HHSForecastScraper, 'read_file_to_dataframe', return_value=pd.DataFrame())
    mocker.patch.object(HHSForecastScraper, 'prepare_and_load_data', return_value=0)
    scraper = HHSForecastScraper(config=hhs_unit_test_config, debug_mode=True)
    scraper.page = MagicMock(); scraper.logger = MagicMock(); scraper._last_download_path = "/fake/hhs.csv"
    return scraper

@pytest.fixture
def hhs_scraper_for_integration(hhs_full_test_config, db_session, mocker):
    mocker.patch.object(HHSForecastScraper, 'setup_browser', return_value=None)
    mocker.patch.object(HHSForecastScraper, 'cleanup_browser', return_value=None)
    mocker.patch.object(HHSForecastScraper, 'navigate_to_url', return_value=None)
    mocker.patch.object(HHSForecastScraper, 'click_element', return_value=None)
    mocker.patch.object(HHSForecastScraper, 'wait_for_timeout', return_value=None)
    mocker.patch.object(HHSForecastScraper, 'wait_for_load_state', return_value=None)
    mocker.patch.object(HHSForecastScraper, 'download_file_via_click', return_value=None) # Not used by _process_method
    scraper = HHSForecastScraper(config=hhs_full_test_config, debug_mode=True)
    scraper.logger = MagicMock()
    return scraper

# --- Basic Tests ---
def test_hhs_scraper_instantiation(hhs_unit_test_config):
    try: scraper = HHSForecastScraper(config=hhs_unit_test_config); assert scraper.config == hhs_unit_test_config
    except Exception as e: pytest.fail(f"HHSForecastScraper instantiation failed: {e}")

# --- Integration Test for _process_method with DB Validation ---
def test_hhs_process_method_integration(hhs_scraper_for_integration, hhs_full_test_config, db_session):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    golden_file_path = os.path.join(current_dir, "..", "..", "fixtures", "golden_files", "hhs_scraper", "hhs_sample.csv")

    if not os.path.exists(golden_file_path):
        pytest.fail(f"Golden file not found: {golden_file_path}")

    expected_prospects = []
    for i, record_base in enumerate(EXPECTED_HHS_PROSPECTS_BASE):
        record = record_base.copy()
        record["source_name"] = hhs_full_test_config.source_name 
        # For HHS, row_index is part of the hash. The base record already has it.
        record["id_hash"] = precalculate_hhs_id_hash(record, hhs_full_test_config)
        expected_prospects.append(record)
    
    # Call the method under test - this will now attempt real DB writes
    loaded_count = hhs_scraper_for_integration._process_method(golden_file_path)

    assert loaded_count == len(expected_prospects)
    
    stmt = select(Prospect).where(Prospect.source_name == hhs_full_test_config.source_name).order_by(Prospect.native_id)
    retrieved_prospects = db_session.execute(stmt).scalars().all()

    assert len(retrieved_prospects) == len(expected_prospects)

    expected_prospects_sorted = sorted(expected_prospects, key=lambda x: x['native_id'])

    for retrieved, expected in zip(retrieved_prospects, expected_prospects_sorted):
        assert retrieved.native_id == expected['native_id']
        assert retrieved.title == expected['title']
        assert retrieved.description == expected['description']
        assert retrieved.agency == expected['agency']
        assert retrieved.naics == expected['naics']
        assert retrieved.estimated_value == expected['estimated_value']
        assert retrieved.est_value_unit == expected['est_value_unit']
        assert retrieved.release_date == expected['release_date']
        assert retrieved.award_date == expected['award_date']
        assert retrieved.award_fiscal_year == expected['award_fiscal_year']
        assert retrieved.place_city == expected['place_city']
        assert retrieved.place_state == expected['place_state']
        assert retrieved.place_country == expected['place_country'] # Validated from custom transform
        assert retrieved.contract_type == expected['contract_type']
        assert (retrieved.set_aside == expected['set_aside']) or \
               (retrieved.set_aside == "None" and expected['set_aside'] is None) # Handle "None" string
        
        assert retrieved.id_hash == expected['id_hash']
        assert retrieved.source_name == expected['source_name']
        assert retrieved.row_index == expected['row_index'] # Verify row_index
        
        retrieved_extra = retrieved.extra_data if isinstance(retrieved.extra_data, dict) else {}
        expected_extra = expected.get('extra_data', {}) if isinstance(expected.get('extra_data'), dict) else {}
        assert retrieved_extra == expected_extra
        assert retrieved.loaded_at is not None
