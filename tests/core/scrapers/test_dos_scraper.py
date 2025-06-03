import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from typing import Optional, Dict, Any # Added Dict, Any
import datetime 
import os 
import hashlib # For id_hash pre-calculation

from app.core.scrapers.dos_scraper import DOSForecastScraper
from app.core.scrapers.configs.dos_config import DOSConfig, DataProcessingRules
from app.exceptions import ScraperError
from app.config import active_config
from app.models import Prospect
from app.utils.scraper_utils import generate_id_hash # For id_hash pre-calculation
from sqlalchemy import select


# --- Helper for ID Hash ---
def precalculate_dos_id_hash(record: Dict, config: DOSConfig) -> str:
    """Pre-calculates id_hash for an expected record based on DOS config."""
    # fields_for_id_hash from DOSConfig:
    # ['native_id_raw', 'naics_final', 'title_raw', 'description_raw', 
    #  'place_city_final', 'place_state_final', 'release_date_final', 
    #  'award_date_final', 'row_index']
    # The `record` dict passed here has final model field names.
    
    data_for_hash = {
        # Map final field names from `record` to the intermediate/final names used in fields_for_id_hash
        'native_id_raw': str(record.get('native_id', '')),
        'naics_final': str(record.get('naics', '')), # naics is 'naics_final' in hash list
        'title_raw': str(record.get('title', '')),
        'description_raw': str(record.get('description', '')),
        'place_city_final': str(record.get('place_city', '')),
        'place_state_final': str(record.get('place_state', '')),
        'release_date_final': str(record.get('release_date', '') if pd.notna(record.get('release_date')) else ''),
        'award_date_final': str(record.get('award_date', '') if pd.notna(record.get('award_date')) else ''),
        'row_index': record.get('row_index')
    }
    temp_df_data = {key: data_for_hash.get(key) for key in config.data_processing_rules.fields_for_id_hash}
    temp_df = pd.DataFrame([temp_df_data])
    id_hash_series = generate_id_hash(temp_df, config.data_processing_rules.fields_for_id_hash, prefix=config.source_name)
    return id_hash_series[0]

# --- Expected Data ---
EXPECTED_DOS_PROSPECTS_BASE = [
    {
        "native_id": "DOS-001", "agency": "OBO", "title": "Global IT Support",
        "description": "Worldwide IT services", "estimated_value": 10000000.0, "est_value_unit": "M USD",
        "place_country": "USA", "place_city": "Arlington", "place_state": "VA",
        "contract_type": "IDIQ", 
        "award_date": datetime.date(2024, 4, 1), # FY2024 Q3 (config uses award_qtr_raw)
        "award_fiscal_year": 2024, # Explicit FY in sample
        "set_aside": "None", "release_date": datetime.date(2024, 4, 15),
        "naics": None, "row_index": 0, "extra_data": None # No specific extra fields in sample/config
    },
    {
        "native_id": "DOS-002", "agency": "FPT", "title": "Language Training",
        "description": "Language instruction services", "estimated_value": 500000.0, "est_value_unit": None,
        "place_country": "USA", "place_city": "Washington", "place_state": "DC",
        "contract_type": "BPA",
        # Award date logic: FY raw -> Date raw -> Qtr raw. Sample has Date raw and FY raw.
        # Date raw '11/01/2023' -> date(2023,11,1), year 2023. FY raw is 2024. Custom logic prioritizes FY raw for year.
        "award_date": datetime.date(2023, 11, 1), 
        "award_fiscal_year": 2024, 
        "set_aside": "Small Business", "release_date": datetime.date(2023, 7, 1),
        "naics": None, "row_index": 1, "extra_data": None
    },
]


# --- Fixtures ---
@pytest.fixture
def dos_full_test_config(): 
    conf = DOSConfig(source_name="DOS Integration Test")
    conf.data_processing_rules = DOSConfig().data_processing_rules # Use default full rules
    return conf

@pytest.fixture
def dos_unit_test_config(): 
    return DOSConfig(source_name="DOS Unit Test", data_processing_rules=DataProcessingRules(fields_for_id_hash=['native_id_raw']))

