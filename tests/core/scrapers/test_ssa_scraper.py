import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from typing import Optional, Dict, Any # Added Dict, Any
import datetime 
import os 
import hashlib # For id_hash pre-calculation

from app.core.scrapers.ssa_scraper import SsaScraper
from app.core.scrapers.configs.ssa_config import SSAConfig, DataProcessingRules
from app.exceptions import ScraperError
from app.config import active_config 
from app.models import Prospect 
from app.utils.scraper_utils import generate_id_hash # For id_hash pre-calculation
from sqlalchemy import select # For DB query

# --- Helper for ID Hash ---
def precalculate_ssa_id_hash(record: Dict, config: SSAConfig) -> str:
    """Pre-calculates id_hash for an expected record based on SSA config."""
    # fields_for_id_hash in SSAConfig:
    # ['native_id_raw', 'naics_raw', 'title_final', 
    #  'description_final', 'agency_raw', 'place_city', 'place_state']
    # The `record` dict passed to this helper should have keys that will become these intermediate columns.
    
    # Map expected final data keys to the intermediate names used for hashing
    data_for_hash = {
        'native_id_raw': str(record.get('native_id', '')),
        'naics_raw': str(record.get('naics', '')),
        'title_final': str(record.get('title', '')),
        'description_final': str(record.get('description', '')),
        'agency_raw': str(record.get('agency', '')),
        'place_city': str(record.get('place_city', '')),
        'place_state': str(record.get('place_state', ''))
    }
    temp_df = pd.DataFrame([data_for_hash])
    id_hash_series = generate_id_hash(temp_df, config.data_processing_rules.fields_for_id_hash, prefix=config.source_name)
    return id_hash_series[0]

# --- Expected Data ---
EXPECTED_SSA_PROSPECTS_BASE = [
    {
        "native_id": "SSA-001", "agency": "HQ", "title": "IT Support Services",
        "description": "IT Support Services", "estimated_value": 1000000.0,
        "est_value_unit": "$1M-$5M (Per FY)", # Custom transform adds (Per FY)
        "award_date": datetime.date(2023, 10, 15), "award_fiscal_year": 2023, # Year of award_date
        "contract_type": "FFP", "naics": "541511", "set_aside": "Small Business",
        "place_city": "Baltimore", "place_state": "MD", "place_country": "USA",
        "release_date": None, # Custom transform sets to None
        "extra_data": {'requirement_type_extra': 'Services'}
    },
    {
        "native_id": "SSA-002", "agency": "REGION 1", "title": "Janitorial Services",
        "description": "Janitorial Services", "estimated_value": 25000.0,
        "est_value_unit": "$25k-$100k (Per FY)",
        # Award date from "Q1 FY2024" -> fiscal_quarter_to_date("Q1 FY2024") -> (2023-10-01, 2024)
        "award_date": datetime.date(2023, 10, 1), "award_fiscal_year": 2024,
        "contract_type": "FFP", "naics": "561720", "set_aside": "8(a)",
        "place_city": "Boston", "place_state": "MA", "place_country": "USA",
        "release_date": None,
        "extra_data": {'requirement_type_extra': 'Services'}
    },
]


# --- Fixtures ---
@pytest.fixture
def ssa_full_test_config(): 
    """Provides an SSAConfig instance with full data_processing_rules for integration tests."""
    # This config must align with how ssa_sample.xlsx is processed into EXPECTED_SSA_PROSPECTS_BASE
    conf = SSAConfig( 
        source_name="SSA Integration Test", 
        base_url=active_config.SSA_CONTRACT_FORECAST_URL or "http://fake-ssa-url.com",
        data_processing_rules=SSAConfig().data_processing_rules 
    )
    # Ensure the fields_for_id_hash matches what precalculate_ssa_id_hash expects conceptually
    # Default from SSAConfig: ['native_id_raw', 'naics_raw', 'title_final', 'description_final', 'agency_raw', 'place_city', 'place_state']
    return conf

@pytest.fixture
def ssa_unit_test_config(): 
    """Provides a simplified SSAConfig instance for basic unit tests."""
    # This config is used for unit tests not focused on deep data processing.
    # It should still be valid.
    return SSAConfig( 
        source_name="SSA Unit Test",
        data_processing_rules=DataProcessingRules(
            custom_transform_functions=["_custom_ssa_transforms"], 
            raw_column_rename_map={ 
                'APP #': 'native_id_raw', 'DESCRIPTION': 'description_raw',
                'EST COST PER FY': 'estimated_value_raw', 'PLANNED AWARD DATE': 'award_date_raw',
                'SITE Type': 'agency_raw', 'NAICS': 'naics_raw', # Added for hash fields
                'PLACE OF PERFORMANCE': 'place_raw', # Added for hash fields
            },
            db_column_rename_map={ 
                'native_id_raw': 'native_id', 'title_final': 'title', 'description_final': 'description',
                'est_value_unit_final': 'est_value_unit', 'agency_raw': 'agency',
                'naics_raw': 'naics', 'place_city': 'place_city', 'place_state': 'place_state',
                # ... other fields if tested in simple unit tests ...
            },
            fields_for_id_hash=['native_id_raw', 'naics_raw', 'title_final', 'description_final', 'agency_raw', 'place_city', 'place_state']
        )
    )

