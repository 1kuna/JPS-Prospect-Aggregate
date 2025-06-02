import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from typing import List, Dict, Any, Optional, Callable

from app.core.mixins.data_processing_mixin import DataProcessingMixin
from app.core.configs.base_config import BaseScraperConfig
from app.exceptions import ScraperError
from app.utils.scraper_utils import generate_id_hash 
from app.utils.parsing import fiscal_quarter_to_date, parse_value_range, split_place
# from app.database.crud import bulk_upsert_prospects # Mocked

# Mock the Prospect model for defining fields
class MockProspectModel:
    __table__ = MagicMock()
    _mock_fields = ['id', 'id_hash', 'source_name', 'title', 'description', 'agency', 
                    'release_date', 'award_date', 'award_fiscal_year',
                    'estimated_value', 'est_value_unit',
                    'place_city', 'place_state', 'place_country',
                    'extra_data', 'loaded_at']
    
    @classmethod
    def columns(cls):
        return [MagicMock(name=name) for name in cls._mock_fields]

# Test class incorporating DataProcessingMixin
class TestScraperWithDP(DataProcessingMixin): # Renamed for clarity
    def __init__(self, logger, config, db_session_mock=None):
        self.logger = logger
        self.config = config 
        self.db_session = db_session_mock
        self.source_name = config.source_name
        self._handle_and_raise_scraper_error = MagicMock(
            side_effect=lambda e, desc: (_ for _ in ()).throw(ScraperError(f"Mocked ScraperError: {desc} from {type(e).__name__} - {e}"))
        )
        self.custom_transform_add_col = MagicMock(side_effect=lambda df: df.assign(custom_added_col="test_value"))
        self.custom_transform_modify_col = MagicMock(side_effect=lambda df: df.assign(RawColA=df["RawColA"] + "_modified"))


@pytest.fixture
def mock_logger_dp(): return MagicMock()

@pytest.fixture
def base_config_dp(): return BaseScraperConfig(source_name="TestDataScraperDP") # Unique source name

@pytest.fixture
def scraper_instance_dp(mock_logger_dp, base_config_dp):
    return TestScraperWithDP(logger=mock_logger_dp, config=base_config_dp)

@pytest.fixture
def sample_csv_file(tmp_path):
    file = tmp_path / "sample.csv"; file.write_text("Header1,Header2\nVal1,Val2"); return file

@pytest.fixture
def sample_excel_file(tmp_path):
    file = tmp_path / "sample.xlsx"; pd.DataFrame({"ECol1": ["Ex1"]}).to_excel(file, index=False); return file

@pytest.fixture
def sample_html_file(tmp_path):
    file = tmp_path / "sample.html"
    html_content = """
    <html><body><table><tr><th>H1</th></tr><tr><td>D1</td></tr></table>
    <table id="table2"><tr><th>H2</th></tr><tr><td>D2</td></tr></table></body></html>
    """
    file.write_text(html_content); return file
    
@pytest.fixture
def sample_dataframe():
    return pd.DataFrame({
        "RawColA": ["Data1", "Data2"], "RawColB": [100, 200],
        "DateStringCol": ["2023-01-01", "02/15/2024"], "FiscalQuarterCol": ["FY2023Q1", "FY2024 Q3"],
        "ValueRangeCol": ["$1M - $5M", "100000"], "LocationCol": ["CityA, StateA", "CityB, StateB, CountryB"],
        "CountryOnlyCol": ["USA", None]
    })

# --- _determine_file_type Tests ---
# (Existing tests are good, can add more if many more extensions are supported)

# --- read_file_to_dataframe Tests ---
@patch('pandas.read_csv')
def test_read_csv_with_options(mock_read, scraper_instance_dp, sample_csv_file):
    options = {"sep": ";", "encoding": "latin1"}
    scraper_instance_dp.read_file_to_dataframe(str(sample_csv_file), file_type_hint='csv', read_options=options)
    expected_options = {'on_bad_lines': 'warn', "sep": ";", "encoding": "latin1"}
    mock_read.assert_called_once_with(str(sample_csv_file), **expected_options)

@patch('pandas.read_html')
def test_read_html_table_selection(mock_read_html, scraper_instance_dp, sample_html_file):
    df1 = pd.DataFrame({"H1": ["D1"]}); df2 = pd.DataFrame({"H2": ["D2"]})
    mock_read_html.return_value = [df1, df2]
    
    # Test default (first table)
    df_res = scraper_instance_dp.read_file_to_dataframe(str(sample_html_file), file_type_hint='html')
    pd.testing.assert_frame_equal(df_res, df1)
    scraper_instance_dp.logger.info.assert_any_call(f"Multiple tables (2) found in HTML file {str(sample_html_file)}. Using the first one by default.")

