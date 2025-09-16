"""
Unit tests for set-aside standardization service.

Tests the mapping of various set-aside formats to standard enum values.
"""

import pytest

from app.services.set_aside_standardization import (
    StandardSetAside,
    SetAsideStandardizer,
)


class TestSetAsideStandardization:
    """Test suite for set-aside standardization."""

    @pytest.fixture
    def standardizer(self):
        """Create a standardizer instance."""
        return SetAsideStandardizer()

    def test_standard_set_aside_enum_properties(self):
        """Test that StandardSetAside enum has correct properties."""
        # Test code property
        assert StandardSetAside.SMALL_BUSINESS.code == "SMALL_BUSINESS"
        assert StandardSetAside.EIGHT_A.code == "EIGHT_A"
        assert StandardSetAside.HUBZONE.code == "HUBZONE"
        assert StandardSetAside.WOMEN_OWNED.code == "WOMEN_OWNED"
        assert StandardSetAside.VETERAN_OWNED.code == "VETERAN_OWNED"
        assert StandardSetAside.FULL_AND_OPEN.code == "FULL_AND_OPEN"
        assert StandardSetAside.SOLE_SOURCE.code == "SOLE_SOURCE"
        assert StandardSetAside.NOT_AVAILABLE.code == "NOT_AVAILABLE"

        # Test label property
        assert StandardSetAside.SMALL_BUSINESS.label == "Small Business"
        assert StandardSetAside.EIGHT_A.label == "8(a)"
        assert StandardSetAside.HUBZONE.label == "HUBZone"
        assert StandardSetAside.WOMEN_OWNED.label == "Women-Owned"
        assert StandardSetAside.VETERAN_OWNED.label == "Veteran-Owned"
        assert StandardSetAside.FULL_AND_OPEN.label == "Full and Open"
        assert StandardSetAside.SOLE_SOURCE.label == "Sole Source"
        assert StandardSetAside.NOT_AVAILABLE.label == "N/A"

    def test_enum_value_access(self):
        """Test that enum values are accessible."""
        # Test .value access (same as label)
        assert StandardSetAside.SMALL_BUSINESS.value == "Small Business"
        assert StandardSetAside.EIGHT_A.value == "8(a)"

        # Test .name access
        assert StandardSetAside.SMALL_BUSINESS.name == "SMALL_BUSINESS"
        assert StandardSetAside.EIGHT_A.name == "EIGHT_A"

    def test_llm_prompt_generation(self, standardizer):
        """Test that LLM prompt is generated correctly."""
        prompt = standardizer.get_llm_prompt()

        # Should contain all standard types
        assert "Small Business" in prompt
        assert "8(a)" in prompt
        assert "HUBZone" in prompt
        assert "Women-Owned" in prompt
        assert "Veteran-Owned" in prompt
        assert "Full and Open" in prompt
        assert "Sole Source" in prompt
        assert "N/A" in prompt

        # Should contain classification rules
        assert "CLASSIFICATION RULES" in prompt
        assert "small business set-asides" in prompt.lower()
        assert "8(a) program" in prompt.lower()
        assert "hubzone program" in prompt.lower()
        assert "wosb" in prompt.lower()
        assert "sdvosb" in prompt.lower()
        assert "unrestricted competition" in prompt.lower()

        # Should contain examples
        assert "EXAMPLES" in prompt
        assert "Small Business Set-Aside" in prompt
        assert "→ Small Business" in prompt
        assert "8(a) Competitive" in prompt
        assert "→ 8(a)" in prompt

    def test_prompt_formatting(self, standardizer):
        """Test that prompt has proper formatting placeholders."""
        prompt = standardizer.get_llm_prompt()

        # Should have placeholder for input
        assert "{{}}" in prompt or "{}" in prompt

        # Should instruct to respond with exact category
        assert "Respond with ONLY the exact category name" in prompt

    def test_prompt_handles_various_inputs(self, standardizer):
        """Test that prompt describes handling of various input formats."""
        prompt = standardizer.get_llm_prompt()

        # Should describe different input formats
        assert "Single field:" in prompt
        assert "Multiple fields:" in prompt
        assert "Program only:" in prompt

        # Should handle edge cases
        assert "TBD" in prompt
        assert "Currently not available" in prompt
        assert "unclear" in prompt.lower() or "missing" in prompt.lower()

    def test_prompt_prioritization_rules(self, standardizer):
        """Test that prompt includes prioritization guidance."""
        prompt = standardizer.get_llm_prompt()

        # Should mention prioritizing specific information
        assert "prioritize the most specific information" in prompt

    def test_all_enum_values_in_prompt(self, standardizer):
        """Test that all enum values are included in the prompt."""
        prompt = standardizer.get_llm_prompt()

        # Get all standard types from enum
        all_types = [e.value for e in StandardSetAside]

        # Each should be in the prompt
        for set_aside_type in all_types:
            assert set_aside_type in prompt, f"'{set_aside_type}' should be in prompt"

    def test_prompt_includes_mapping_examples(self, standardizer):
        """Test that prompt includes clear mapping examples."""
        prompt = standardizer.get_llm_prompt()

        # Test for specific mapping examples
        test_cases = [
            ("Small Business Set-Aside", "Small Business"),
            ("8(a) Competitive", "8(a)"),
            ("WOSB Sole Source", "Women-Owned"),
            ("Service-Disabled Veteran Owned", "Veteran-Owned"),
            ("HubZone", "HUBZone"),
            ("Unrestricted", "Full and Open"),
            ("TBD", "N/A"),
        ]

        for input_val, expected_output in test_cases:
            assert (
                input_val in prompt
            ), f"Example input '{input_val}' should be in prompt"
            # The arrow format should be present
            assert "→" in prompt, "Prompt should use arrow notation for examples"

    def test_prompt_handles_mixed_case(self, standardizer):
        """Test that prompt addresses case variations."""
        prompt = standardizer.get_llm_prompt()

        # Should handle case variations (implicit in HubZone vs HUBZone example)
        assert "HubZone" in prompt or "HUBZone" in prompt

    def test_prompt_handles_abbreviations(self, standardizer):
        """Test that prompt handles common abbreviations."""
        prompt = standardizer.get_llm_prompt()

        # Should handle common abbreviations
        assert "WOSB" in prompt  # Women-Owned Small Business
        assert "SDVOSB" in prompt  # Service-Disabled Veteran-Owned Small Business
        assert "EDWOSB" in prompt  # Economically Disadvantaged Women-Owned

    def test_standardizer_initialization(self):
        """Test that standardizer initializes correctly."""
        standardizer = SetAsideStandardizer()
        # Should initialize without errors
        assert standardizer is not None

        # Should have get_llm_prompt method
        assert hasattr(standardizer, "get_llm_prompt")
        assert callable(standardizer.get_llm_prompt)

    def test_enum_completeness(self):
        """Test that enum covers all expected set-aside types."""
        expected_types = [
            "SMALL_BUSINESS",
            "EIGHT_A",
            "HUBZONE",
            "WOMEN_OWNED",
            "VETERAN_OWNED",
            "FULL_AND_OPEN",
            "SOLE_SOURCE",
            "NOT_AVAILABLE",
        ]

        actual_types = [e.name for e in StandardSetAside]

        for expected in expected_types:
            assert (
                expected in actual_types
            ), f"Expected set-aside type '{expected}' not found"

        # Verify no extra types
        assert len(actual_types) == len(
            expected_types
        ), "Unexpected set-aside types found"

    def test_prompt_structure(self, standardizer):
        """Test that prompt has the expected structure."""
        prompt = standardizer.get_llm_prompt()

        # Should have major sections
        assert "CLASSIFICATION RULES:" in prompt
        assert "INPUT FORMATS:" in prompt
        assert "EXAMPLES:" in prompt
        assert "Input:" in prompt

        # Should end with clear instruction
        assert "Respond with ONLY the exact category name" in prompt
