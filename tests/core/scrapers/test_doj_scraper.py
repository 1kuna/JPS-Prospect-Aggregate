import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from typing import Optional, Dict, Any # Added Dict, Any
import datetime 
import os 
import hashlib # For id_hash pre-calculation

from app.core.scrapers.doj_scraper import DOJForecastScraper
from app.core.scrapers.configs.doj_config import DOJConfig, DataProcessingRules
from app.exceptions import ScraperError
from app.config import active_config
from app.models import Prospect
from app.utils.scraper_utils import generate_id_hash # For id_hash pre-calculation
from sqlalchemy import select


# --- Helper for ID Hash ---
def precalculate_doj_id_hash(record: Dict, config: DOJConfig) -> str:
    """Pre-calculates id_hash for an expected record based on DOJ config."""
    # fields_for_id_hash from DOJConfig:
    # ['native_id_raw', 'naics_raw', 'title_raw', 'description_raw', 
    #  'place_city_intermediate', 'place_state_intermediate']
    # The `record` dict passed here has final model field names.
    
    data_for_hash = {
        'native_id_raw': str(record.get('native_id', '')),
        'naics_raw': str(record.get('naics', '')),
        'title_raw': str(record.get('title', '')),
        'description_raw': str(record.get('description', '')),
        # For place_city/state, the hash fields use *_intermediate names.
        # These are direct outputs from split_place if it was configured in declarative parsing rules
        # (which it is in DOJConfig for 'place_raw').
        # So, the `record` keys should match these intermediate names conceptually.
        'place_city_intermediate': str(record.get('place_city', '')), 
        'place_state_intermediate': str(record.get('place_state', '')) 
    }
    temp_df_data = {key: data_for_hash.get(key) for key in config.data_processing_rules.fields_for_id_hash}
    temp_df = pd.DataFrame([temp_df_data])
    id_hash_series = generate_id_hash(temp_df, config.data_processing_rules.fields_for_id_hash, prefix=config.source_name)
    return id_hash_series[0]

# --- Expected Data ---
EXPECTED_DOJ_PROSPECTS_BASE = [
    {
        "native_id": "DOJ-001", "bureau": "FBI", "title": "IT Modernization", # Bureau is agency
        "description": "Modernize IT systems", "contract_type": "FFP", "naics": "541511",
        "set_aside": "None", "estimated_value": 10000000.0, "est_value_unit": "M USD",
        "release_date": datetime.date(2023, 10, 1), 
        "award_date": datetime.date(2024, 1, 15), "award_fiscal_year": 2024,
        "place_city": "Washington", "place_state": "DC", "place_country": "USA",
        "extra_data": None # No specific extra fields mapped from sample for this one
    },
    {
        "native_id": "DOJ-002", "bureau": "DEA", "title": "Analytical Services",
        "description": "Forensic analysis services", "contract_type": "LH", "naics": "541990",
        "set_aside": "Small Business", "estimated_value": 1000000.0, "est_value_unit": "M USD",
        "release_date": datetime.date(2023, 11, 15),
        "award_date": datetime.date(2024, 1, 1), "award_fiscal_year": 2024, # From "2024 Q2"
        "place_city": "Quantico", "place_state": "VA", "place_country": "USA",
        "extra_data": None
    },
]

# --- Fixtures ---
@pytest.fixture
def doj_full_test_config(): 
    conf = DOJConfig(source_name="DOJ Integration Test")
    conf.data_processing_rules = DOJConfig().data_processing_rules
    # Ensure agency mapping is correct for expected data
    conf.data_processing_rules.db_column_rename_map['agency_raw'] = 'agency' 
    return conf

@pytest.fixture
def doj_unit_test_config(): 
    return DOJConfig(source_name="DOJ Unit Test", data_processing_rules=DataProcessingRules(fields_for_id_hash=['native_id_raw']))


