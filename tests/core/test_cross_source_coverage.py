"""
Cross-source data mapping rule enforcement test.

Verifies that required fields are present or inferable across at least 80% of sources.
This ensures data consistency and helps identify when scrapers need updates.
"""

import pytest
from typing import Dict, List, Set
import pandas as pd
from pathlib import Path

from app.core.scraper_configs import (
    ACQUISITION_GATEWAY_CONFIG,
    DHS_CONFIG,
    HHS_CONFIG,
    TREASURY_CONFIG,
    DOT_CONFIG,
    SSA_CONFIG,
    DOC_CONFIG,
    DOJ_CONFIG,
    DOS_CONFIG,
)
from tests.factories import ScraperDataFactory


class TestCrossSourceCoverage:
    """Test that required fields are consistently produced across sources."""
    
    # Required fields that should be present in ≥80% of sources
    REQUIRED_FIELDS = {
        "title": "Opportunity title",
        "agency": "Agency name",
        "naics": "NAICS code",
        "estimated_value_text": "Value as text (or parsed numeric)",
        "place_city": "City location",
        "place_state": "State location",
        "loaded_at": "Load timestamp",
    }
    
    # Fields that can be inferred or have acceptable defaults
    INFERABLE_FIELDS = {
        "description": "Can be empty or generated from title",
        "posted_date": "Can be inferred from loaded_at",
        "response_date": "Can be null for some opportunities",
    }
    
    COVERAGE_THRESHOLD = 0.8  # 80% of sources must provide required fields
    
    @pytest.fixture
    def scraper_configs(self):
        """Get all scraper configurations."""
        return {
            "ACQUISITION_GATEWAY": ACQUISITION_GATEWAY_CONFIG,
            "DHS": DHS_CONFIG,
            "HHS": HHS_CONFIG,
            "TREASURY": TREASURY_CONFIG,
            "DOT": DOT_CONFIG,
            "SSA": SSA_CONFIG,
            "DOC": DOC_CONFIG,
            "DOJ": DOJ_CONFIG,
            "DOS": DOS_CONFIG,
        }
    
    @pytest.fixture
    def sample_data_per_source(self):
        """Generate deterministic sample data for each source."""
        samples = {}
        
        # Create sample data for each source
        sources = [
            "ACQUISITION_GATEWAY", "DHS", "HHS", "TREASURY", 
            "DOT", "SSA", "DOC", "DOJ", "DOS"
        ]
        
        for idx, source in enumerate(sources):
            # Create deterministic sample data
            opportunity = ScraperDataFactory.create_opportunity_dict(idx)
            
            # Simulate source-specific field availability
            if source == "SSA":
                # SSA might not have NAICS
                opportunity.pop("naics", None)
            elif source == "DOJ":
                # DOJ might not have place information
                opportunity.pop("place", None)
            elif source == "DOS":
                # DOS might not have value information
                opportunity.pop("value", None)
            
            # Convert to DataFrame format (as scrapers would produce)
            df = pd.DataFrame([opportunity])
            
            # Apply source-specific transformations
            df = self._apply_source_transformations(df, source)
            
            samples[source] = df
        
        return samples
    
    def _apply_source_transformations(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        """Apply source-specific field transformations."""
        # Common transformations that scrapers perform
        
        # Parse place into city/state if present
        if "place" in df.columns and df["place"].notna().any():
            df["place_city"] = df["place"].str.split(",").str[0].str.strip()
            df["place_state"] = df["place"].str.split(",").str[-1].str.strip()
        
        # Rename value to estimated_value_text
        if "value" in df.columns:
            df["estimated_value_text"] = df["value"]
        
        # Add loaded_at timestamp
        df["loaded_at"] = pd.Timestamp.now()
        
        # Source-specific transformations
        if source == "ACQUISITION_GATEWAY":
            # AG has good data coverage
            pass
        elif source == "DHS":
            # DHS specific mappings
            if "solicitation_number" in df.columns:
                df["native_id"] = df["solicitation_number"]
        
        return df
    
    def test_required_fields_coverage(self, sample_data_per_source):
        """Test that required fields meet coverage threshold across sources."""
        field_coverage = {}
        missing_by_source = {}
        
        # Calculate coverage for each required field
        for field, description in self.REQUIRED_FIELDS.items():
            sources_with_field = []
            sources_missing_field = []
            
            for source, df in sample_data_per_source.items():
                if field in df.columns and df[field].notna().any():
                    sources_with_field.append(source)
                else:
                    sources_missing_field.append(source)
            
            coverage = len(sources_with_field) / len(sample_data_per_source)
            field_coverage[field] = coverage
            
            if sources_missing_field:
                missing_by_source[field] = sources_missing_field
        
        # Generate report
        report_lines = [
            "\n" + "="*60,
            "CROSS-SOURCE FIELD COVERAGE REPORT",
            "="*60,
            f"Threshold: {self.COVERAGE_THRESHOLD*100:.0f}%",
            f"Total Sources: {len(sample_data_per_source)}",
            "",
        ]
        
        # Report field coverage
        for field, coverage in field_coverage.items():
            status = "✓" if coverage >= self.COVERAGE_THRESHOLD else "✗"
            report_lines.append(
                f"{status} {field:25s} {coverage*100:5.1f}% "
                f"({int(coverage * len(sample_data_per_source))}/{len(sample_data_per_source)} sources)"
            )
            
            if field in missing_by_source and coverage < self.COVERAGE_THRESHOLD:
                report_lines.append(f"    Missing in: {', '.join(missing_by_source[field])}")
        
        # Check for failures
        failed_fields = [
            field for field, coverage in field_coverage.items() 
            if coverage < self.COVERAGE_THRESHOLD
        ]
        
        if failed_fields:
            report_lines.extend([
                "",
                "ACTIONS REQUIRED:",
                "-"*40,
            ])
            
            for field in failed_fields:
                report_lines.append(
                    f"• {field}: Update scrapers for {', '.join(missing_by_source[field])} "
                    f"to extract or infer this field"
                )
        
        report = "\n".join(report_lines)
        print(report)  # Print for visibility
        
        # Assert coverage threshold is met
        assert not failed_fields, (
            f"The following fields do not meet {self.COVERAGE_THRESHOLD*100:.0f}% coverage threshold:\n"
            f"{report}"
        )
    
    def test_inferable_fields_present_or_null(self, sample_data_per_source):
        """Test that inferable fields are either present or properly null."""
        issues = []
        
        for field in self.INFERABLE_FIELDS:
            for source, df in sample_data_per_source.items():
                if field in df.columns:
                    # Field exists - check it's either populated or explicitly null
                    if df[field].isna().all():
                        # All null is OK for inferable fields
                        pass
                    elif df[field].notna().any():
                        # Has some values - good
                        pass
                    else:
                        issues.append(f"{source}: {field} exists but has invalid state")
        
        assert not issues, f"Inferable field issues found:\n" + "\n".join(issues)
    
    def test_critical_field_combinations(self, sample_data_per_source):
        """Test that critical field combinations are present."""
        critical_combinations = [
            ("title", "agency"),  # Must have title and agency
            ("loaded_at",),  # Must have timestamp
        ]
        
        issues = []
        
        for source, df in sample_data_per_source.items():
            for combination in critical_combinations:
                if not all(
                    field in df.columns and df[field].notna().any() 
                    for field in combination
                ):
                    issues.append(
                        f"{source}: Missing critical combination {combination}"
                    )
        
        assert not issues, (
            "Critical field combinations missing:\n" + "\n".join(issues)
        )
    
    def test_value_field_consistency(self, sample_data_per_source):
        """Test that value fields are consistently handled."""
        value_fields = ["estimated_value_text", "estimated_value_single", "value"]
        
        for source, df in sample_data_per_source.items():
            has_any_value = any(
                field in df.columns and df[field].notna().any() 
                for field in value_fields
            )
            
            # Each source should have at least one value field or explicitly none
            if not has_any_value:
                # Check if this is expected for the source
                if source not in ["DOS"]:  # DOS might not have values
                    pytest.fail(
                        f"{source}: No value field found. "
                        f"Expected one of {value_fields}"
                    )
    
    def test_naics_consistency(self, sample_data_per_source):
        """Test NAICS code format consistency across sources."""
        naics_issues = []
        
        for source, df in sample_data_per_source.items():
            if "naics" in df.columns and df["naics"].notna().any():
                naics_values = df["naics"].dropna()
                
                for naics in naics_values:
                    # NAICS should be string of digits
                    if not isinstance(naics, str) or not naics.isdigit():
                        naics_issues.append(
                            f"{source}: Invalid NAICS format '{naics}' - should be numeric string"
                        )
                    
                    # Standard NAICS codes are 2-6 digits
                    if len(naics) < 2 or len(naics) > 6:
                        naics_issues.append(
                            f"{source}: Invalid NAICS length '{naics}' - should be 2-6 digits"
                        )
        
        assert not naics_issues, (
            "NAICS code format issues:\n" + "\n".join(naics_issues)
        )
    
    def test_location_field_pairing(self, sample_data_per_source):
        """Test that location fields are properly paired."""
        for source, df in sample_data_per_source.items():
            has_city = "place_city" in df.columns and df["place_city"].notna().any()
            has_state = "place_state" in df.columns and df["place_state"].notna().any()
            
            # If one is present, both should be present
            if has_city != has_state:
                pytest.fail(
                    f"{source}: Incomplete location data. "
                    f"Has city: {has_city}, Has state: {has_state}. "
                    f"Both should be present or both absent."
                )
    
    def test_field_coverage_report_generation(self, sample_data_per_source):
        """Test that a comprehensive field coverage report can be generated."""
        all_fields = set()
        
        # Collect all fields across all sources
        for df in sample_data_per_source.values():
            all_fields.update(df.columns)
        
        # Create coverage matrix
        coverage_matrix = pd.DataFrame(
            index=sorted(all_fields),
            columns=sorted(sample_data_per_source.keys()),
            data=False
        )
        
        # Fill coverage matrix
        for source, df in sample_data_per_source.items():
            for field in df.columns:
                if df[field].notna().any():
                    coverage_matrix.loc[field, source] = True
        
        # Calculate field coverage percentages
        field_coverage = (coverage_matrix.sum(axis=1) / len(sample_data_per_source) * 100).round(1)
        
        # Identify high-value fields (present in many sources)
        high_value_fields = field_coverage[field_coverage >= 60].index.tolist()
        
        # Verify we have good coverage of high-value fields
        assert len(high_value_fields) >= 5, (
            f"Too few high-value fields (60%+ coverage). "
            f"Found {len(high_value_fields)}, expected at least 5. "
            f"This suggests poor data extraction across sources."
        )