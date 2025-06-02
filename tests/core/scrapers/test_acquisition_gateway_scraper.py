import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import datetime # For date comparisons in integration test
import os # For path joining
import hashlib # For id_hash pre-calculation

from app.core.scrapers.acquisition_gateway_scraper import AcquisitionGatewayScraper
from app.core.scrapers.configs.acquisition_gateway_config import AcquisitionGatewayConfig, DataProcessingRules
from app.exceptions import ScraperError
from app.config import active_config 
from app.models import Prospect # For DB query in integration test
from app.utils.scraper_utils import generate_id_hash # For id_hash pre-calculation
from sqlalchemy import select # For DB query

# --- Helper for ID Hash ---
def precalculate_ags_id_hash(record: Dict, config: AcquisitionGatewayConfig) -> str:
    """Pre-calculates id_hash for an expected record based on AGS config."""
    # Data needs to be in a DataFrame for generate_id_hash utility
    # The fields_for_id_hash in config refers to *intermediate* column names
    # (after raw_rename_map, before db_column_rename_map)
    # We need to map our expected final record keys back to these intermediate names.
    
    # Create a reverse map from db_column_rename_map values (model fields) to keys (intermediate df fields)
    # Or, more simply, ensure the input `record` to this helper has keys matching `fields_for_id_hash`
    # The `fields_for_id_hash` in `AcquisitionGatewayConfig` are:
    # ['native_id_intermediate', 'naics_intermediate', 'title_intermediate', 'description_intermediate']
    
    # The `record` dict passed here will have keys like 'native_id', 'naics', etc. (model field names)
    # We need to construct a dictionary with keys that match `fields_for_id_hash`
    # by finding which raw/intermediate name maps to which model field name.
    
    # Example: if db_map is {'native_id_intermediate': 'native_id'}, and fields_for_id_hash is ['native_id_intermediate']
    # and record has 'native_id', we need to use record['native_id'] for 'native_id_intermediate'.

    data_for_hash = {}
    raw_map = config.data_processing_rules.raw_column_rename_map
    # This is complex because raw_map is source->intermediate, db_map is intermediate->final.
    # fields_for_id_hash uses intermediate names.
    # Let's assume the `record` keys can be directly used if they match the *concept* of the intermediate names.
    # For AGS, fields_for_id_hash are:
    # native_id_intermediate (from 'Listing ID') -> maps to 'native_id'
    # naics_intermediate (from 'NAICS Code') -> maps to 'naics'
    # title_intermediate (from 'Title') -> maps to 'title'
    # description_intermediate (from 'Body' or 'Summary') -> maps to 'description'

    # So, the `record` keys for this helper should align with these concepts.
    df_record_data = {
        'native_id_intermediate': str(record.get('native_id', '')), # Ensure string for hashing
        'naics_intermediate': str(record.get('naics', '')),
        'title_intermediate': str(record.get('title', '')),
        'description_intermediate': str(record.get('description', ''))
    }
    temp_df = pd.DataFrame([df_record_data])
    # The prefix used in prepare_and_load_data is self.config.source_name
    id_hash_series = generate_id_hash(temp_df, config.data_processing_rules.fields_for_id_hash, prefix=config.source_name)
    return id_hash_series[0]


# --- Expected Data ---
# Define this at module level or inside the test function if it needs fixtures like ags_test_config
# For now, define globally and pass config to helper.
# Note: `source_name` will be from the config used in the test.
# `id_hash` needs to be calculated based on the specific config's `fields_for_id_hash` and `source_name`.

