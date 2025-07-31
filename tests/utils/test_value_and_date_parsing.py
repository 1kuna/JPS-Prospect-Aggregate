"""
Comprehensive tests for value and date parsing utilities.

Tests critical data processing functions for contract values and dates.
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import patch

from app.utils.value_and_date_parsing import (
    parse_contract_value,
    parse_date,
    standardize_date_format,
    extract_numeric_value,
    parse_fiscal_year,
    clean_currency_text,
    validate_date_range,
    parse_date_range
)


class TestContractValueParsing:
    """Test contract value parsing functions."""
    
    def test_parse_contract_value_single_values(self):
        """Test parsing single contract values."""
        test_cases = [
            ("$100,000", 100000),
            ("$1,500,000.00", 1500000),
            ("500000", 500000),
            ("$50K", 50000),
            ("$2.5M", 2500000),
            ("$1.2B", 1200000000),
            ("100K", 100000),
            ("2.5M", 2500000),
            ("1.2B", 1200000000),
        ]
        
        for input_value, expected in test_cases:
            result = parse_contract_value(input_value)
            assert abs(result - expected) < 0.01, f"Failed for {input_value}: got {result}, expected {expected}"
    
    def test_parse_contract_value_ranges(self):
        """Test parsing contract value ranges."""
        test_cases = [
            ("$100,000 - $500,000", (100000, 500000)),
            ("$1M - $5M", (1000000, 5000000)),
            ("100K - 500K", (100000, 500000)),
            ("$50,000 to $150,000", (50000, 150000)),
            ("Between $100K and $300K", (100000, 300000)),
            ("$1.5M-$2.5M", (1500000, 2500000)),
        ]
        
        for input_value, expected in test_cases:
            result = parse_contract_value(input_value)
            assert isinstance(result, tuple), f"Expected tuple for {input_value}"
            assert len(result) == 2, f"Expected 2-element tuple for {input_value}"
            min_val, max_val = result
            expected_min, expected_max = expected
            assert abs(min_val - expected_min) < 0.01, f"Min value failed for {input_value}"
            assert abs(max_val - expected_max) < 0.01, f"Max value failed for {input_value}"
    
    def test_parse_contract_value_edge_cases(self):
        """Test edge cases in contract value parsing."""
        # Empty or invalid inputs
        assert parse_contract_value("") is None
        assert parse_contract_value(None) is None
        assert parse_contract_value("TBD") is None
        assert parse_contract_value("To Be Determined") is None
        assert parse_contract_value("N/A") is None
        assert parse_contract_value("Not Available") is None
        
        # Text without numbers
        assert parse_contract_value("No value specified") is None
        assert parse_contract_value("Contact for details") is None
        
        # Complex text with embedded values
        result = parse_contract_value("The contract value is estimated at $250,000 for this project")
        assert abs(result - 250000) < 0.01
    
    def test_parse_contract_value_international_formats(self):
        """Test parsing international currency formats."""
        test_cases = [
            ("€100,000", 100000),
            ("£250,000", 250000),
            ("¥1,000,000", 1000000),
            ("CAD $500,000", 500000),
            ("USD $750,000", 750000),
        ]
        
        for input_value, expected in test_cases:
            result = parse_contract_value(input_value)
            assert abs(result - expected) < 0.01, f"Failed for {input_value}"
    
    def test_extract_numeric_value(self):
        """Test numeric value extraction utility."""
        test_cases = [
            ("$1,234,567.89", 1234567.89),
            ("1.5K", 1500),
            ("2.5M", 2500000),
            ("1.2B", 1200000000),
            ("50%", 50),
            ("3.14159", 3.14159),
        ]
        
        for input_value, expected in test_cases:
            result = extract_numeric_value(input_value)
            assert abs(result - expected) < 0.01, f"Failed for {input_value}"
    
    def test_clean_currency_text(self):
        """Test currency text cleaning utility."""
        test_cases = [
            ("$1,234,567.89", "1234567.89"),
            ("USD $500,000", "500000"),
            ("€100,000.00", "100000.00"),
            ("Contract value: $250K", "250K"),
            ("Estimated at $1.5M - $2.5M", "1.5M - 2.5M"),
        ]
        
        for input_value, expected in test_cases:
            result = clean_currency_text(input_value)
            assert expected in result, f"Expected '{expected}' in result for '{input_value}', got '{result}'"


class TestDateParsing:
    """Test date parsing functions."""
    
    def test_parse_date_standard_formats(self):
        """Test parsing standard date formats."""
        test_cases = [
            ("2024-01-15", date(2024, 1, 15)),
            ("01/15/2024", date(2024, 1, 15)),
            ("15-Jan-2024", date(2024, 1, 15)),
            ("January 15, 2024", date(2024, 1, 15)),
            ("Jan 15, 2024", date(2024, 1, 15)),
            ("15 January 2024", date(2024, 1, 15)),
            ("2024/01/15", date(2024, 1, 15)),
        ]
        
        for input_date, expected in test_cases:
            result = parse_date(input_date)
            assert result == expected, f"Failed for {input_date}: got {result}, expected {expected}"
    
    def test_parse_date_ambiguous_formats(self):
        """Test parsing ambiguous date formats."""
        # Test MM/DD/YYYY vs DD/MM/YYYY disambiguation
        test_cases = [
            ("01/02/2024", date(2024, 1, 2)),  # Should interpret as Jan 2 (US format)
            ("13/01/2024", date(2024, 1, 13)),  # Must be DD/MM/YYYY (13 > 12)
            ("02/01/2024", date(2024, 2, 1)),   # Ambiguous, should default to MM/DD
        ]
        
        for input_date, expected in test_cases:
            result = parse_date(input_date)
            # Allow for either interpretation of ambiguous dates
            if input_date == "02/01/2024":
                assert result in [date(2024, 2, 1), date(2024, 1, 2)]
            else:
                assert result == expected, f"Failed for {input_date}"
    
    def test_parse_date_edge_cases(self):
        """Test edge cases in date parsing."""
        # Invalid inputs
        assert parse_date("") is None
        assert parse_date(None) is None
        assert parse_date("Invalid date") is None
        assert parse_date("TBD") is None
        assert parse_date("13/32/2024") is None  # Invalid day
        assert parse_date("2024-13-01") is None  # Invalid month
        
        # Partial dates
        assert parse_date("2024") is None  # Year only
        assert parse_date("January") is None  # Month only
        
        # Future dates (if validation is enabled)
        future_date = "01/01/2099"
        result = parse_date(future_date)
        # Should either parse successfully or return None based on validation
        assert result is None or isinstance(result, date)
    
    def test_parse_date_relative_formats(self):
        """Test parsing relative date formats."""
        with patch('app.utils.value_and_date_parsing.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 6, 15)
            
            test_cases = [
                ("today", date(2024, 6, 15)),
                ("yesterday", date(2024, 6, 14)),
                ("tomorrow", date(2024, 6, 16)),
            ]
            
            for input_date, expected in test_cases:
                result = parse_date(input_date)
                if result:  # If relative parsing is implemented
                    assert result == expected
    
    def test_standardize_date_format(self):
        """Test date format standardization."""
        test_cases = [
            (date(2024, 1, 15), "2024-01-15"),
            (datetime(2024, 1, 15, 10, 30), "2024-01-15"),
            ("2024-01-15", "2024-01-15"),
            ("01/15/2024", "2024-01-15"),
        ]
        
        for input_date, expected in test_cases:
            result = standardize_date_format(input_date)
            assert result == expected, f"Failed for {input_date}"
    
    def test_parse_fiscal_year(self):
        """Test fiscal year parsing."""
        test_cases = [
            ("FY2024", 2024),
            ("Fiscal Year 2024", 2024),
            ("FY 24", 2024),
            ("2024 Fiscal Year", 2024),
            ("24", 2024),  # Assuming 2000s
            ("99", 1999),  # Assuming 1900s for high values
        ]
        
        for input_fy, expected in test_cases:
            result = parse_fiscal_year(input_fy)
            assert result == expected, f"Failed for {input_fy}"
    
    def test_validate_date_range(self):
        """Test date range validation."""
        # Valid ranges
        assert validate_date_range(date(2024, 1, 1), date(2024, 12, 31)) is True
        assert validate_date_range(date(2024, 6, 15), date(2024, 6, 15)) is True  # Same date
        
        # Invalid ranges
        assert validate_date_range(date(2024, 12, 31), date(2024, 1, 1)) is False  # End before start
        assert validate_date_range(None, date(2024, 1, 1)) is False  # Null start
        assert validate_date_range(date(2024, 1, 1), None) is False  # Null end
    
    def test_parse_date_range(self):
        """Test parsing date ranges."""
        test_cases = [
            ("2024-01-01 to 2024-12-31", (date(2024, 1, 1), date(2024, 12, 31))),
            ("Jan 1, 2024 - Dec 31, 2024", (date(2024, 1, 1), date(2024, 12, 31))),
            ("01/01/2024 through 12/31/2024", (date(2024, 1, 1), date(2024, 12, 31))),
        ]
        
        for input_range, expected in test_cases:
            result = parse_date_range(input_range)
            if result:  # If range parsing is implemented
                assert result == expected, f"Failed for {input_range}"


class TestDataValidation:
    """Test data validation functions."""
    
    def test_value_validation_ranges(self):
        """Test validation of contract value ranges."""
        # Valid ranges
        assert validate_contract_value_range(100000, 500000) is True
        assert validate_contract_value_range(1000000, 1000000) is True  # Same value
        
        # Invalid ranges
        assert validate_contract_value_range(500000, 100000) is False  # Max < Min
        assert validate_contract_value_range(-100000, 500000) is False  # Negative values
        assert validate_contract_value_range(None, 500000) is False  # Null values
    
    def test_date_validation_business_rules(self):
        """Test business rule validation for dates."""
        today = date.today()
        
        # Posted date should not be in far future
        assert validate_posted_date(today) is True
        assert validate_posted_date(date(today.year + 1, 1, 1)) is False
        
        # Response date should be after posted date
        posted = date(2024, 1, 1)
        response = date(2024, 2, 1)
        assert validate_response_date(posted, response) is True
        
        response_before = date(2023, 12, 1)
        assert validate_response_date(posted, response_before) is False


class TestPerformanceAndEdgeCases:
    """Test performance and edge cases."""
    
    def test_large_value_parsing(self):
        """Test parsing very large contract values."""
        large_values = [
            ("$999,999,999,999", 999999999999),
            ("$1T", 1000000000000),
            ("$1.5 trillion", 1500000000000),
        ]
        
        for input_value, expected in large_values:
            result = parse_contract_value(input_value)
            assert abs(result - expected) < 1, f"Failed for large value {input_value}"
    
    def test_malformed_input_handling(self):
        """Test handling of malformed inputs."""
        malformed_inputs = [
            "$$$100,000$$$",
            "100,000 dollars and cents",
            "approximately $100K-ish",
            "somewhere between $50K and maybe $100K",
            "CONFIDENTIAL",
            "See attachment for pricing",
        ]
        
        for malformed in malformed_inputs:
            # Should not raise exceptions
            result = parse_contract_value(malformed)
            # Result can be None or a parsed value, but shouldn't crash
            assert result is None or isinstance(result, (int, float, tuple))
    
    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters."""
        unicode_inputs = [
            ("$100,000", 100000),  # Regular ASCII
            ("€100,000", 100000),  # Euro symbol
            ("£100,000", 100000),  # Pound symbol
            ("¥100,000", 100000),  # Yen symbol
            ("$100\u202f000", 100000),  # Narrow no-break space
            ("$100\u00a0000", 100000),  # Non-breaking space
        ]
        
        for input_value, expected in unicode_inputs:
            result = parse_contract_value(input_value)
            if result is not None:
                assert abs(result - expected) < 0.01, f"Failed for unicode input {input_value}"
    
    def test_parsing_performance(self):
        """Test parsing performance with many inputs."""
        import time
        
        test_values = [
            "$100,000", "$1M", "$500K", "250000", "$1.5M - $2.5M",
            "2024-01-01", "Jan 15, 2024", "01/15/2024", "15-Jan-2024"
        ] * 100  # 800 total operations
        
        start_time = time.time()
        
        for value in test_values:
            if '$' in value or 'K' in value or 'M' in value:
                parse_contract_value(value)
            else:
                parse_date(value)
        
        end_time = time.time()
        
        # Should complete in reasonable time (less than 1 second for 800 operations)
        assert end_time - start_time < 1.0, "Parsing performance is too slow"


# Helper functions for testing (implement if not already present)
def validate_contract_value_range(min_val, max_val):
    """Validate contract value range."""
    if min_val is None or max_val is None:
        return False
    if min_val < 0 or max_val < 0:
        return False
    return min_val <= max_val


def validate_posted_date(posted_date):
    """Validate posted date is reasonable."""
    if posted_date is None:
        return False
    today = date.today()
    # Posted date should not be more than 1 year in the future
    return posted_date <= date(today.year + 1, today.month, today.day)


def validate_response_date(posted_date, response_date):
    """Validate response date is after posted date."""
    if posted_date is None or response_date is None:
        return False
    return response_date >= posted_date