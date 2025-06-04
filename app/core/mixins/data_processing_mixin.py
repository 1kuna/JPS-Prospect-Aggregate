import os
import pandas as pd
from typing import Optional, Dict, Any, List, Callable

from app.exceptions import ScraperError
from app.utils.logger import logger # Assuming logger is accessible via self.logger
from app.utils.parsing import fiscal_quarter_to_date, parse_value_range, split_place
from app.utils.scraper_utils import generate_id_hash 
from app.database.crud import bulk_upsert_prospects
from app.models import Prospect # For getting model fields
from app.config import active_config # For preserve_ai_data configuration


class DataProcessingMixin:
    """
    Mixin class for common data processing tasks after file download.
    Relies on attributes from BaseScraper:
    - self.logger
    - self.config (instance of BaseScraperConfig or subclass, providing source_name)
    - self._handle_and_raise_scraper_error (for standardized error handling)
    - self.db_session (SQLAlchemy session, if needed directly, though bulk_upsert_prospects handles it)
    """

    def _determine_file_type(self, file_path: str, file_type_hint: Optional[str] = None) -> str:
        """Determines the file type from hint or extension."""
        if not hasattr(self, 'logger'): # Basic check, should be present
            raise AttributeError("DataProcessingMixin requires self.logger.")

        if file_type_hint:
            self.logger.debug(f"File type hint provided: '{file_type_hint}' for {file_path}")
            return file_type_hint.lower()
        
        _, ext = os.path.splitext(file_path)
        ext = ext.lower().strip('.')
        
        if ext in ['csv', 'txt']: return 'csv'
        elif ext in ['xls', 'xlsx', 'xlsm']: return 'excel'
        elif ext in ['html', 'htm']: return 'html'
        else:
            # Not using _handle_and_raise_scraper_error here as it's a ValueError for bad input, not a runtime scraping error.
            self.logger.error(f"Could not determine file type for: {file_path} (extension: '{ext}')")
            raise ValueError(f"Unsupported or undetermined file type for: {file_path}")

    def read_file_to_dataframe(self, 
                               file_path: str, 
                               file_type_hint: Optional[str] = None, 
                               read_options: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Reads a file into a pandas DataFrame based on determined file type."""
        if not all(hasattr(self, attr) for attr in ['logger', '_handle_and_raise_scraper_error']):
            raise AttributeError("DataProcessingMixin.read_file_to_dataframe is missing required attributes/methods.")

        operation_desc = f"reading file '{file_path}' to DataFrame"
        self.logger.info(f"Starting {operation_desc}")
        effective_read_options = read_options or {}
        
        try:
            file_type = self._determine_file_type(file_path, file_type_hint)
            df = None

            if file_type == 'csv':
                csv_defaults = {'on_bad_lines': 'warn'}; csv_defaults.update(effective_read_options)
                df = pd.read_csv(file_path, **csv_defaults)
            elif file_type == 'excel':
                df = pd.read_excel(file_path, **effective_read_options)
            elif file_type == 'html':
                html_tables = pd.read_html(file_path, **effective_read_options)
                if not html_tables: self.logger.warning(f"No tables found in HTML file: {file_path}"); df = pd.DataFrame()
                else:
                    if len(html_tables) > 1: self.logger.info(f"Multiple tables ({len(html_tables)}) found in {file_path}. Using first one.")
                    df = html_tables[0]
            
            if df is None: raise ScraperError(f"DataFrame remained None after attempting to read {file_path} as {file_type}.")
            if df.empty: self.logger.warning(f"DataFrame is empty after reading file: {file_path}")
            else: self.logger.info(f"Successfully read {len(df)} rows from {file_path} as {file_type}.")
            return df

        except FileNotFoundError as e:
            self._handle_and_raise_scraper_error(e, f"file not found during {operation_desc}")
        except pd.errors.EmptyDataError as e: # This might not be an "error" but expected for some sources
            self.logger.warning(f"No data or empty file (pandas EmptyDataError) for '{file_path}'. Returning empty DataFrame.")
            return pd.DataFrame()
        except ValueError as e: # e.g. bad CSV, bad Excel options, or _determine_file_type error
            self._handle_and_raise_scraper_error(e, f"value error during {operation_desc}")
        except ImportError as e: 
            self._handle_and_raise_scraper_error(e, f"missing parser for {operation_desc}")
        except Exception as e: 
            self._handle_and_raise_scraper_error(e, f"unexpected error during {operation_desc}")
        return pd.DataFrame() # Should be unreachable


    def transform_dataframe(self, df: pd.DataFrame, config_params: Any) -> pd.DataFrame:
        """Applies a series of transformations to the DataFrame based on config_params."""
        if not all(hasattr(self, attr) for attr in ['logger', '_handle_and_raise_scraper_error']):
            raise AttributeError("DataProcessingMixin.transform_dataframe is missing required attributes/methods.")
        
        operation_desc = "transforming DataFrame"
        self.logger.info(f"Starting {operation_desc}")
        if df.empty: self.logger.info("DataFrame is empty. No transformations applied."); return df

        try:
            if getattr(config_params, 'dropna_how_all', True):
                 df.dropna(how='all', inplace=True); self.logger.debug(f"Shape after dropna(how='all'): {df.shape}")

            # Custom Transformations (run first as per previous decision)
            custom_funcs = getattr(config_params, 'custom_transform_functions', [])
            if custom_funcs:
                for func_spec in custom_funcs:
                    func_name = func_spec if isinstance(func_spec, str) else (getattr(func_spec, '__name__', 'unknown_callable'))
                    self.logger.info(f"Applying custom transformation: {func_name}")
                    if isinstance(func_spec, str):
                        if hasattr(self, func_spec): df = getattr(self, func_spec)(df.copy()) # Pass copy to be safe
                        else: self.logger.warning(f"Custom transform method '{func_spec}' not found on scraper.")
                    elif isinstance(func_spec, Callable): df = func_spec(df.copy())
                    else: self.logger.warning(f"Invalid custom_transform_function type: {type(func_spec)}.")
            
            rename_map = getattr(config_params, 'raw_column_rename_map', None)
            if rename_map: 
                df.rename(columns=rename_map, inplace=True, errors='ignore')
                self.logger.debug(f"Cols after raw rename: {df.columns.tolist()}")

            date_configs = getattr(config_params, 'date_column_configs', [])
            for conf in date_configs:
                col, target, p_type, fmt, store_date = conf['column'], conf.get('target_column', conf['column']), conf.get('parse_type', 'datetime'), conf.get('format'), conf.get('store_as_date', True)
                if col in df.columns:
                    if p_type == 'fiscal_quarter':
                        parsed = df[col].apply(lambda x: fiscal_quarter_to_date(x) if pd.notna(x) else (None, None))
                        df[conf.get('target_date_col') or f"{target}_date"] = parsed.apply(lambda x: x[0].date() if x[0] and x[0] is not None else None)
                        df[conf.get('target_fy_col') or f"{target}_fy"] = parsed.apply(lambda x: x[1] if x[1] is not None else None).astype('Int64')
                    else:
                        df[target] = pd.to_datetime(df[col], errors='coerce', format=fmt)
                        if store_date: df[target] = df[target].dt.date
                else: self.logger.warning(f"Date column '{col}' not found for parsing.")
            
            val_configs = getattr(config_params, 'value_column_configs', [])
            for conf in val_configs:
                col, target_val, target_unit = conf['column'], conf.get('target_value_col', f"{conf['column']}_value"), conf.get('target_unit_col', f"{conf['column']}_unit")
                if col in df.columns:
                    parsed = df[col].apply(lambda x: parse_value_range(x) if pd.notna(x) else (None, None))
                    df[target_val] = parsed.apply(lambda x: x[0])
                    df[target_unit] = parsed.apply(lambda x: x[1])
                else: self.logger.warning(f"Value column '{col}' not found for parsing.")

            place_configs = getattr(config_params, 'place_column_configs', [])
            for conf in place_configs:
                col = conf['column']
                if col in df.columns:
                    parsed = df[col].apply(lambda x: split_place(x) if pd.notna(x) else (None, None))
                    df[conf.get('target_city_col', f"{col}_city")] = parsed.apply(lambda x: x[0] if len(x) > 0 else None)
                    df[conf.get('target_state_col', f"{col}_state")] = parsed.apply(lambda x: x[1] if len(x) > 1 else None)
                    # Set country from config default if target_country_col is specified
                    country_col = conf.get('target_country_col')
                    if country_col:
                        df[country_col] = getattr(config_params, 'default_country', 'USA')
                else: self.logger.warning(f"Place column '{col}' not found for parsing.")
            
            self.logger.info(f"DataFrame transformation completed. Shape after all transforms: {df.shape}")
            return df
        except Exception as e:
            self._handle_and_raise_scraper_error(e, operation_desc)
        return pd.DataFrame() # Should be unreachable


    def prepare_and_load_data(self, df: pd.DataFrame, config_params: Any, data_source=None) -> int:
        """Prepares DataFrame data and loads it into the database."""
        if not all(hasattr(self, attr) for attr in ['logger', 'config', '_handle_and_raise_scraper_error']):
            raise AttributeError("DataProcessingMixin.prepare_and_load_data is missing required attributes/methods.")
        
        source_name = self.config.source_name # Get from config
        operation_desc = f"preparing and loading data for source: {source_name}"
        self.logger.info(f"Starting {operation_desc}")
        if df.empty: self.logger.info("DataFrame is empty. Nothing to load."); return 0

        try:
            id_hash_cols = getattr(config_params, 'fields_for_id_hash', [])
            if not id_hash_cols: self._handle_and_raise_scraper_error(ValueError("fields_for_id_hash not configured."), operation_desc); return 0
            df['id_hash'] = generate_id_hash(df, id_hash_cols, prefix=source_name)

            required_cols = getattr(config_params, 'required_fields_for_load', [])
            if required_cols:
                original_len = len(df)
                df.dropna(subset=required_cols, how='any', inplace=True)
                self.logger.info(f"Filtered {original_len - len(df)} rows due to missing required fields: {required_cols}. {len(df)} rows remaining.")
            if df.empty: self.logger.info("DataFrame empty after filtering. Nothing to load."); return 0
            
            db_col_map = getattr(config_params, 'db_column_rename_map', {})
            if db_col_map: df.rename(columns=db_col_map, inplace=True, errors='ignore')
            
            # Determine actual Prospect model fields dynamically
            actual_model_fields = [col.name for col in Prospect.__table__.columns]

            prospects_data_list = []
            for record_dict in df.to_dict(orient='records'):
                data = {k: (None if pd.isna(v) else v) for k, v in record_dict.items()}
                prospect_instance_data = {k: data[k] for k in actual_model_fields if k in data}
                extra_data = {k: data[k] for k in data if k not in actual_model_fields and k != 'id_hash'} # id_hash is special
                
                prospect_instance_data['extra'] = extra_data if extra_data else None
                if data_source and hasattr(data_source, 'id'):
                    prospect_instance_data['source_id'] = data_source.id # Set source_id from data_source
                if 'id_hash' in data: prospect_instance_data['id'] = data['id_hash'] # Map id_hash to id field
                
                # Ensure all model fields are present in prospect_instance_data, defaulting to None
                for mf in actual_model_fields:
                    if mf not in prospect_instance_data: prospect_instance_data[mf] = None
                
                # Remove 'id' if it's None, as DB might auto-generate it. This depends on model definition.
                # If 'id' is manually managed (e.g. from id_hash), this might not be needed.
                # For now, assume 'id' (PK) is handled by DB or is part of 'id_hash' mapping.
                if 'id' in prospect_instance_data and prospect_instance_data['id'] is None:
                    del prospect_instance_data['id'] 

                prospects_data_list.append(prospect_instance_data)

            if not prospects_data_list: self.logger.info("No valid data to load after final prep."); return 0
            
            self.logger.info(f"Attempting to bulk upsert {len(prospects_data_list)} prospects for {source_name}.")
            # Convert prospects_data_list back to DataFrame for bulk_upsert_prospects
            prospects_df = pd.DataFrame(prospects_data_list)
            result = bulk_upsert_prospects(
                prospects_df, 
                preserve_ai_data=active_config.PRESERVE_AI_DATA_ON_REFRESH,
                enable_smart_matching=active_config.ENABLE_SMART_DUPLICATE_MATCHING
            ) 
            self.logger.info(f"Bulk upsert completed for {source_name}. Result: {result}")
            return len(prospects_data_list) 
        except Exception as e:
            self._handle_and_raise_scraper_error(e, operation_desc)
        return 0 # Should be unreachable