def test_read_file_unsupported_type_error(scraper_instance_dp, tmp_path):
    file = tmp_path / "sample.unsupported"; file.touch()
    with pytest.raises(ScraperError, match="Mocked ScraperError: value error during reading file"):
        scraper_instance_dp.read_file_to_dataframe(str(file)) # Error from _determine_file_type's ValueError

def test_read_file_pandas_value_error(scraper_instance_dp, sample_csv_file):
    with patch('pandas.read_csv', side_effect=ValueError("Bad CSV format")):
        with pytest.raises(ScraperError, match="Mocked ScraperError: value error during reading file"):
            scraper_instance_dp.read_file_to_dataframe(str(sample_csv_file), file_type_hint='csv')

# --- transform_dataframe Tests ---
class MockTransformConfig: # More flexible config for tests
    def __init__(self, **kwargs):
        defaults = {
            "dropna_how_all": True, "column_rename_map": None, "date_column_configs": [],
            "value_column_configs": [], "place_column_configs": [], "custom_transform_functions": [],
            "default_country": "USA"
        }
        defaults.update(kwargs)
        for key, value in defaults.items():
            setattr(self, key, value)

def test_transform_df_date_parsing_missing_col(scraper_instance_dp, sample_dataframe):
    cfg = MockTransformConfig(date_column_configs=[{'column': 'NonExistentDateCol', 'target_column': 'parsed_date'}])
    df_copy = sample_dataframe.copy()
    transformed_df = scraper_instance_dp.transform_dataframe(df_copy, cfg)
    scraper_instance_dp.logger.warning.assert_any_call("Date column 'NonExistentDateCol' not found for parsing.")
    assert "parsed_date" not in transformed_df.columns # Target col shouldn't be created if source missing

def test_transform_df_custom_functions_called(scraper_instance_dp, sample_dataframe):
    cfg = MockTransformConfig(custom_transform_functions=["custom_transform_add_col", "custom_transform_modify_col"])
    df_copy = sample_dataframe.copy()
    transformed_df = scraper_instance_dp.transform_dataframe(df_copy, cfg)
    scraper_instance_dp.custom_transform_add_col.assert_called_once()
    scraper_instance_dp.custom_transform_modify_col.assert_called_once()
    assert "custom_added_col" in transformed_df.columns
    assert transformed_df.loc[0, "RawColA"] == "Data1_modified" # Check modification

@patch('app.core.mixins.data_processing_mixin.fiscal_quarter_to_date', return_value=(pd.Timestamp("2023-10-01"), 2024))
def test_transform_df_declarative_fiscal_quarter(mock_fq_parser, scraper_instance_dp, sample_dataframe):
    cfg = MockTransformConfig(date_column_configs=[
        {'column': 'FiscalQuarterCol', 'parse_type': 'fiscal_quarter', 'target_date_col': 'fq_date', 'target_fy_col': 'fq_fy'}
    ])
    df_copy = sample_dataframe.copy()
    transformed_df = scraper_instance_dp.transform_dataframe(df_copy, cfg)
    assert transformed_df.loc[0, 'fq_date'] == pd.Timestamp("2023-10-01").date()
    assert transformed_df.loc[0, 'fq_fy'] == 2024

@patch('app.core.mixins.data_processing_mixin.parse_value_range', return_value=(1000000.0, "M USD"))
def test_transform_df_declarative_value_parse(mock_val_parser, scraper_instance_dp, sample_dataframe):
    cfg = MockTransformConfig(value_column_configs=[
        {'column': 'ValueRangeCol', 'target_value_col': 'parsed_value', 'target_unit_col': 'parsed_unit'}
    ])
    df_copy = sample_dataframe.copy()
    transformed_df = scraper_instance_dp.transform_dataframe(df_copy, cfg)
    assert transformed_df.loc[0, 'parsed_value'] == 1000000.0
    assert transformed_df.loc[0, 'parsed_unit'] == "M USD"