EXPECTED_AGS_PROSPECTS_BASE = [
    {
        "native_id": "123", "title": "Test Title 1", "description": "Test Body 1",
        "naics": "541511", "estimated_value": 1000000.0, 
        "release_date": datetime.date(2023, 10, 1), "award_date": datetime.date(2024, 9, 30),
        "award_fiscal_year": 2024, "agency": "Test Org", "place_city": "Arlington",
        "place_state": "VA", "place_country": "USA", "contract_type": "FFP",
        "set_aside": None, # "None" string in CSV becomes None after processing if not mapped otherwise
        "extra_data": None # Assuming no unmapped columns from the sample CSV based on config
    },
    {
        "native_id": "456", "title": "Test Title 2", "description": "Test Body 2",
        "naics": "541512", "estimated_value": 250000.0,
        "release_date": None, # Blank in CSV
        "award_date": datetime.date(2025, 9, 30), "award_fiscal_year": 2025,
        "agency": "Test Org", "place_city": "Remote", "place_state": None, # Blank in CSV
        "place_country": "USA", "contract_type": "T&M", "set_aside": "Small Business",
        "extra_data": None
    },
]

# --- Fixtures ---
@pytest.fixture
def ags_full_test_config(): # Renamed from ags_test_config for clarity
    """Provides an AcquisitionGatewayConfig instance with full data_processing_rules for integration tests."""
    # This must match the actual config used by the scraper for processing the golden file.
    # DataProcessingRules from the actual config file is used by default.
    return AcquisitionGatewayConfig(source_name="Acquisition Gateway Integration Test")


@pytest.fixture
def mock_ags_dependencies(mocker): # Kept for unit tests that might still need it
    mocker.patch.object(AcquisitionGatewayScraper, 'navigate_to_url', return_value=None)
    # ... (other mocks for unit tests not focused on processing) ...

@pytest.fixture
def ags_scraper_instance_mocked_for_unit_tests(ags_full_test_config, mock_ags_dependencies, mocker):
    # This fixture is for unit tests where data processing IS mocked
    mocker.patch.object(AcquisitionGatewayScraper, 'read_file_to_dataframe', return_value=pd.DataFrame({'test': ['data']}))
    mocker.patch.object(AcquisitionGatewayScraper, 'transform_dataframe', side_effect=lambda df, config_params: df)
    mocker.patch.object(AcquisitionGatewayScraper, 'prepare_and_load_data', return_value=1)
    # ... (rest of the setup from original ags_scraper_instance) ...
    mock_page = MagicMock(); mock_page.expect_download.return_value.__enter__.return_value.value = MagicMock(path=lambda: "/tmp/fake.csv")
    scraper = AcquisitionGatewayScraper(config=ags_full_test_config, debug_mode=True) # Use full config
    scraper.page = mock_page; scraper.logger = MagicMock(); scraper._last_download_path = None 
    return scraper

@pytest.fixture
def ags_scraper_for_integration(ags_full_test_config, db_session, mocker): 
    mocker.patch.object(AcquisitionGatewayScraper, 'setup_browser', return_value=None)
    mocker.patch.object(AcquisitionGatewayScraper, 'cleanup_browser', return_value=None)
    mocker.patch.object(AcquisitionGatewayScraper, 'navigate_to_url', return_value=None)
    mocker.patch.object(AcquisitionGatewayScraper, 'click_element', return_value=None)
    mocker.patch.object(AcquisitionGatewayScraper, '_handle_download_event', return_value=None)
    scraper = AcquisitionGatewayScraper(config=ags_full_test_config, debug_mode=True)
    scraper.logger = MagicMock()
    # BaseScraper's __init__ now takes config. ScraperService would pass db_session to run method or similar.
    # DataProcessingMixin.prepare_and_load_data calls bulk_upsert_prospects, which uses the global db.session.
    # The db_session fixture manages this global session's transaction for the test.
    return scraper


# --- Basic Tests (using unit_test_config if exists or full_test_config) ---
def test_ags_scraper_instantiation(ags_full_test_config): # Test with the full config
    try:
        scraper = AcquisitionGatewayScraper(config=ags_full_test_config)
        assert scraper.config == ags_full_test_config
    except Exception as e:
        pytest.fail(f"AcquisitionGatewayScraper instantiation failed: {e}")

