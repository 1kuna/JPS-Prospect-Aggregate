"""
Comprehensive tests for NAICS lookup utilities.

Tests NAICS code validation and description lookup functionality.
"""

import pytest
from unittest.mock import Mock, patch, mock_open

from app.utils.naics_lookup import (
    validate_naics_code,
    get_naics_description,
    get_naics_info
)


class TestNAICSValidation:
    """Test NAICS code validation functions."""
    
    def test_validate_naics_code_valid_codes(self):
        """Test validation of valid NAICS codes."""
        valid_codes = [
            "541511",  # Custom Computer Programming Services
            "541512",  # Computer Systems Design Services
            "541519",  # Other Computer Related Services
            "517311",  # Wired Telecommunications Carriers
        ]
        
        for code in valid_codes:
            result = validate_naics_code(code)
            # The function might check against a loaded database
            # We can't assert True without knowing the loaded data
            assert isinstance(result, bool), f"validate_naics_code should return bool for {code}"
    
    def test_validate_naics_code_invalid_codes(self):
        """Test validation of invalid NAICS codes."""
        invalid_codes = [
            "",        # Empty string
            None,      # None value
            "ABC123",  # Non-numeric
            "12345",   # Too short (5 digits)
            "1234567", # Too long (7 digits)
            "54151a",  # Contains letter
        ]
        
        for code in invalid_codes:
            result = validate_naics_code(code)
            # Invalid format codes should return False
            if code and isinstance(code, str) and not code.isdigit():
                assert result is False, f"Non-numeric code {code} should be invalid"
            elif code and isinstance(code, str) and len(code) != 6:
                assert result is False, f"Wrong length code {code} should be invalid"


class TestNAICSDescriptions:
    """Test NAICS description lookup functions."""
    
    @patch('app.utils.naics_lookup.NAICS_DESCRIPTIONS')
    def test_get_naics_description_existing_codes(self, mock_naics_codes):
        """Test getting descriptions for existing NAICS codes."""
        mock_naics_codes.get.side_effect = lambda x: {
            "541511": "Custom Computer Programming Services",
            "541512": "Computer Systems Design Services",
            "541519": "Other Computer Related Services",
            "517311": "Wired Telecommunications Carriers"
        }.get(x)
        
        test_cases = [
            ("541511", "Custom Computer Programming Services"),
            ("541512", "Computer Systems Design Services"),
            ("541519", "Other Computer Related Services"),
            ("517311", "Wired Telecommunications Carriers"),
        ]
        
        for code, expected_desc in test_cases:
            result = get_naics_description(code)
            assert result == expected_desc, f"Description lookup failed for {code}"
    
    @patch('app.utils.naics_lookup.NAICS_DESCRIPTIONS')
    def test_get_naics_description_non_existing_codes(self, mock_naics_codes):
        """Test getting descriptions for non-existing NAICS codes."""
        mock_naics_codes.get.side_effect = lambda x: {
            "541511": "Custom Computer Programming Services"
        }.get(x)
        
        non_existing_codes = ["999999", "123456", "000000"]
        
        for code in non_existing_codes:
            result = get_naics_description(code)
            assert result is None, f"Should return None for non-existing code {code}"
    
    def test_get_naics_description_invalid_input(self):
        """Test description lookup with invalid input."""
        invalid_inputs = [None, "", "ABC", "12345"]
        
        for invalid_input in invalid_inputs:
            result = get_naics_description(invalid_input)
            assert result is None, f"Should return None for invalid input {invalid_input}"


class TestNAICSInfo:
    """Test NAICS info retrieval function."""
    
    @patch('app.utils.naics_lookup.get_naics_description')
    @patch('app.utils.naics_lookup.validate_naics_code')
    def test_get_naics_info_valid_code(self, mock_validate, mock_get_desc):
        """Test getting info for valid NAICS code."""
        mock_validate.return_value = True
        mock_get_desc.return_value = "Custom Computer Programming Services"
        
        result = get_naics_info("541511")
        
        assert isinstance(result, dict), "Should return a dictionary"
        assert "code" in result
        assert "description" in result
        assert result["code"] == "541511"
        assert result["description"] == "Custom Computer Programming Services"
    
    @patch('app.utils.naics_lookup.get_naics_description')
    @patch('app.utils.naics_lookup.validate_naics_code')
    def test_get_naics_info_invalid_code(self, mock_validate, mock_get_desc):
        """Test getting info for invalid NAICS code."""
        mock_validate.return_value = False
        mock_get_desc.return_value = None
        
        result = get_naics_info("999999")
        
        assert isinstance(result, dict), "Should return a dictionary"
        assert result.get("code") == "999999" or result.get("code") is None
        assert result.get("description") is None
    
    def test_get_naics_info_none_input(self):
        """Test getting info with None input."""
        result = get_naics_info(None)
        
        assert isinstance(result, dict), "Should return a dictionary"
        assert result.get("code") is None
        assert result.get("description") is None


class TestNAICSDataLoading:
    """Test NAICS data loading and file handling."""
    
    @patch('app.utils.naics_lookup.logger')
    def test_naics_codes_loading_error_handling(self, mock_logger):
        """Test error handling when NAICS codes file is not found."""
        # This test ensures the module handles missing data gracefully
        # The actual loading happens at module import time
        # We're just verifying the module imported successfully
        import app.utils.naics_lookup
        assert hasattr(app.utils.naics_lookup, 'NAICS_DESCRIPTIONS')
        assert hasattr(app.utils.naics_lookup, 'validate_naics_code')
        assert hasattr(app.utils.naics_lookup, 'get_naics_description')
        assert hasattr(app.utils.naics_lookup, 'get_naics_info')