# --- prepare_and_load_data Tests ---
@patch('app.core.mixins.data_processing_mixin.bulk_upsert_prospects')
@patch('app.core.mixins.data_processing_mixin.Prospect', new=MockProspectModel)
def test_prepare_load_empty_df(mock_bulk_upsert, scraper_instance_dp):
    cfg = MockTransformConfig() # Minimal config
    empty_df = pd.DataFrame()
    count = scraper_instance_dp.prepare_and_load_data(empty_df, cfg)
    assert count == 0
    mock_bulk_upsert.assert_not_called()

@patch('app.core.mixins.data_processing_mixin.bulk_upsert_prospects')
@patch('app.core.mixins.data_processing_mixin.Prospect', new=MockProspectModel)
def test_prepare_load_missing_required_fields(mock_bulk_upsert, scraper_instance_dp, sample_dataframe):
    # sample_dataframe has "RawColA", "RawColB"
    # After db_rename_map, assume "RawColA" -> "title", "RawColB" -> "value_field"
    class MockLoadCfg(MockTransformConfig): # Inherit to get defaults
        fields_for_id_hash = ["RawColA"] # Must be present before db_rename_map
        db_column_rename_map = {"RawColA": "title", "RawColB": "value_field"}
        required_fields_for_load = ["title", "non_existent_req_field"] # One exists, one doesn't after map
    
    cfg = MockLoadCfg()
    df_copy = sample_dataframe.copy()
    # Simulate that 'title' (from RawColA) is fine, but 'non_existent_req_field' will cause rows to be dropped
    # This test is tricky because required_fields_for_load applies to *final* model field names,
    # but dropna is on the DataFrame *before* to_dict for model instantiation.
    # The current prepare_and_load_data applies dropna *before* rename for DB.
    # This test will assume required_fields_for_load are columns that should exist with non-NA values *before* db_column_rename_map.
    cfg.required_fields_for_load = ["RawColA", "NonExistentColInDf"] # Test current logic
    
    count = scraper_instance_dp.prepare_and_load_data(df_copy, cfg)
    assert count == 0 # All rows dropped as "NonExistentColInDf" is missing
    scraper_instance_dp.logger.info.assert_any_call("Filtered 2 rows due to missing required fields: ['NonExistentColInDf']. 0 rows remaining.")
    mock_bulk_upsert.assert_not_called()

@patch('app.core.mixins.data_processing_mixin.bulk_upsert_prospects', side_effect=Exception("DB Write Error"))
@patch('app.core.mixins.data_processing_mixin.Prospect', new=MockProspectModel)
def test_prepare_load_db_error(mock_bulk_upsert_err, scraper_instance_dp, sample_dataframe):
    class MockLoadCfg(MockTransformConfig):
        fields_for_id_hash = ["RawColA"]
        db_column_rename_map = {"RawColA": "title"}
    cfg = MockLoadCfg()
    df_copy = sample_dataframe.copy()

    with pytest.raises(ScraperError, match="Mocked ScraperError: preparing and loading data for source: TestDataScraperDP from Exception - DB Write Error"):
        scraper_instance_dp.prepare_and_load_data(df_copy, cfg)
    scraper_instance_dp._handle_and_raise_scraper_error.assert_called_once()

@patch('app.core.mixins.data_processing_mixin.bulk_upsert_prospects')
@patch('app.core.mixins.data_processing_mixin.Prospect', new=MockProspectModel)
def test_prepare_load_extra_data_generation(mock_bulk_upsert, scraper_instance_dp):
    df = pd.DataFrame({
        "title_col": ["Title1"], # Will map to Prospect.title
        "unmapped_col1": ["ExtraValue1"],
        "unmapped_col2": [123.45]
    })
    class MockLoadCfg(MockTransformConfig):
        fields_for_id_hash = ["title_col"]
        db_column_rename_map = {"title_col": "title"}
        # prospect_model_fields will be dynamically generated from MockProspectModel
    cfg = MockLoadCfg()
    
    scraper_instance_dp.prepare_and_load_data(df, cfg)
    
    mock_bulk_upsert.assert_called_once()
    # Get the data passed to bulk_upsert_prospects
    # Assuming bulk_upsert_prospects is called with prospects_data as a positional or keyword arg
    call_args = mock_bulk_upsert.call_args
    prospects_data = call_args.kwargs.get('prospects_data', call_args.args[0])
    
    assert len(prospects_data) == 1
    assert prospects_data[0]['title'] == "Title1"
    assert 'extra_data' in prospects_data[0]
    assert prospects_data[0]['extra_data'] == {"unmapped_col1": "ExtraValue1", "unmapped_col2": 123.45}

```
