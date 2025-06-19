"""
Treasury scraper using the consolidated architecture.
Preserves all original Treasury-specific functionality including complex custom transforms.
"""
import pandas as pd
import os
from datetime import datetime
from typing import Optional

from app.core.consolidated_scraper_base import ConsolidatedScraperBase
from app.core.config_converter import create_treasury_config
from app.config import active_config


class TreasuryScraper(ConsolidatedScraperBase):
    """
    Consolidated Treasury scraper.
    Preserves all original functionality including complex native_id handling.
    """
    
    def __init__(self):
        config = create_treasury_config()
        config.base_url = active_config.TREASURY_FORECAST_URL
        super().__init__(config)
    
    def _custom_treasury_transforms(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Custom Treasury transformations preserving the original complex logic.
        Handles native_id selection, row_index, and description initialization.
        """
        try:
            self.logger.info("Applying Treasury transformations...")
            
            # Handle alternative native_id fields (from original _custom_treasury_pre_transforms)
            if 'native_id_intermediate' in df.columns:
                df['native_id_final'] = df['native_id_intermediate']
                self.logger.debug("Used 'native_id_intermediate' as native_id_final.")
            elif 'shopcart_req_intermediate' in df.columns:
                df['native_id_final'] = df['shopcart_req_intermediate']
                self.logger.info("Used 'shopcart_req_intermediate' as native_id_final.")
            elif 'contract_num_intermediate' in df.columns:
                df['native_id_final'] = df['contract_num_intermediate']
                self.logger.info("Used 'contract_num_intermediate' as native_id_final.")
            else:
                df['native_id_final'] = None
                self.logger.warning("No primary or fallback native ID column found. 'native_id_final' set to None.")

            # Add row_index for unique ID generation (Treasury data may have duplicates)
            df.reset_index(drop=True, inplace=True)
            df['row_index'] = df.index 
            self.logger.debug("Added 'row_index' to DataFrame.")
            
            # Initialize description as None (from original _custom_treasury_transforms_in_mixin_flow)
            df['description_final'] = None 
            self.logger.debug("Initialized 'description_final' to None.")
            
        except Exception as e:
            self.logger.warning(f"Error in _custom_treasury_transforms: {e}")
        
        return df
    
    async def treasury_setup(self) -> bool:
        """
        Treasury-specific setup: navigate and wait for 'load' state.
        Preserves original Treasury behavior.
        """
        if not self.base_url:
            self.logger.error("Base URL not configured.")
            return False
        
        self.logger.info(f"Treasury setup: Navigating to {self.base_url}")
        
        success = await self.navigate_to_url(self.base_url, wait_until='domcontentloaded')
        if success:
            # Wait for the page to be fully interactive instead of 'load'
            await self.wait_for_load_state('domcontentloaded')
            self.logger.info("Page DOM content loaded and interactive.")
        
        return success
    
    async def treasury_extract(self) -> Optional[str]:
        """
        Treasury-specific extraction with multiple download strategies.
        Handles Salesforce Lightning framework quirks.
        """
        self.logger.info("Starting Treasury data file download process.")
        
        selector = self.config.export_button_selector
        
        # Wait for the download button to be visible
        if not await self.wait_for_selector(selector, state='visible'):
            self.logger.error(f"Download button '{selector}' not found or not visible")
            return None
        
        self.logger.info(f"Download button '{selector}' is visible.")
        
        # Try multiple download strategies for Lightning framework
        return await self._treasury_multi_strategy_download(selector)
    
    async def _treasury_multi_strategy_download(self, selector: str) -> Optional[str]:
        """
        Try multiple download strategies for Treasury's Lightning framework.
        """
        # Strategy 1: Check if clicking button updates page content with data
        self.logger.info("Strategy 1: Check for page content update after button click")
        result = await self._treasury_page_content_download(selector)
        if result:
            return result
        
        # Strategy 2: Traditional download with extended timeout
        self.logger.info("Strategy 2: Traditional download with long timeout")
        result = await self.download_file_via_click(
            selector=selector,
            js_click_fallback=True,
            wait_after_click=2000,  # Wait 2 seconds after click
            timeout=60000  # Reduced timeout for faster testing
        )
        if result:
            return result
        
        # Strategy 3: Check for new tab/window downloads
        self.logger.info("Strategy 3: Checking for new tab/window download")
        result = await self._treasury_new_tab_download(selector)
        if result:
            return result
        
        # Strategy 4: Look for direct download links after button click
        self.logger.info("Strategy 4: Looking for generated download links")
        result = await self._treasury_generated_link_download(selector)
        if result:
            return result
        
        self.logger.error("All Treasury download strategies failed")
        return None
    
    async def _treasury_page_content_download(self, selector: str) -> Optional[str]:
        """
        Click button and check if the current page content is updated with data.
        """
        try:
            # Get initial page content to compare
            initial_content = await self.page.content()
            initial_length = len(initial_content)
            
            # Click the button
            self.logger.info("Clicking download button to check for page content update")
            success = await self.click_element(selector, use_js=True)
            if not success:
                return None
            
            # Wait for potential content update
            await self.wait_for_timeout(5000)  # Wait 5 seconds for content to load
            
            # Get updated content
            updated_content = await self.page.content()
            updated_length = len(updated_content)
            
            self.logger.info(f"Content length: initial={initial_length}, updated={updated_length}")
            
            # Check if content significantly changed (likely with data table)
            if updated_length > initial_length * 1.1:  # At least 10% increase
                # Look for table data indicators
                if 'table' in updated_content.lower() and ('naics' in updated_content.lower() or 'contract' in updated_content.lower()):
                    # This looks like Treasury data content
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"treasury_data_{timestamp}.html"
                    filepath = os.path.join(self.download_dir, filename)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(updated_content)
                    
                    self.last_downloaded_file = filepath
                    self.logger.info(f"Saved Treasury data from page content: {filepath}")
                    return filepath
            
            # Check if any visible table elements appeared or updated
            table_elements = await self.page.query_selector_all('table')
            if table_elements:
                self.logger.info(f"Found {len(table_elements)} table elements on page")
                
                # Try to find the main data table
                for i, table in enumerate(table_elements):
                    table_text = await table.inner_text()
                    if len(table_text) > 1000 and ('naics' in table_text.lower() or 'contract' in table_text.lower()):
                        # This looks like the data table
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"treasury_table_data_{timestamp}.html"
                        filepath = os.path.join(self.download_dir, filename)
                        
                        table_html = await table.inner_html()
                        full_html = f"""
                        <html>
                        <head><title>Treasury Data</title></head>
                        <body>
                        <table>{table_html}</table>
                        </body>
                        </html>
                        """
                        
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(full_html)
                        
                        self.last_downloaded_file = filepath
                        self.logger.info(f"Saved Treasury table data: {filepath}")
                        return filepath
            
        except Exception as e:
            self.logger.warning(f"Page content download strategy failed: {e}")
        
        return None
    
    async def _treasury_new_tab_download(self, selector: str) -> Optional[str]:
        """
        Handle Treasury downloads that might open in new tabs.
        """
        try:
            # Set up new page expectation
            async with self.context.expect_page() as new_page_info:
                # Click the button
                success = await self.click_element(selector, use_js=True)
                if not success:
                    return None
                
                # Wait for new page
                new_page = await new_page_info.value
                
                # Check if new page has download or data
                await new_page.wait_for_load_state('domcontentloaded', timeout=30000)
                
                # Look for download on new page or check if it's the data page itself
                url = new_page.url
                self.logger.info(f"New page opened: {url}")
                
                # If the new page is a direct download URL, download it
                if any(ext in url.lower() for ext in ['.xls', '.xlsx', '.csv']):
                    await new_page.close()
                    return await self.download_file_directly(url)
                
                # Check if new page has the data content
                content = await new_page.content()
                if 'table' in content.lower() and len(content) > 10000:  # Likely has data table
                    # Save the HTML content as the data file
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"treasury_data_{timestamp}.html"
                    filepath = os.path.join(self.download_dir, filename)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    await new_page.close()
                    self.last_downloaded_file = filepath
                    self.logger.info(f"Saved Treasury data from new page: {filepath}")
                    return filepath
                
                await new_page.close()
                
        except Exception as e:
            self.logger.warning(f"New tab download strategy failed: {e}")
        
        return None
    
    async def _treasury_generated_link_download(self, selector: str) -> Optional[str]:
        """
        Look for dynamically generated download links after clicking the button.
        """
        try:
            # Click the button first
            success = await self.click_element(selector, use_js=True)
            if not success:
                return None
            
            # Wait for potential dynamic content to load
            await self.wait_for_timeout(3000)
            
            # Look for any new download links that might have appeared
            download_selectors = [
                "a[href*='.xls']",
                "a[href*='.xlsx']", 
                "a[href*='download']",
                "a[download]",
                "button[onclick*='download']"
            ]
            
            for dl_selector in download_selectors:
                elements = await self.page.query_selector_all(dl_selector)
                if elements:
                    self.logger.info(f"Found {len(elements)} potential download links with {dl_selector}")
                    
                    for element in elements:
                        href = await element.get_attribute('href')
                        if href and not href.startswith('javascript:'):
                            # Try to download directly
                            if href.startswith('/'):
                                # Relative URL, make it absolute
                                href = f"https://osdbu.forecast.treasury.gov{href}"
                            elif not href.startswith('http'):
                                continue
                            
                            self.logger.info(f"Attempting direct download from: {href}")
                            return await self.download_file_directly(href)
            
        except Exception as e:
            self.logger.warning(f"Generated link download strategy failed: {e}")
        
        return None
    
    def treasury_process(self, file_path: str) -> int:
        """
        Treasury-specific processing preserving original file reading strategy.
        """
        if not file_path:
            # Try to get most recent download
            file_path = self.get_last_downloaded_path()
            if not file_path:
                self.logger.error("No file available for processing")
                return 0
        
        self.logger.info(f"Starting Treasury processing for file: {file_path}")
        
        # Read file using html_then_excel strategy
        df = self.read_file_to_dataframe(file_path)
        if df is None or df.empty:
            self.logger.info("DataFrame is empty after reading. Nothing to process.")
            return 0
        
        # Initial cleanup
        df = df.dropna(how='all')
        if df.empty:
            self.logger.info("DataFrame is empty after initial dropna. Nothing to process.")
            return 0
        
        # Apply transformations
        df = self.transform_dataframe(df)
        if df.empty:
            self.logger.info("DataFrame is empty after transformations. Nothing to load.")
            return 0
        
        # Load to database
        return self.prepare_and_load_data(df)
    
    async def scrape(self) -> int:
        """Execute the complete Treasury scraping workflow."""
        return await self.scrape_with_structure(
            setup_method=self.treasury_setup,
            extract_method=self.treasury_extract,
            process_method=self.treasury_process
        )


# For backward compatibility
async def run_treasury_scraper() -> int:
    """Run the Treasury scraper."""
    scraper = TreasuryScraper()
    return await scraper.scrape()