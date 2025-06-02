import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from typing import Optional, Dict, Any # Added Dict, Any
from urllib.parse import urljoin 
import datetime 
import os 
import hashlib # For id_hash pre-calculation

from app.core.scrapers.doc_scraper import DocScraper
from app.core.scrapers.configs.doc_config import DOCConfig, DataProcessingRules
from app.exceptions import ScraperError
from app.config import active_config 
from app.models import Prospect
from app.utils.scraper_utils import generate_id_hash # For id_hash pre-calculation
from sqlalchemy import select


# --- Helper for ID Hash ---
def precalculate_doc_id_hash(record: Dict, config: DOCConfig) -> str:
    """Pre-calculates id_hash for an expected record based on DOC config."""
    # fields_for_id_hash from DOCConfig:
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
EXPECTED_DOC_PROSPECTS_BASE = [
    {
        "native_id": "DOC-001", "agency": "ITA", "title": "Cloud Services",
        "description": "Cloud computing services", "naics": "541511",
        "place_city": "Arlington", "place_state": "VA", "place_country": "USA",
        "estimated_value": 1000000.0, "est_value_unit": "M USD",
        "release_date": datetime.date(2024, 1, 1), # 2024 Q2
        "award_date": None, "award_fiscal_year": pd.NA, 
        "set_aside": "Small Business",
        "extra_data": {
            'action_award_type_extra': 'BPA', 
            'competition_strategy_extra': 'Full and Open',
            'contract_vehicle_extra': 'GSA MAS'
        }
    },
    {
        "native_id": "DOC-002", "agency": "NOAA", "title": "Weather Buoys",
        "description": "Maintenance of weather buoys", "naics": "334511",
        "place_city": "San Diego", "place_state": "CA", "place_country": "USA",
        "estimated_value": 500000.0, "est_value_unit": "K USD",
        "release_date": datetime.date(2024, 4, 1), # 2024 Q3
        "award_date": None, "award_fiscal_year": pd.NA,
        "set_aside": "None", # "None" string from sample
        "extra_data": {
            'action_award_type_extra': 'IDIQ',
            'competition_strategy_extra': 'Not Specified',
            'contract_vehicle_extra': 'SEWP' # Original sample had SEWP III, assuming it maps to SEWP
        }
    },
]


# --- Fixtures ---
@pytest.fixture
def doc_full_test_config(): 
    conf = DOCConfig(source_name="DOC Integration Test")
    conf.data_processing_rules = DOCConfig().data_processing_rules
    return conf

@pytest.fixture
def doc_unit_test_config(): 
    return DOCConfig(source_name="DOC Unit Test", data_processing_rules=DataProcessingRules(fields_for_id_hash=['native_id_raw']))

@pytest.fixture
def mock_doc_dependencies(mocker): # For unit tests
    mocker.patch.object(DocScraper, 'navigate_to_url', return_value=None)
    mocker.patch.object(DocScraper, 'wait_for_selector', return_value=None)
    mocker.patch.object(DocScraper, 'download_file_directly', return_value="/fake/doc.xlsx")
    mocker.patch.object(DocScraper, 'setup_browser', return_value=None)
    mocker.patch.object(DocScraper, 'cleanup_browser', return_value=None)

@pytest.fixture
def doc_scraper_unit_instance(doc_unit_test_config, mock_doc_dependencies, mocker): 
    mocker.patch.object(DocScraper, 'read_file_to_dataframe', return_value=pd.DataFrame())
    mocker.patch.object(DocScraper, 'prepare_and_load_data', return_value=0)
    scraper = DocScraper(config=doc_unit_test_config, debug_mode=True)
    scraper.page = MagicMock(); scraper.page.url = doc_unit_test_config.base_url 
    scraper.page.locator.return_value.first = MagicMock(get_attribute=lambda attr: "rel/path.xlsx")
    scraper.logger = MagicMock()
    mock_playwright = MagicMock(); mock_api_context = MagicMock()
    mock_api_context.get.return_value = MagicMock(ok=True, body=lambda: b"filedata", headers={})
    mock_playwright.request.new_context.return_value = mock_api_context
    scraper.playwright = mock_playwright
    return scraper

@pytest.fixture
def doc_scraper_for_integration(doc_full_test_config, db_session, mocker):
    mocker.patch.object(DocScraper, 'setup_browser', return_value=None)
    mocker.patch.object(DocScraper, 'cleanup_browser', return_value=None)
    mocker.patch.object(DocScraper, 'navigate_to_url', return_value=None)
    mocker.patch.object(DocScraper, 'wait_for_selector', return_value=None)
    mocker.patch.object(DocScraper, 'download_file_directly', return_value=None) # Not called by _process_method
    scraper = DocScraper(config=doc_full_test_config, debug_mode=True)
    scraper.logger = MagicMock()
    return scraper

# --- Basic Tests ---
def test_doc_scraper_instantiation(doc_unit_test_config):
    try: scraper = DocScraper(config=doc_unit_test_config); assert scraper.config == doc_unit_test_config
    except Exception as e: pytest.fail(f"DocScraper instantiation failed: {e}")

# --- Integration Test for _process_method with DB Validation ---
def test_doc_process_method_integration(doc_scraper_for_integration, doc_full_test_config, db_session):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    golden_file_path = os.path.join(current_dir, "..", "..", "fixtures", "golden_files", "doc_scraper", "doc_sample.xlsx")

    if not os.path.exists(golden_file_path):
        pytest.fail(f"Golden file not found: {golden_file_path}")

    expected_prospects = []
    for record_base in EXPECTED_DOC_PROSPECTS_BASE:
        record = record_base.copy()
        record["source_name"] = doc_full_test_config.source_name 
        record["id_hash"] = precalculate_doc_id_hash(record, doc_full_test_config)
        expected_prospects.append(record)
    
    # Call the method under test - this will now attempt real DB writes
    loaded_count = doc_scraper_for_integration._process_method(golden_file_path)

    assert loaded_count == len(expected_prospects)
    
    stmt = select(Prospect).where(Prospect.source_name == doc_full_test_config.source_name).order_by(Prospect.native_id)
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
        assert pd.isna(retrieved.award_date) if pd.isna(expected['award_date']) else retrieved.award_date == expected['award_date']
        assert pd.isna(retrieved.award_fiscal_year) if pd.isna(expected['award_fiscal_year']) else retrieved.award_fiscal_year == expected['award_fiscal_year']
        assert retrieved.place_city == expected['place_city']
        assert retrieved.place_state == expected['place_state']
        assert retrieved.place_country == expected['place_country']
        assert retrieved.set_aside == expected['set_aside']
        assert retrieved.id_hash == expected['id_hash']
        assert retrieved.source_name == expected['source_name']
        
        retrieved_extra = retrieved.extra_data if isinstance(retrieved.extra_data, dict) else {}
        expected_extra = expected.get('extra_data', {}) if isinstance(expected.get('extra_data'), dict) else {}
        # Normalize by converting all values to string for comparison if they are not dicts/lists themselves,
        # as sometimes numeric-like strings might be loaded as numbers by pandas then converted back to str.
        # However, for this test, direct comparison should work if types are consistent.
        assert retrieved_extra == expected_extra
        assert retrieved.loaded_at is not None
```
