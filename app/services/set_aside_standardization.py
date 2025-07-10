"""
Set-aside standardization service for normalizing set-aside field values.
This service provides mapping and LLM-based classification of set-aside types.
"""

from typing import Dict, List, Optional, Tuple
import re
from enum import Enum

class StandardSetAside(Enum):
    """Standardized set-aside types based on federal procurement regulations"""
    SMALL_BUSINESS = "Small Business"
    SMALL_BUSINESS_TOTAL = "Small Business Total"
    EIGHT_A_COMPETITIVE = "8(a) Competitive"
    EIGHT_A_SOLE_SOURCE = "8(a) Sole Source"
    HUBZONE = "HUBZone"
    HUBZONE_SOLE_SOURCE = "HUBZone Sole Source"
    WOSB = "Women-Owned Small Business"
    EDWOSB = "Economically Disadvantaged Women-Owned Small Business"
    SDVOSB = "Service-Disabled Veteran-Owned Small Business"
    SDVOSB_SOLE_SOURCE = "Service-Disabled Veteran-Owned Small Business Sole Source"
    SDB = "Small Disadvantaged Business"
    VOSB = "Veteran-Owned Small Business"
    FULL_AND_OPEN = "Full and Open Competition"
    UNRESTRICTED = "Unrestricted"
    SOLE_SOURCE = "Sole Source"
    OTHER_THAN_SMALL = "Other Than Small Business"
    NOT_AVAILABLE = "N/A"