@pytest.fixture
def mock_doj_dependencies(mocker): # For unit tests
    mocker.patch.object(DOJForecastScraper, 'navigate_to_url', return_value=None)
    mocker.patch.object(DOJForecastScraper, 'wait_for_load_state', return_value=None)
    mocker.patch.object(DOJForecastScraper, 'wait_for_selector', return_value=None) 
    mocker.patch.object(DOJForecastScraper, 'download_file_via_click', return_value="/fake/doj.xlsx")
    mocker.patch.object(DOJForecastScraper, 'setup_browser', return_value=None)
    mocker.patch.object(DOJForecastScraper, 'cleanup_browser', return_value=None)

@pytest.fixture
def doj_scraper_unit_instance(doj_unit_test_config, mock_doj_dependencies, mocker): 
    mocker.patch.object(DOJForecastScraper, 'read_file_to_dataframe', return_value=pd.DataFrame())
    mocker.patch.object(DOJForecastScraper, 'prepare_and_load_data', return_value=0)
    scraper = DOJForecastScraper(config=doj_unit_test_config, debug_mode=True)
    scraper.page = MagicMock(); scraper.logger = MagicMock(); scraper._last_download_path = "/fake/doj.xlsx"
    return scraper

@pytest.fixture
def doj_scraper_for_integration(doj_full_test_config, db_session, mocker):
    mocker.patch.object(DOJForecastScraper, 'setup_browser', return_value=None)
    mocker.patch.object(DOJForecastScraper, 'cleanup_browser', return_value=None)
    mocker.patch.object(DOJForecastScraper, 'navigate_to_url', return_value=None)
    mocker.patch.object(DOJForecastScraper, 'download_file_via_click', return_value=None)
    mocker.patch.object(DOJForecastScraper, 'wait_for_selector', return_value=None)
    mocker.patch.object(DOJForecastScraper, 'wait_for_load_state', return_value=None)
    scraper = DOJForecastScraper(config=doj_full_test_config, debug_mode=True)
    scraper.logger = MagicMock()
    return scraper

# --- Basic Tests ---
def test_doj_scraper_instantiation(doj_unit_test_config):
    try: scraper = DOJForecastScraper(config=doj_unit_test_config); assert scraper.config == doj_unit_test_config
    except Exception as e: pytest.fail(f"DOJForecastScraper instantiation failed: {e}")

# --- Integration Test for _process_method with DB Validation ---
def test_doj_process_method_integration(doj_scraper_for_integration, doj_full_test_config, db_session):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    golden_file_path = os.path.join(current_dir, "..", "..", "fixtures", "golden_files", "doj_scraper", "doj_sample.xlsx")

    if not os.path.exists(golden_file_path):
        pytest.fail(f"Golden file not found: {golden_file_path}")

    expected_prospects = []
    for record_base in EXPECTED_DOJ_PROSPECTS_BASE:
        record = record_base.copy()
        record["source_name"] = doj_full_test_config.source_name 
        # Map final field names to those used in fields_for_id_hash for this helper
        record_for_hash = {
            'native_id': record.get('native_id'), 'naics': record.get('naics'),
            'title': record.get('title'), 'description': record.get('description'),
            'place_city': record.get('place_city'), 'place_state': record.get('place_state')
        }
        record["id_hash"] = precalculate_doj_id_hash(record_for_hash, doj_full_test_config)
        expected_prospects.append(record)
    
    # Call the method under test - this will now attempt real DB writes
    loaded_count = doj_scraper_for_integration._process_method(golden_file_path)

    assert loaded_count == len(expected_prospects)
    
    stmt = select(Prospect).where(Prospect.source_name == doj_full_test_config.source_name).order_by(Prospect.native_id)
    retrieved_prospects = db_session.execute(stmt).scalars().all()

    assert len(retrieved_prospects) == len(expected_prospects)

    expected_prospects_sorted = sorted(expected_prospects, key=lambda x: x['native_id'])

    for retrieved, expected in zip(retrieved_prospects, expected_prospects_sorted):
        assert retrieved.native_id == expected['native_id']
        assert retrieved.title == expected['title']
        assert retrieved.description == expected['description']
        # 'bureau' was mapped to 'agency_raw', then 'agency_raw' to 'agency' in db_map
        assert retrieved.agency == expected['bureau'] # Check against 'bureau' from expected base
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