@pytest.fixture
def mock_ssa_dependencies(mocker):
    mocker.patch.object(SsaScraper, 'navigate_to_url', return_value=None)
    mocker.patch.object(SsaScraper, 'download_file_directly', return_value="/fake/path/to/downloaded.xlsx")
    mocker.patch.object(SsaScraper, 'setup_browser', return_value=None)
    mocker.patch.object(SsaScraper, 'cleanup_browser', return_value=None)
    mocker.patch.object(SsaScraper, '_save_error_screenshot', return_value=None)
    mocker.patch.object(SsaScraper, '_save_error_html', return_value=None)

@pytest.fixture
def ssa_scraper_unit_instance(ssa_unit_test_config, mock_ssa_dependencies, mocker): 
    mocker.patch.object(SsaScraper, 'read_file_to_dataframe', return_value=pd.DataFrame({'test': ['data']}))
    mocker.patch.object(SsaScraper, 'prepare_and_load_data', return_value=1) # Mock for unit tests
    scraper = SsaScraper(config=ssa_unit_test_config, debug_mode=True)
    scraper.page = MagicMock(); scraper.page.urljoin = lambda url: "http://fake-ssa-url.com/" + url.lstrip('/') 
    scraper.logger = MagicMock()
    mock_playwright = MagicMock(); mock_api_context = MagicMock()
    mock_api_context.get.return_value = MagicMock(ok=True, body=lambda: b"filedata", headers={})
    mock_playwright.request.new_context.return_value = mock_api_context
    scraper.playwright = mock_playwright
    return scraper

@pytest.fixture
def ssa_scraper_for_integration(ssa_full_test_config, db_session, mocker):
    mocker.patch.object(SsaScraper, 'setup_browser', return_value=None)
    mocker.patch.object(SsaScraper, 'cleanup_browser', return_value=None)
    mocker.patch.object(SsaScraper, 'navigate_to_url', return_value=None)
    mocker.patch.object(SsaScraper, 'download_file_directly', return_value=None)
    scraper = SsaScraper(config=ssa_full_test_config, debug_mode=True)
    scraper.logger = MagicMock()
    return scraper

# --- Basic Tests ---
def test_ssa_scraper_instantiation(ssa_unit_test_config):
    try: scraper = SsaScraper(config=ssa_unit_test_config); assert scraper.config == ssa_unit_test_config
    except Exception as e: pytest.fail(f"SsaScraper instantiation failed: {e}")

# --- Method Tests (Unit Tests) ---
def test_ssa_find_excel_link_success(ssa_scraper_unit_instance): # Renamed fixture
    mock_link = MagicMock(); mock_link.get_attribute.return_value = "file.xlsx"
    ssa_scraper_unit_instance.page.query_selector_all.return_value = [mock_link]
    assert ssa_scraper_unit_instance._find_excel_link() is not None

# --- Integration Test for _process_method with DB Validation ---
def test_ssa_process_method_integration(ssa_scraper_for_integration, ssa_full_test_config, db_session):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    golden_file_path = os.path.join(current_dir, "..", "..", "fixtures", "golden_files", "ssa_scraper", "ssa_sample.xlsx")

    if not os.path.exists(golden_file_path):
        pytest.fail(f"Golden file not found: {golden_file_path}")

    # Prepare expected data
    expected_prospects = []
    for record_base in EXPECTED_SSA_PROSPECTS_BASE:
        record = record_base.copy()
        record["source_name"] = ssa_full_test_config.source_name 
        record["id_hash"] = precalculate_ssa_id_hash(record, ssa_full_test_config)
        expected_prospects.append(record)
    
    # No mocking of bulk_upsert_prospects - let it write to the test DB session
    loaded_count = ssa_scraper_for_integration._process_method(golden_file_path)

    assert loaded_count == len(expected_prospects)
    
    stmt = select(Prospect).where(Prospect.source_name == ssa_full_test_config.source_name).order_by(Prospect.native_id)
    retrieved_prospects = db_session.execute(stmt).scalars().all()

    assert len(retrieved_prospects) == len(expected_prospects)

    for retrieved, expected in zip(retrieved_prospects, sorted(expected_prospects, key=lambda x: x['native_id'])):
        assert retrieved.native_id == expected['native_id']
        assert retrieved.title == expected['title']
        assert retrieved.description == expected['description']
        assert retrieved.agency == expected['agency']
        assert retrieved.naics == expected['naics'] # Ensure NAICS is string in golden/expected
        assert retrieved.estimated_value == expected['estimated_value']
        assert retrieved.est_value_unit == expected['est_value_unit']
        assert retrieved.release_date == expected['release_date'] # None
        assert retrieved.award_date == expected['award_date']
        assert retrieved.award_fiscal_year == expected['award_fiscal_year']
        assert retrieved.place_city == expected['place_city']
        assert retrieved.place_state == expected['place_state']
        assert retrieved.place_country == expected['place_country']
        assert retrieved.contract_type == expected['contract_type']
        assert retrieved.set_aside == expected['set_aside']
        assert retrieved.id_hash == expected['id_hash']
        assert retrieved.source_name == expected['source_name']
        # Compare extra_data carefully, could be dict or None
        retrieved_extra = retrieved.extra_data if isinstance(retrieved.extra_data, dict) else {}
        expected_extra = expected.get('extra_data', {}) if isinstance(expected.get('extra_data'), dict) else {}
        assert retrieved_extra == expected_extra
        assert retrieved.loaded_at is not None
```