class SetAsideStandardizer:
    """Service for standardizing set-aside field values"""
    
    def __init__(self):
        self.mapping_rules = self._build_mapping_rules()
        self.pattern_rules = self._build_pattern_rules()
    
    def _build_mapping_rules(self) -> Dict[str, StandardSetAside]:
        """Build exact mapping rules for known values"""
        return {
            # Exact matches (case-insensitive)
            "small business": StandardSetAside.SMALL_BUSINESS,
            "small business set-aside": StandardSetAside.SMALL_BUSINESS_TOTAL,
            "small business set aside - total": StandardSetAside.SMALL_BUSINESS_TOTAL,
            "small business total set-aside": StandardSetAside.SMALL_BUSINESS_TOTAL,
            "determined small business set aside - total": StandardSetAside.SMALL_BUSINESS_TOTAL,
            "8(a) competitive": StandardSetAside.EIGHT_A_COMPETITIVE,
            "8(a) sole source": StandardSetAside.EIGHT_A_SOLE_SOURCE,
            "8(a) non-competitive": StandardSetAside.EIGHT_A_SOLE_SOURCE,
            "hubzone": StandardSetAside.HUBZONE,
            "hubzone sole source": StandardSetAside.HUBZONE_SOLE_SOURCE,
            "women-owned small business (wosb)": StandardSetAside.WOSB,
            "woman owned small business": StandardSetAside.WOSB,
            "wosb competitive": StandardSetAside.WOSB,
            "economically disadvantaged women-owned small business (edwosb)": StandardSetAside.EDWOSB,
            "service-disabled veteran owned small business": StandardSetAside.SDVOSB,
            "set-aside - service disabled veteran owned small business": StandardSetAside.SDVOSB,
            "sdvosb competitive": StandardSetAside.SDVOSB,
            "sdvosb sole source": StandardSetAside.SDVOSB_SOLE_SOURCE,
            "service-disabled vet-owned": StandardSetAside.SDVOSB,
            "small disadvantaged business": StandardSetAside.SDB,
            "small disadvantaged business (sdb)": StandardSetAside.SDB,
            "set-aside - veteran": StandardSetAside.VOSB,
            "full and open": StandardSetAside.FULL_AND_OPEN,
            "full": StandardSetAside.FULL_AND_OPEN,
            "full and open/unrestricted": StandardSetAside.UNRESTRICTED,
            "competitive": StandardSetAside.FULL_AND_OPEN,
            "sole source": StandardSetAside.SOLE_SOURCE,
            "other than small business": StandardSetAside.OTHER_THAN_SMALL,
            
            # Common non-informative values
            "determined": StandardSetAside.NOT_AVAILABLE,
            "currently this information not available": StandardSetAside.NOT_AVAILABLE,
            "[tbd]": StandardSetAside.NOT_AVAILABLE,
            "tbd": StandardSetAside.NOT_AVAILABLE,
            "undecided": StandardSetAside.NOT_AVAILABLE,
            "other": StandardSetAside.NOT_AVAILABLE,
            "follow- action": StandardSetAside.NOT_AVAILABLE,
            "partial": StandardSetAside.NOT_AVAILABLE,
            "broad agency announcement (baa)": StandardSetAside.NOT_AVAILABLE,
            "mandatory source": StandardSetAside.NOT_AVAILABLE,
        }
    
    def _build_pattern_rules(self) -> List[Tuple[str, StandardSetAside]]:
        """Build regex pattern rules for fuzzy matching"""
        return [
            # Small Business patterns
            (r'small\s+business\s+set[- ]?aside', StandardSetAside.SMALL_BUSINESS_TOTAL),
            (r'small\s+business(?!\s+other)', StandardSetAside.SMALL_BUSINESS),
            (r'\bsb\b(?!\s*(competitive|sole|source))', StandardSetAside.SMALL_BUSINESS),
            
            # 8(a) patterns  
            (r'8\s*\(\s*a\s*\)\s*competitive', StandardSetAside.EIGHT_A_COMPETITIVE),
            (r'8\s*\(\s*a\s*\)\s*(sole\s*source|non[- ]?competitive)', StandardSetAside.EIGHT_A_SOLE_SOURCE),
            (r'eight\s*a\s*competitive', StandardSetAside.EIGHT_A_COMPETITIVE),
            
            # HUBZone patterns
            (r'hub\s*zone\s*sole\s*source', StandardSetAside.HUBZONE_SOLE_SOURCE),
            (r'hub\s*zone', StandardSetAside.HUBZONE),
            
            # Women-owned patterns
            (r'economically\s+disadvantaged\s+women[- ]?owned', StandardSetAside.EDWOSB),
            (r'edwosb', StandardSetAside.EDWOSB),
            (r'women?[- ]?owned\s+small\s+business', StandardSetAside.WOSB),
            (r'wosb', StandardSetAside.WOSB),
            
            # Veteran patterns
            (r'service[- ]?disabled\s+veteran[- ]?owned', StandardSetAside.SDVOSB),
            (r'sdvosb\s*sole\s*source', StandardSetAside.SDVOSB_SOLE_SOURCE),
            (r'sdvosb', StandardSetAside.SDVOSB),
            (r'veteran[- ]?owned', StandardSetAside.VOSB),
            (r'\bvosb\b', StandardSetAside.VOSB),
            
            # Disadvantaged patterns
            (r'small\s+disadvantaged\s+business', StandardSetAside.SDB),
            (r'\bsdb\b', StandardSetAside.SDB),
            
            # Open competition patterns
            (r'full\s+and\s+open\s*/?\s*unrestricted', StandardSetAside.UNRESTRICTED),
            (r'full\s+and\s+open', StandardSetAside.FULL_AND_OPEN),
            (r'unrestricted', StandardSetAside.UNRESTRICTED),
            
            # Other patterns
            (r'sole\s+source', StandardSetAside.SOLE_SOURCE),
            (r'other\s+than\s+small\s+business', StandardSetAside.OTHER_THAN_SMALL),
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
2. "Small Business Total" is for total set-asides, "Small Business" is for general small business
3. Distinguish between competitive and sole source awards when possible
4. Map variations like "WOSB", "Women Owned", "Woman-Owned" to "Women-Owned Small Business"
5. Map "SDVOSB", "Service Disabled Veteran" variations to "Service-Disabled Veteran-Owned Small Business"
6. Use "Full and Open Competition" for competitive processes, "Unrestricted" for truly unrestricted

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