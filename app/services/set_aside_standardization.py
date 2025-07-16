"""
Set-aside standardization service for normalizing set-aside field values.
This service provides mapping and LLM-based classification of set-aside types.
"""

from typing import Dict, List, Optional, Tuple
import re
from enum import Enum

class StandardSetAside(Enum):
    """Simplified standardized set-aside types for business development focus"""
    SMALL_BUSINESS = "Small Business"
    EIGHT_A = "8(a)"
    HUBZONE = "HUBZone"
    WOMEN_OWNED = "Women-Owned"
    VETERAN_OWNED = "Veteran-Owned"
    FULL_AND_OPEN = "Full and Open"
    SOLE_SOURCE = "Sole Source"
    NOT_AVAILABLE = "N/A"

class SetAsideStandardizer:
    """Service for standardizing set-aside field values"""
    
    def __init__(self):
        self.mapping_rules = self._build_mapping_rules()
        self.pattern_rules = self._build_pattern_rules()
    
    def _build_mapping_rules(self) -> Dict[str, StandardSetAside]:
        """Build exact mapping rules for known values"""
        return {
            # Small Business (consolidates all small business types)
            "small business": StandardSetAside.SMALL_BUSINESS,
            "small business set-aside": StandardSetAside.SMALL_BUSINESS,
            "small business set aside - total": StandardSetAside.SMALL_BUSINESS,
            "small business total set-aside": StandardSetAside.SMALL_BUSINESS,
            "determined small business set aside - total": StandardSetAside.SMALL_BUSINESS,
            "small disadvantaged business": StandardSetAside.SMALL_BUSINESS,
            "small disadvantaged business (sdb)": StandardSetAside.SMALL_BUSINESS,
            "other than small business": StandardSetAside.SMALL_BUSINESS,
            
            # 8(a) Program (consolidates competitive/sole source)
            "8(a) competitive": StandardSetAside.EIGHT_A,
            "8(a) sole source": StandardSetAside.EIGHT_A,
            "8(a) non-competitive": StandardSetAside.EIGHT_A,
            
            # HUBZone (consolidates competitive/sole source)
            "hubzone": StandardSetAside.HUBZONE,
            "hubzone sole source": StandardSetAside.HUBZONE,
            
            # Women-Owned (consolidates WOSB/EDWOSB)
            "women-owned small business (wosb)": StandardSetAside.WOMEN_OWNED,
            "woman owned small business": StandardSetAside.WOMEN_OWNED,
            "wosb competitive": StandardSetAside.WOMEN_OWNED,
            "economically disadvantaged women-owned small business (edwosb)": StandardSetAside.WOMEN_OWNED,
            
            # Veteran-Owned (consolidates all veteran programs)
            "service-disabled veteran owned small business": StandardSetAside.VETERAN_OWNED,
            "set-aside - service disabled veteran owned small business": StandardSetAside.VETERAN_OWNED,
            "sdvosb competitive": StandardSetAside.VETERAN_OWNED,
            "sdvosb sole source": StandardSetAside.VETERAN_OWNED,
            "service-disabled vet-owned": StandardSetAside.VETERAN_OWNED,
            "set-aside - veteran": StandardSetAside.VETERAN_OWNED,
            
            # Full and Open (consolidates open competition types)
            "full and open": StandardSetAside.FULL_AND_OPEN,
            "full": StandardSetAside.FULL_AND_OPEN,
            "full and open/unrestricted": StandardSetAside.FULL_AND_OPEN,
            "unrestricted": StandardSetAside.FULL_AND_OPEN,
            "competitive": StandardSetAside.FULL_AND_OPEN,
            
            # Sole Source
            "sole source": StandardSetAside.SOLE_SOURCE,
            
            # Common non-informative values (with punctuation variations)
            "determined": StandardSetAside.NOT_AVAILABLE,
            "currently this information not available": StandardSetAside.NOT_AVAILABLE,
            "currently, this information is not available": StandardSetAside.NOT_AVAILABLE,
            "currently this information is not available": StandardSetAside.NOT_AVAILABLE,
            "[tbd]": StandardSetAside.NOT_AVAILABLE,
            "tbd": StandardSetAside.NOT_AVAILABLE,
            "to be determined": StandardSetAside.NOT_AVAILABLE,
            "undecided": StandardSetAside.NOT_AVAILABLE,
            "other": StandardSetAside.NOT_AVAILABLE,
            "follow- action": StandardSetAside.NOT_AVAILABLE,
            "follow-action": StandardSetAside.NOT_AVAILABLE,
            "partial": StandardSetAside.NOT_AVAILABLE,
            "broad agency announcement (baa)": StandardSetAside.NOT_AVAILABLE,
            "mandatory source": StandardSetAside.NOT_AVAILABLE,
        }
    
    def _build_pattern_rules(self) -> List[Tuple[str, StandardSetAside]]:
        """Build regex pattern rules for fuzzy matching"""
        return [
            # Small Business patterns (consolidates all small business types)
            (r'small\s+business\s+set[- ]?aside', StandardSetAside.SMALL_BUSINESS),
            (r'small\s+business(?!\s+other)', StandardSetAside.SMALL_BUSINESS),
            (r'\bsb\b(?!\s*(competitive|sole|source))', StandardSetAside.SMALL_BUSINESS),
            (r'small\s+disadvantaged\s+business', StandardSetAside.SMALL_BUSINESS),
            (r'\bsdb\b', StandardSetAside.SMALL_BUSINESS),
            (r'other\s+than\s+small\s+business', StandardSetAside.SMALL_BUSINESS),
            
            # 8(a) patterns (consolidates competitive/sole source)
            (r'8\s*\(\s*a\s*\)', StandardSetAside.EIGHT_A),
            (r'eight\s*a', StandardSetAside.EIGHT_A),
            
            # HUBZone patterns (consolidates competitive/sole source)
            (r'hub\s*zone', StandardSetAside.HUBZONE),
            
            # Women-owned patterns (consolidates WOSB/EDWOSB)
            (r'economically\s+disadvantaged\s+women[- ]?owned', StandardSetAside.WOMEN_OWNED),
            (r'edwosb', StandardSetAside.WOMEN_OWNED),
            (r'women?[- ]?owned\s+small\s+business', StandardSetAside.WOMEN_OWNED),
            (r'wosb', StandardSetAside.WOMEN_OWNED),
            (r'women?\s+owned', StandardSetAside.WOMEN_OWNED),
            
            # Veteran patterns (consolidates all veteran programs)
            (r'service[- ]?disabled\s+veteran[- ]?owned', StandardSetAside.VETERAN_OWNED),
            (r'sdvosb', StandardSetAside.VETERAN_OWNED),
            (r'veteran[- ]?owned', StandardSetAside.VETERAN_OWNED),
            (r'\bvosb\b', StandardSetAside.VETERAN_OWNED),
            (r'service\s+disabled', StandardSetAside.VETERAN_OWNED),
            
            # Open competition patterns (consolidates unrestricted/competitive)
            (r'full\s+and\s+open', StandardSetAside.FULL_AND_OPEN),
            (r'unrestricted', StandardSetAside.FULL_AND_OPEN),
            (r'\bfull\b(?!\s+and\s+open)', StandardSetAside.FULL_AND_OPEN),
            
            # Sole Source patterns
            (r'sole\s+source', StandardSetAside.SOLE_SOURCE),
        ]
    
    def standardize_set_aside(self, value: Optional[str]) -> StandardSetAside:
        """
        Standardize a set-aside value using mapping rules and pattern matching
        
        Args:
            value: Raw set-aside value to standardize
            
        Returns:
            StandardSetAside enum value
        """
        if not value or not value.strip():
            return StandardSetAside.NOT_AVAILABLE
        
        # Clean the value
        cleaned = self._clean_value(value)
        
        # Try exact mapping first (case-insensitive)
        lower_cleaned = cleaned.lower()
        if lower_cleaned in self.mapping_rules:
            return self.mapping_rules[lower_cleaned]
        
        # Try pattern matching
        for pattern, set_aside_type in self.pattern_rules:
            if re.search(pattern, cleaned, re.IGNORECASE):
                return set_aside_type
        
        # If no match found, return N/A
        return StandardSetAside.NOT_AVAILABLE
    
    def _clean_value(self, value: str) -> str:
        """Clean a set-aside value for processing"""
        if not value:
            return ""
        
        # Convert to string and strip
        value = str(value).strip()
        
        # Remove common contamination patterns
        # Remove dates (YYYY-MM-DD, MM/DD/YYYY, etc.)
        value = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '', value)
        value = re.sub(r'\b\d{1,2}/\d{1,2}/\d{4}\b', '', value)
        
        # Remove states and common location indicators
        value = re.sub(r'\b[A-Z]{2}\b(?!\s*(competitive|sole|source))', '', value)
        value = re.sub(r'\bUnited States\b', '', value, flags=re.IGNORECASE)
        value = re.sub(r'\bUSA\b', '', value, flags=re.IGNORECASE)
        value = re.sub(r'\bU\.S\.\b', '', value, flags=re.IGNORECASE)
        
        # Remove extra whitespace and common separators
        value = re.sub(r'[,;|]+', ' ', value)
        value = re.sub(r'\s+', ' ', value)
        value = value.strip()
        
        return value
    
    def get_llm_prompt(self) -> str:
        """Get the LLM prompt for set-aside classification"""
        standard_types = [e.value for e in StandardSetAside]
        
        return f"""You are a federal procurement specialist. Analyze the given set-aside field value and classify it into one of these standardized categories:

{chr(10).join(f"- {t}" for t in standard_types)}

Rules:
1. Use "N/A" for unclear, missing, or non-informative values like "TBD", "Determined", "Other"
2. "Small Business" includes all small business set-asides (SDB, small business total, etc.)
3. "8(a)" includes both competitive and sole source 8(a) awards
4. "HUBZone" includes both competitive and sole source HUBZone awards
5. "Women-Owned" includes WOSB, EDWOSB, and all women-owned variations
6. "Veteran-Owned" includes SDVOSB, VOSB, and all veteran-owned variations
7. "Full and Open" includes unrestricted, competitive, and open competition
8. "Sole Source" is only for explicit sole source procurements (not set-aside types)

Input: "{{}}"

Respond with only the exact standardized category name."""

    def get_confidence_score(self, original_value: str, standardized: StandardSetAside) -> float:
        """
        Calculate confidence score for a standardization
        
        Args:
            original_value: Original set-aside value
            standardized: Standardized result
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not original_value or not original_value.strip():
            return 1.0 if standardized == StandardSetAside.NOT_AVAILABLE else 0.0
        
        cleaned = self._clean_value(original_value).lower()
        
        # High confidence for exact matches
        if cleaned in self.mapping_rules:
            return 0.95
        
        # Medium-high confidence for pattern matches
        for pattern, set_aside_type in self.pattern_rules:
            if re.search(pattern, cleaned, re.IGNORECASE) and set_aside_type == standardized:
                return 0.80
        
        # Low confidence if we couldn't match and returned N/A
        if standardized == StandardSetAside.NOT_AVAILABLE:
            return 0.60
        
        # Very low confidence for other cases
        return 0.30