# --- Method Tests (Unit) ---
def test_ags_setup_method(ags_scraper_instance_mocked_for_unit_tests, ags_full_test_config):
    ags_scraper_instance_mocked_for_unit_tests.config = ags_full_test_config # Ensure it uses the right config for this test
    ags_scraper_instance_mocked_for_unit_tests._setup_method()
    ags_scraper_instance_mocked_for_unit_tests.navigate_to_url.assert_called_once_with(ags_full_test_config.base_url)

# --- Main scrape method orchestration (Unit Test) ---
def test_ags_scrape_method_calls_sub_methods(ags_scraper_instance_mocked_for_unit_tests, mocker):
    mocker.patch.object(ags_scraper_instance_mocked_for_unit_tests, '_setup_method', return_value=None)
    mocker.patch.object(ags_scraper_instance_mocked_for_unit_tests, '_extract_method', return_value="/fake/file.csv")
    mocker.patch.object(ags_scraper_instance_mocked_for_unit_tests, '_process_method', return_value=5)
    result = ags_scraper_instance_mocked_for_unit_tests.scrape()
    assert result['success'] is True and result['data'] == 5

# --- Integration Test for _process_method with DB Validation ---
def test_ags_process_method_integration(ags_scraper_for_integration, db_session, ags_full_test_config):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    golden_file_path = os.path.join(current_dir, "..", "..", "fixtures", "golden_files", "acquisition_gateway", "acquisition_gateway_sample.csv")

    if not os.path.exists(golden_file_path):
        pytest.fail(f"Golden file not found: {golden_file_path}")

    # Prepare expected data with correct id_hash and source_name
    expected_prospects = []
    for record_base in EXPECTED_AGS_PROSPECTS_BASE:
        record = record_base.copy()
        record["source_name"] = ags_full_test_config.source_name 
        # The record keys for precalculate_ags_id_hash should match the concepts used in fields_for_id_hash
        # For AGS: native_id, naics, title, description
        record_for_hash_calc = {
            'native_id': record.get('native_id'), 'naics': record.get('naics'),
            'title': record.get('title'), 'description': record.get('description')
        }
        record["id_hash"] = precalculate_ags_id_hash(record_for_hash_calc, ags_full_test_config)
        expected_prospects.append(record)

    # Call the method under test - this will now attempt real DB writes
    loaded_count = ags_scraper_for_integration._process_method(golden_file_path)

    assert loaded_count == len(expected_prospects)
    
    # Query the database
    stmt = select(Prospect).where(Prospect.source_name == ags_full_test_config.source_name).order_by(Prospect.native_id)
    retrieved_prospects = db_session.execute(stmt).scalars().all()

    assert len(retrieved_prospects) == len(expected_prospects)

    for retrieved, expected in zip(retrieved_prospects, sorted(expected_prospects, key=lambda x: x['native_id'])):
        assert retrieved.native_id == expected['native_id']
        assert retrieved.title == expected['title']
        assert retrieved.description == expected['description']
        assert retrieved.agency == expected['agency']
        assert retrieved.naics == expected['naics']
        assert retrieved.estimated_value == expected['estimated_value']
        assert retrieved.release_date == expected['release_date']
        assert retrieved.award_date == expected['award_date']
        assert retrieved.award_fiscal_year == expected['award_fiscal_year']
        assert retrieved.place_city == expected['place_city']
        assert retrieved.place_state == expected['place_state']
        assert retrieved.place_country == expected['place_country']
        assert retrieved.contract_type == expected['contract_type']
        # Handle 'set_aside' potentially being None vs "None" string if config changes
        assert (retrieved.set_aside == expected['set_aside']) or \
               (pd.isna(retrieved.set_aside) and pd.isna(expected['set_aside'])) or \
               (retrieved.set_aside == "None" and expected['set_aside'] is None)

        assert retrieved.id_hash == expected['id_hash']
        assert retrieved.source_name == expected['source_name']
        # For extra_data, assuming None for this sample based on current AGS config and sample data
        assert retrieved.extra_data == expected.get('extra_data', None) # Handles if key is missing too
        assert retrieved.loaded_at is not None # Should be set by the database default
```