@pytest.fixture
def mock_dos_dependencies(mocker): # For unit tests
    mocker.patch.object(DOSForecastScraper, 'download_file_directly', return_value="/fake/dos.xlsx")
    mocker.patch.object(DOSForecastScraper, 'setup_browser', return_value=None)
    mocker.patch.object(DOSForecastScraper, 'cleanup_browser', return_value=None)

@pytest.fixture
def dos_scraper_unit_instance(dos_unit_test_config, mock_dos_dependencies, mocker): 
    mocker.patch.object(DOSForecastScraper, 'read_file_to_dataframe', return_value=pd.DataFrame())
    mocker.patch.object(DOSForecastScraper, 'prepare_and_load_data', return_value=0)
    scraper = DOSForecastScraper(config=dos_unit_test_config, debug_mode=True)
    scraper.logger = MagicMock()
    mock_playwright = MagicMock(); mock_api_context = MagicMock()
    mock_api_context.get.return_value = MagicMock(ok=True, body=lambda: b"filedata", headers={})
    mock_playwright.request.new_context.return_value = mock_api_context
    scraper.playwright = mock_playwright
    return scraper

@pytest.fixture
def dos_scraper_for_integration(dos_full_test_config, db_session, mocker):
    mocker.patch.object(DOSForecastScraper, 'setup_browser', return_value=None)
    mocker.patch.object(DOSForecastScraper, 'cleanup_browser', return_value=None)
    mocker.patch.object(DOSForecastScraper, 'download_file_directly', return_value=None)
    scraper = DOSForecastScraper(config=dos_full_test_config, debug_mode=True)
    scraper.logger = MagicMock()
    return scraper

# --- Basic Tests ---
def test_dos_scraper_instantiation(dos_unit_test_config):
    try: scraper = DOSForecastScraper(config=dos_unit_test_config); assert scraper.config == dos_unit_test_config
    except Exception as e: pytest.fail(f"DOSForecastScraper instantiation failed: {e}")

# --- Integration Test for _process_method with DB Validation ---
def test_dos_process_method_integration(dos_scraper_for_integration, dos_full_test_config, db_session):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    golden_file_path = os.path.join(current_dir, "..", "..", "fixtures", "golden_files", "dos_scraper", "dos_sample.xlsx")

    if not os.path.exists(golden_file_path):
        pytest.fail(f"Golden file not found: {golden_file_path}")

    expected_prospects = []
    for record_base in EXPECTED_DOS_PROSPECTS_BASE:
        record = record_base.copy()
        record["source_name"] = dos_full_test_config.source_name 
        record["id_hash"] = precalculate_dos_id_hash(record, dos_full_test_config)
        expected_prospects.append(record)
    
    # Call the method under test - this will now attempt real DB writes
    loaded_count = dos_scraper_for_integration._process_method(golden_file_path)

    assert loaded_count == len(expected_prospects)
    
    stmt = select(Prospect).where(Prospect.source_name == dos_full_test_config.source_name).order_by(Prospect.native_id, Prospect.row_index)
    retrieved_prospects = db_session.execute(stmt).scalars().all()

    assert len(retrieved_prospects) == len(expected_prospects)

    # Sort expected by native_id and row_index for comparison
    expected_prospects_sorted = sorted(expected_prospects, key=lambda x: (x['native_id'], x.get('row_index', -1)))

    for retrieved, expected in zip(retrieved_prospects, expected_prospects_sorted):
        assert retrieved.native_id == expected['native_id']
        assert retrieved.title == expected['title']
        assert retrieved.description == expected['description']
        assert retrieved.agency == expected['agency']
        assert pd.isna(retrieved.naics) if pd.isna(expected['naics']) else retrieved.naics == expected['naics'] # NAICS is None
        assert retrieved.estimated_value == expected['estimated_value']
        assert (retrieved.est_value_unit == expected['est_value_unit']) or (pd.isna(retrieved.est_value_unit) and pd.isna(expected['est_value_unit']))
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
        assert retrieved.row_index == expected['row_index']
        
        retrieved_extra = retrieved.extra_data if isinstance(retrieved.extra_data, dict) else {}
        expected_extra = expected.get('extra_data', {}) if isinstance(expected.get('extra_data'), dict) else {}
        assert retrieved_extra == expected_extra # Should be empty based on current DOS config for sample
        assert retrieved.loaded_at is not None
