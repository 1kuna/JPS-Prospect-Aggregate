import pytest
from unittest.mock import MagicMock, patch, call
import pandas as pd
import time 
import shutil 
import os
from typing import Optional, Dict, Any # Added Dict, Any
import datetime 
import hashlib # For id_hash pre-calculation

from app.core.scrapers.dot_scraper import DotScraper
from app.core.scrapers.configs.dot_config import DOTConfig, DataProcessingRules
from app.exceptions import ScraperError
from app.config import active_config
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, Response as PlaywrightResponse, Download
from app.models import Prospect
from app.utils.scraper_utils import generate_id_hash # For id_hash pre-calculation
from sqlalchemy import select


# --- Helper for ID Hash ---
def precalculate_dot_id_hash(record: Dict, config: DOTConfig) -> str:
    """Pre-calculates id_hash for an expected record based on DOT config."""
    # fields_for_id_hash from DOTConfig:
    # ['native_id_raw', 'naics_raw', 'title_raw', 'description_raw', 
    #  'place_city_intermediate', 'place_state_intermediate']
    # The `record` dict passed here has final model field names.
    
    data_for_hash = {
        'native_id_raw': str(record.get('native_id', '')),
        'naics_raw': str(record.get('naics', '')),
        'title_raw': str(record.get('title', '')),
        'description_raw': str(record.get('description', '')),
        'place_city_intermediate': str(record.get('place_city', '')),
        'place_state_intermediate': str(record.get('place_state', ''))
    }
    temp_df_data = {key: data_for_hash.get(key) for key in config.data_processing_rules.fields_for_id_hash}
    temp_df = pd.DataFrame([temp_df_data])
    id_hash_series = generate_id_hash(temp_df, config.data_processing_rules.fields_for_id_hash, prefix=config.source_name)
    return id_hash_series[0]

# --- Expected Data ---
EXPECTED_DOT_PROSPECTS_BASE = [
    {
        "native_id": "DOT-001", "agency": "FAA", "title": "IT Infrastructure Upgrade",
        "description": "Upgrade of IT infrastructure for FAA facilities.",
        "estimated_value": 10000000.0, "est_value_unit": "M USD", "naics": "541511",
        "set_aside": "8(a)", "release_date": datetime.date(2023, 10, 1), # 2024 Q1
        "award_date": datetime.date(2024, 1, 15), "award_fiscal_year": 2024,
        "place_city": "Washington", "place_state": "DC", "place_country": "USA",
        "contract_type": "IDIQ", # Fallback from Action/Award Type
        "extra_data": {'action_award_type_extra': 'IDIQ', 'contract_vehicle_extra': 'GSA MAS'}
    },
    {
        "native_id": "DOT-002", "agency": "FHWA", "title": "Bridge Inspection Services",
        "description": "Nationwide bridge inspection services.",
        "estimated_value": 5000000.0, "est_value_unit": "M USD", "naics": "541330",
        "set_aside": "Small Business", "release_date": datetime.date(2024, 1, 1), # 2024 Q2
        "award_date": datetime.date(2024, 3, 30), "award_fiscal_year": 2024,
        "place_city": "Various", "place_state": None, "place_country": "USA", # "Various, USA"
        "contract_type": "BPA",
        "extra_data": {'action_award_type_extra': 'BPA', 'contract_vehicle_extra': 'None'} # "None" string
    },
    {
        "native_id": "DOT-003", "agency": "FRA", "title": "Rail Safety Research",
        "description": "Research on advanced rail safety technologies.",
        "estimated_value": 1000000.0, "est_value_unit": "M USD", "naics": "541715",
        "set_aside": "Full and Open", "release_date": datetime.date(2024, 4, 1), # 2024 Q3
        "award_date": None, "award_fiscal_year": pd.NA, # INVALID_DATE_FORMAT
        "place_city": "Springfield", "place_state": "VA", "place_country": "USA",
        "contract_type": "Firm Fixed Price",
        "extra_data": {'action_award_type_extra': 'Firm Fixed Price', 'contract_vehicle_extra': 'SEWP III'}
    },
]

# --- Fixtures ---
@pytest.fixture
def dot_full_test_config(): 
    conf = DOTConfig(source_name="DOT Integration Test")
    conf.data_processing_rules = DOTConfig().data_processing_rules
    return conf

@pytest.fixture
def dot_unit_test_config(): 
    return DOTConfig(source_name="DOT Unit Test", data_processing_rules=DataProcessingRules(fields_for_id_hash=['native_id_raw']))

@pytest.fixture
def mock_dot_dependencies(mocker): # For unit tests
    mocker.patch.object(DotScraper, 'click_element', return_value=None)
    mocker.patch.object(DotScraper, 'wait_for_load_state', return_value=None)
    mocker.patch.object(DotScraper, 'wait_for_timeout', return_value=None)
    mocker.patch.object(DotScraper, '_handle_download_event', return_value=None)
    mocker.patch('shutil.copy2', return_value=None)
    mocker.patch.object(DotScraper, 'setup_browser', return_value=None)
    mocker.patch.object(DotScraper, 'cleanup_browser', return_value=None)

