import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from typing import Optional, Dict, Any # Added Dict, Any
import datetime 
import os 
import hashlib # For id_hash pre-calculation

from app.core.scrapers.dhs_scraper import DHSForecastScraper
from app.core.scrapers.configs.dhs_config import DHSConfig, DataProcessingRules
from app.exceptions import ScraperError
from app.config import active_config
from app.models import Prospect
from app.utils.scraper_utils import generate_id_hash # For id_hash pre-calculation
from sqlalchemy import select


# --- Helper for ID Hash ---
def precalculate_dhs_id_hash(record: Dict, config: DHSConfig) -> str:
    """Pre-calculates id_hash for an expected record based on DHS config."""
    # fields_for_id_hash from DHSConfig:
    # ['native_id_raw', 'naics_raw', 'title_raw', 'description_raw', 
    #  'place_city_raw', 'place_state_raw']
    # The `record` dict passed here has final model field names.
    
    data_for_hash = {
        'native_id_raw': str(record.get('native_id', '')),
        'naics_raw': str(record.get('naics', '')),
        'title_raw': str(record.get('title', '')),
        'description_raw': str(record.get('description', '')),
        'place_city_raw': str(record.get('place_city', '')),
        'place_state_raw': str(record.get('place_state', ''))
    }
    temp_df_data = {key: data_for_hash.get(key) for key in config.data_processing_rules.fields_for_id_hash}
    temp_df = pd.DataFrame([temp_df_data])
    id_hash_series = generate_id_hash(temp_df, config.data_processing_rules.fields_for_id_hash, prefix=config.source_name)
    return id_hash_series[0]

# --- Expected Data ---
EXPECTED_DHS_PROSPECTS_BASE = [
    {
        "native_id": "DHS-001", "naics": "541511", "agency": "CISA", "title": "Cybersecurity Support",
        "contract_type": "FFP", "estimated_value": 1000000.0, "est_value_unit": "M USD",
        "set_aside": "Small Business", "place_city": "Arlington", "place_state": "VA",
        "description": "Support for cyber operations", "release_date": datetime.date(2023, 10, 15),
        "award_date": datetime.date(2023, 10, 1), "award_fiscal_year": 2024, # 2024 Q1
        "place_country": "USA", # Defaulted by custom transform
        "extra_data": {
            'contract_vehicle_extra': 'GSA MAS', 
            'small_business_program_extra': 'None',
            'contract_status_extra': 'Awarded'
        }
    },
    {
        "native_id": "DHS-002", "naics": "541512", "agency": "FEMA", "title": "Cloud Migration",
        "contract_type": "T&M", "estimated_value": 10000000.0, "est_value_unit": "M USD",
        "set_aside": "None", "place_city": "Reston", "place_state": "VA",
        "description": "Migrate systems to cloud", "release_date": datetime.date(2023, 11, 1),
        "award_date": datetime.date(2024, 1, 1), "award_fiscal_year": 2024, # 2024 Q2
        "place_country": "USA",
        "extra_data": {
            'contract_vehicle_extra': 'SEWP',
            'small_business_program_extra': '8(a)',
            'contract_status_extra': 'Planned'
        }
    },
]


# --- Fixtures ---
@pytest.fixture
def dhs_full_test_config(): 
    conf = DHSConfig(source_name="DHS Integration Test")
    conf.data_processing_rules = DHSConfig().data_processing_rules
    return conf

@pytest.fixture
def dhs_unit_test_config(): 
    return DHSConfig(source_name="DHS Unit Test", data_processing_rules=DataProcessingRules(fields_for_id_hash=['native_id_raw']))

@pytest.fixture
def mock_dhs_dependencies(mocker): # For unit tests
    mocker.patch.object(DHSForecastScraper, 'navigate_to_url', return_value=None)
    mocker.patch.object(DHSForecastScraper, 'wait_for_load_state', return_value=None)
    mocker.patch.object(DHSForecastScraper, 'wait_for_timeout', return_value=None)
    mocker.patch.object(DHSForecastScraper, 'download_file_via_click', return_value="/fake/dhs.csv")
    mocker.patch.object(DHSForecastScraper, 'setup_browser', return_value=None)
    mocker.patch.object(DHSForecastScraper, 'cleanup_browser', return_value=None)

@pytest.fixture
def dhs_scraper_unit_instance(dhs_unit_test_config, mock_dhs_dependencies, mocker): 
    mocker.patch.object(DHSForecastScraper, 'read_file_to_dataframe', return_value=pd.DataFrame())
    mocker.patch.object(DHSForecastScraper, 'prepare_and_load_data', return_value=0)
    scraper = DHSForecastScraper(config=dhs_unit_test_config, debug_mode=True)
    scraper.page = MagicMock(); scraper.logger = MagicMock(); scraper._last_download_path = "/fake/dhs.csv"
    return scraper

@pytest.fixture
def dhs_scraper_for_integration(dhs_full_test_config, db_session, mocker):
    mocker.patch.object(DHSForecastScraper, 'setup_browser', return_value=None)
    mocker.patch.object(DHSForecastScraper, 'cleanup_browser', return_value=None)
    mocker.patch.object(DHSForecastScraper, 'navigate_to_url', return_value=None)
    mocker.patch.object(DHSForecastScraper, 'download_file_via_click', return_value=None)
    mocker.patch.object(DHSForecastScraper, 'wait_for_load_state', return_value=None)
    mocker.patch.object(DHSForecastScraper, 'wait_for_timeout', return_value=None)
    scraper = DHSForecastScraper(config=dhs_full_test_config, debug_mode=True)
    scraper.logger = MagicMock()
    return scraper

# --- Basic Tests ---
def test_dhs_scraper_instantiation(dhs_unit_test_config):
    try: scraper = DHSForecastScraper(config=dhs_unit_test_config); assert scraper.config == dhs_unit_test_config
    except Exception as e: pytest.fail(f"DHSForecastScraper instantiation failed: {e}")

# --- Integration Test for _process_method with DB Validation ---
def test_dhs_process_method_integration(dhs_scraper_for_integration, dhs_full_test_config, db_session):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    golden_file_path = os.path.join(current_dir, "..", "..", "fixtures", "golden_files", "dhs_scraper", "dhs_sample.csv")

    if not os.path.exists(golden_file_path):
        pytest.fail(f"Golden file not found: {golden_file_path}")

    expected_prospects = []
    for record_base in EXPECTED_DHS_PROSPECTS_BASE:
        record = record_base.copy()
        record["source_name"] = dhs_full_test_config.source_name 
        record["id_hash"] = precalculate_dhs_id_hash(record, dhs_full_test_config)
        expected_prospects.append(record)
    
    # Call the method under test - this will now attempt real DB writes
    loaded_count = dhs_scraper_for_integration._process_method(golden_file_path)

    assert loaded_count == len(expected_prospects)
    
    stmt = select(Prospect).where(Prospect.source_name == dhs_full_test_config.source_name).order_by(Prospect.native_id)
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
        assert retrieved.place_country == expected['place_country']
        assert retrieved.contract_type == expected['contract_type']
        assert retrieved.set_aside == expected['set_aside']
        assert retrieved.id_hash == expected['id_hash']
        assert retrieved.source_name == expected['source_name']
        
        retrieved_extra = retrieved.extra_data if isinstance(retrieved.extra_data, dict) else {}
        expected_extra = expected.get('extra_data', {}) if isinstance(expected.get('extra_data'), dict) else {}
        assert retrieved_extra == expected_extra
        assert retrieved.loaded_at is not None
```
