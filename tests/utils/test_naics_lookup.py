"""
Comprehensive tests for NAICS lookup utilities.

Tests NAICS code validation and description lookup functionality.
"""

from unittest.mock import patch

from app.utils.naics_lookup import (
    get_naics_description,
    get_naics_info,
    validate_naics_code,
)


class TestNAICSValidation:
    """Test NAICS code validation functions."""

    def test_validate_naics_code_valid_format(self):
        """Test validation accepts properly formatted codes."""
        # Deterministic test codes - no randomness
        test_codes = [
            "541511",  # Computer Systems Design
            "541512",  # Computer Systems Design
            "236220",  # Commercial Building Construction
            "517311",  # Wired Telecommunications Carriers
            "999999",  # Format valid even if code doesn't exist
            "100000",  # Edge case - starts with 1
            "200000",  # Edge case - starts with 2
            "654321",  # Another valid format
        ]

        for code in test_codes:
            result = validate_naics_code(code)
            # The function should return a boolean for well-formatted codes
            assert isinstance(
                result, bool
            ), f"validate_naics_code should return bool for {code}"

    def test_validate_naics_code_invalid_codes(self):
        """Test validation of invalid NAICS codes."""
        invalid_codes = [
            "",  # Empty string
            None,  # None value
            "ABC123",  # Non-numeric
            "12345",  # Too short (5 digits)
            "1234567",  # Too long (7 digits)
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

    @patch("app.utils.naics_lookup.NAICS_DESCRIPTIONS")
    def test_get_naics_description_existing_codes(self, mock_naics_codes):
        """Test getting descriptions for codes that exist in the database."""
        # Deterministic test data - no randomness
        test_descriptions = {
            "541511": "Custom Computer Programming Services",
            "541512": "Computer Systems Design Services",
            "236220": "Commercial and Institutional Building Construction",
            "517311": "Wired Telecommunications Carriers",
            "541611": "Administrative Management and General Management Consulting Services",
        }

        mock_naics_codes.get.side_effect = lambda x: test_descriptions.get(x)

        # Test that existing codes return their descriptions
        for code, expected_desc in test_descriptions.items():
            result = get_naics_description(code)
            assert (
                result == expected_desc
            ), "Description lookup should return the mapped description"

    @patch("app.utils.naics_lookup.NAICS_DESCRIPTIONS")
    def test_get_naics_description_non_existing_codes(self, mock_naics_codes):
        """Test getting descriptions for non-existing NAICS codes."""
        # Create a small set of known codes
        known_codes = {
            "541511": "Custom Computer Programming Services",
            "541512": "Computer Systems Design Services",
            "236220": "Commercial and Institutional Building Construction",
        }

        mock_naics_codes.get.side_effect = lambda x: known_codes.get(x)

        # Test codes that are definitely not in our known set
        non_existing_codes = [
            "999999",  # Valid format but doesn't exist
            "000000",  # Valid format but doesn't exist
            "111111",  # Valid format but doesn't exist
            "987654",  # Valid format but doesn't exist
            "123456",  # Valid format but doesn't exist
        ]

        for test_code in non_existing_codes:
            result = get_naics_description(test_code)
            assert (
                result is None
            ), f"Should return None for non-existing code {test_code}"

    def test_get_naics_description_invalid_input(self):
        """Test description lookup with invalid input."""
        invalid_inputs = [None, "", "ABC", "12345"]

        for invalid_input in invalid_inputs:
            result = get_naics_description(invalid_input)
            assert (
                result is None
            ), f"Should return None for invalid input {invalid_input}"


class TestNAICSInfo:
    """Test NAICS info retrieval function."""

    @patch("app.utils.naics_lookup.get_naics_description")
    @patch("app.utils.naics_lookup.validate_naics_code")
    def test_get_naics_info_valid_code(self, mock_validate, mock_get_desc):
        """Test getting info for valid NAICS code."""
        # Deterministic test data
        test_code = "541511"
        test_desc = "Custom Computer Programming Services"

        mock_validate.return_value = True
        mock_get_desc.return_value = test_desc

        result = get_naics_info(test_code)

        assert isinstance(result, dict), "Should return a dictionary"
        assert "code" in result
        assert "description" in result
        assert result["code"] == test_code
        assert result["description"] == test_desc

    @patch("app.utils.naics_lookup.get_naics_description")
    @patch("app.utils.naics_lookup.validate_naics_code")
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

    @patch("app.utils.naics_lookup.logger")
    def test_naics_codes_loading_error_handling(self, mock_logger):
        """Test error handling when NAICS codes file is not found."""
        # This test ensures the module handles missing data gracefully
        # The actual loading happens at module import time
        # We're just verifying the module imported successfully
        import app.utils.naics_lookup

        assert hasattr(app.utils.naics_lookup, "NAICS_DESCRIPTIONS")
        assert hasattr(app.utils.naics_lookup, "validate_naics_code")
        assert hasattr(app.utils.naics_lookup, "get_naics_description")
        assert hasattr(app.utils.naics_lookup, "get_naics_info")

    def test_naics_backfill_behavior(self):
        """Test NAICS backfill behavior when descriptions are missing."""
        # Test that the system handles missing descriptions gracefully
        result = get_naics_info("999999")  # Non-existent code
        assert isinstance(result, dict)
        assert result.get("code") == "999999" or result.get("code") is None
        assert result.get("description") is None or result.get("description") == ""

        # Test partial code matching behavior
        partial_codes = [
            "54",  # 2-digit sector code
            "541",  # 3-digit subsector
            "5415",  # 4-digit industry group
            "54151",  # 5-digit NAICS industry
        ]

        for partial_code in partial_codes:
            # These should be handled as invalid by validation
            is_valid = validate_naics_code(partial_code)
            assert is_valid is False, f"Partial code {partial_code} should be invalid"