@pytest.fixture
def dot_scraper_unit_instance(dot_unit_test_config, mock_dot_dependencies, mocker): 
    mocker.patch.object(DotScraper, 'read_file_to_dataframe', return_value=pd.DataFrame())
    mocker.patch.object(DotScraper, 'prepare_and_load_data', return_value=0)
    scraper = DotScraper(config=dot_unit_test_config, debug_mode=True)
    scraper.page = MagicMock(spec_set=PlaywrightPage); scraper.page.url = dot_unit_test_config.base_url 
    mock_new_page = MagicMock(spec_set=PlaywrightPage); mock_new_page.url = "http://new.com"; mock_new_page.is_closed.return_value = False
    mock_context = MagicMock(spec_set=["expect_page", "request"])
    mock_context.expect_page.return_value.__enter__.return_value.value = mock_new_page
    scraper.context = mock_context; scraper.logger = MagicMock(); scraper._last_download_path = None 
    return scraper

@pytest.fixture
def dot_scraper_for_integration(dot_full_test_config, db_session, mocker):
    mocker.patch.object(DotScraper, 'setup_browser', return_value=None)
    mocker.patch.object(DotScraper, 'cleanup_browser', return_value=None)
    mocker.patch.object(DotScraper, 'navigate_to_url', return_value=None)
    mocker.patch.object(DotScraper, 'click_element', return_value=None)
    mocker.patch.object(DotScraper, '_handle_download_event', return_value=None)
    mocker.patch.object(DotScraper, 'wait_for_load_state', return_value=None)
    mocker.patch.object(DotScraper, 'wait_for_timeout', return_value=None)
    mocker.patch('shutil.copy2', return_value=None) 
    scraper = DotScraper(config=dot_full_test_config, debug_mode=True)
    scraper.logger = MagicMock()
    return scraper

# --- Basic Tests ---
def test_dot_scraper_instantiation(dot_unit_test_config):
    try: scraper = DotScraper(config=dot_unit_test_config); assert scraper.config == dot_unit_test_config
    except Exception as e: pytest.fail(f"DotScraper instantiation failed: {e}")

# --- Integration Test for _process_method with DB Validation ---
def test_dot_process_method_integration(dot_scraper_for_integration, dot_full_test_config, db_session):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    golden_file_path = os.path.join(current_dir, "..", "..", "fixtures", "golden_files", "dot_scraper", "dot_sample.csv")

    if not os.path.exists(golden_file_path):
        pytest.fail(f"Golden file not found: {golden_file_path}")

    expected_prospects = []
    for record_base in EXPECTED_DOT_PROSPECTS_BASE:
        record = record_base.copy()
        record["source_name"] = dot_full_test_config.source_name 
        # Prepare record with keys matching those used in fields_for_id_hash
        record_for_hash = {
            'native_id': record.get('native_id'), 'naics': record.get('naics'),
            'title': record.get('title'), 'description': record.get('description'),
            'place_city': record.get('place_city'), 'place_state': record.get('place_state')
        }
        record["id_hash"] = precalculate_dot_id_hash(record_for_hash, dot_full_test_config)
        expected_prospects.append(record)
    
    # Call the method under test - this will now attempt real DB writes
    loaded_count = dot_scraper_for_integration._process_method(golden_file_path)

    assert loaded_count == len(expected_prospects)
    
    stmt = select(Prospect).where(Prospect.source_name == dot_full_test_config.source_name).order_by(Prospect.native_id)
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
        
        # Handle NaT/None for dates
        if pd.isna(expected['award_date']): assert pd.isna(retrieved.award_date)
        else: assert retrieved.award_date == expected['award_date']
        
        if pd.isna(expected['award_fiscal_year']): assert pd.isna(retrieved.award_fiscal_year)
        else: assert retrieved.award_fiscal_year == expected['award_fiscal_year']
            
        assert retrieved.place_city == expected['place_city']
        assert (retrieved.place_state == expected['place_state']) or (pd.isna(retrieved.place_state) and pd.isna(expected['place_state']))
        assert retrieved.place_country == expected['place_country']
        assert retrieved.contract_type == expected['contract_type']
        assert retrieved.set_aside == expected['set_aside']
        assert retrieved.id_hash == expected['id_hash']
        assert retrieved.source_name == expected['source_name']
        
        retrieved_extra = retrieved.extra_data if isinstance(retrieved.extra_data, dict) else {}
        expected_extra = expected.get('extra_data', {}) if isinstance(expected.get('extra_data'), dict) else {}
        assert retrieved_extra == expected_extra
        assert retrieved.loaded_at is not None
