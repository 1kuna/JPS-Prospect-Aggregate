"""
DOJ scraper using the consolidated architecture.
Preserves all original DOJ-specific functionality including complex award date processing.
"""
import json
import pandas as pd
from typing import Optional
from app.utils.value_and_date_parsing import fiscal_quarter_to_date

from app.core.consolidated_scraper_base import ConsolidatedScraperBase
from app.core.config_converter import create_doj_config
from app.config import active_config


class DOJForecastScraper(ConsolidatedScraperBase):
    """
    Consolidated DOJ scraper.
    Preserves all original functionality including complex award date logic and place country handling.
    """
    
    def __init__(self):
        config = create_doj_config()
        config.base_url = active_config.DOJ_FORECAST_URL
        super().__init__(config)
    
    def _custom_doj_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Custom DOJ transformations preserving the original complex logic.
        Handles award date with fiscal quarter fallback and place country standardization.
        """
        try:
            self.logger.info("Applying custom DOJ transformations...")
            
            # Award Date Logic (Complex)
            award_date_col_raw = "award_date_raw"  # From raw_column_rename_map
            
            if award_date_col_raw in df.columns:
                df['award_date_final'] = pd.to_datetime(df[award_date_col_raw], errors='coerce')
                # Attempt to get year directly, will be float if NaT present, so handle with Int64 later
                df['award_fiscal_year_final'] = df['award_date_final'].dt.year 
                
                needs_fallback_mask = df['award_date_final'].isna() & df[award_date_col_raw].notna()
                if needs_fallback_mask.any():
                    self.logger.info(f"Found {needs_fallback_mask.sum()} award dates needing fiscal quarter fallback parsing.")
                    parsed_qtr_info = df.loc[needs_fallback_mask, award_date_col_raw].apply(
                        lambda x: fiscal_quarter_to_date(x) if pd.notna(x) else (None, None)
                    )
                    df.loc[needs_fallback_mask, 'award_date_final'] = parsed_qtr_info.apply(lambda x: x[0])
                    df.loc[needs_fallback_mask, 'award_fiscal_year_final'] = parsed_qtr_info.apply(lambda x: x[1])
                
                # Final conversion to date object and Int64 for year
                df['award_date_final'] = pd.to_datetime(df['award_date_final'], errors='coerce').dt.date
                df['award_fiscal_year_final'] = df['award_fiscal_year_final'].astype('Int64')  # Handles NaN -> <NA>
                self.logger.debug("Processed 'award_date_final' and 'award_fiscal_year_final' with fallback logic.")
            else:
                df['award_date_final'] = None
                df['award_fiscal_year_final'] = pd.NA
                self.logger.warning(f"'{award_date_col_raw}' not found. Award date fields initialized to None/NA.")

            # Contact Selection Logic - prioritize requirement POC over small business POC
            req_poc_name = 'doj_req_poc_name'
            req_poc_email = 'doj_req_poc_email' 
            sb_poc_name = 'doj_sb_poc_name'
            sb_poc_email = 'doj_sb_poc_email'
            
            # Initialize primary contact fields
            df['primary_contact_name'] = None
            df['primary_contact_email'] = None
            
            # Prioritize requirement POC
            if req_poc_name in df.columns and req_poc_email in df.columns:
                df['primary_contact_name'] = df[req_poc_name].fillna('')
                df['primary_contact_email'] = df[req_poc_email].fillna('')
                
                # Fall back to small business POC where requirement POC is missing
                if sb_poc_name in df.columns and sb_poc_email in df.columns:
                    df['primary_contact_name'] = df['primary_contact_name'].where(
                        df['primary_contact_name'] != '', df[sb_poc_name].fillna('')
                    )
                    df['primary_contact_email'] = df['primary_contact_email'].where(
                        df['primary_contact_email'] != '', df[sb_poc_email].fillna('')
                    )
                
                # Clean up empty values
                df['primary_contact_name'] = df['primary_contact_name'].replace('', None)
                df['primary_contact_email'] = df['primary_contact_email'].replace('', None)
                self.logger.debug("Selected primary contacts from DOJ requirement POC with small business POC fallback.")

            # Place Country Logic
            place_country_col_raw = "place_country_raw"  # From raw_column_rename_map (original: 'Country')
            if place_country_col_raw in df.columns:
                df['place_country_final'] = df[place_country_col_raw].fillna('USA')
                self.logger.debug("Processed 'place_country_final', defaulting NA to USA.")
            else:
                df['place_country_final'] = 'USA'
                self.logger.debug(f"'{place_country_col_raw}' not found. Defaulted 'place_country_final' to USA.")
                
        except Exception as e:
            self.logger.warning(f"Error in _custom_doj_transforms: {e}")
        
        return df
    
    def _doj_create_extras(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create extras JSON with DOJ-specific fields that aren't in core schema.
        Captures 21 additional data points for comprehensive data retention.
        """
        try:
            # Define DOJ-specific extras fields mapping (using original CSV column names)
            extras_fields = {
                'Fiscal Year': 'fiscal_year',
                'OBD': 'organizational_business_division', 
                'Contracting Office': 'contracting_office',
                'DOJ Small Business POC - Name': 'small_business_poc_name',
                'DOJ Small Business POC - Email Address': 'small_business_poc_email',
                'DOJ Requirement POC - Name': 'requirement_poc_name',
                'DOJ Requirement POC - Email Address': 'requirement_poc_email',
                'Category': 'category',
                'Subcategory': 'subcategory', 
                'Award Type': 'award_type',
                'Product Service Code': 'product_service_code',
                'Competition Approach': 'competition_approach',
                'Contracting Solution': 'contracting_solution',
                'Contract Availability': 'contract_availability',
                'Length of Contract': 'length_of_contract',
                'Request for Information (RFI) Planned': 'rfi_planned',
                'Acquisition History': 'acquisition_history',
                'Incumbent Contractor': 'incumbent_contractor',
                'Incumbent Contractor PIID': 'incumbent_contractor_piid',
                'Solicitation Link': 'solicitation_link',
                'Other Information': 'other_information'
            }
            
            # Create extras JSON column
            extras_data = []
            for _, row in df.iterrows():
                extras = {}
                for df_col, extra_key in extras_fields.items():
                    if df_col in df.columns:
                        value = row[df_col]
                        if pd.notna(value) and value != '':
                            extras[extra_key] = str(value)
                extras_data.append(extras if extras else {})
            
            # Add the extras JSON column
            df['extras_json'] = [json.dumps(extras) for extras in extras_data]
            
            self.logger.debug(f"Created DOJ extras JSON for {len(extras_data)} rows with {len(extras_fields)} potential fields")
                
        except Exception as e:
            self.logger.warning(f"Error in _doj_create_extras: {e}")
        
        return df
    
    async def doj_setup(self) -> bool:
        """
        DOJ-specific setup: navigate to URL and wait for DOM to load.
        """
        if not self.base_url:
            self.logger.error("Base URL not configured.")
            return False
        
        self.logger.info(f"DOJ setup: Navigating to {self.base_url}")
        
        success = await self.navigate_to_url(self.base_url)
        if not success:
            return False
        
        # Ensure basic page structure is ready
        await self.wait_for_load_state('domcontentloaded')
        return True
    
    async def doj_extract(self) -> Optional[str]:
        """
        DOJ-specific extraction: wait for download link and click to download.
        Preserves original DOJ download behavior.
        """
        self.logger.info(f"Starting DOJ Excel document download. Waiting for link: {self.config.export_button_selector}")
        
        # Wait for the download link to be visible
        await self.wait_for_selector(
            self.config.export_button_selector,
            timeout=self.config.interaction_timeout_ms,
            state='visible'
        )
        self.logger.info("Download link is visible.")
        
        # Download via click
        return await self.download_file_via_click(
            selector=self.config.export_button_selector
        )
    
    def doj_process(self, file_path: str) -> int:
        """
        DOJ-specific processing with Excel-specific read options.
        """
        if not file_path:
            # Try to get most recent download
            file_path = self.get_last_downloaded_path()
            if not file_path:
                self.logger.error("No file available for processing")
                return 0
        
        self.logger.info(f"Starting DOJ processing for file: {file_path}")
        
        # Read Excel file with specific options (header at row 12)
        df = self.read_file_to_dataframe(file_path)
        if df is None or df.empty:
            self.logger.info("DataFrame is empty after reading. Nothing to process.")
            return 0
        
        # Apply transformations
        df = self.transform_dataframe(df)
        if df.empty:
            self.logger.info("DataFrame is empty after transformations. Nothing to load.")
            return 0
        
        # Load to database
        return self.prepare_and_load_data(df)
    
    async def scrape(self) -> int:
        """Execute the complete DOJ scraping workflow."""
        return await self.scrape_with_structure(
            setup_method=self.doj_setup,
            extract_method=self.doj_extract,
            process_method=self.doj_process
        )


# For backward compatibility
async def run_doj_scraper() -> int:
    """Run the DOJ scraper."""
    scraper = DOJForecastScraper()
    return await scraper.scrape()