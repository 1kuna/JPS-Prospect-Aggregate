#!/usr/bin/env python3
"""
File naming validation script for JPS Prospect Aggregate project.

This script validates and reports on file naming consistency across the project,
particularly focusing on data files and scraper outputs.
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass
from datetime import datetime

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.constants.agency_mapping import (
    AGENCIES, LEGACY_MAPPINGS,
    get_data_directory_mapping,
    standardize_file_name
)


@dataclass
class ValidationResult:
    """Results of file naming validation."""
    valid_files: List[str]
    invalid_files: List[str] 
    naming_issues: List[str]
    directory_issues: List[str]
    recommendations: List[str]


class FileNamingValidator:
    """Validates file naming conventions across the project."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.data_dir = self.project_root / "data" / "raw"
        
        # Standard file patterns
        self.timestamp_pattern = re.compile(r'\d{8}_\d{6}')  # YYYYMMDD_HHMMSS
        self.agency_pattern = re.compile(r'^[a-z_]+_\d{8}_\d{6}\.(csv|xlsx?|xlsm)$')
        
        # Known file extensions by agency
        self.expected_extensions = {
            'ACQGW': 'csv',
            'DHS': 'csv', 
            'SSA': 'xlsm',
            'DOC': 'xlsx',
            'DOS': 'xlsx',
            'HHS': 'csv',
            'DOJ': 'xlsx',
            'TREAS': 'xls',
            'DOT': 'csv'
        }
    
    def validate_project(self) -> ValidationResult:
        """Validate file naming across the entire project."""
        result = ValidationResult([], [], [], [], [])
        
        if not self.data_dir.exists():
            result.directory_issues.append(f"Data directory not found: {self.data_dir}")
            return result
        
        # Validate data directories
        self._validate_data_directories(result)
        
        # Validate data files
        self._validate_data_files(result)
        
        # Generate recommendations
        self._generate_recommendations(result)
        
        return result
    
    def _validate_data_directories(self, result: ValidationResult):
        """Validate data directory naming conventions."""
        for item in self.data_dir.iterdir():
            if not item.is_dir():
                continue
                
            dir_name = item.name
            
            # Check if directory follows new naming convention (agency abbreviation)
            if dir_name.upper() in AGENCIES:
                result.valid_files.append(f"Directory: {dir_name} (follows consolidated structure)")
                continue
            
            # Any other directory is non-standard
            result.directory_issues.append(f"Non-standard directory: {dir_name} (should use agency abbreviation)")
    
    def _validate_data_files(self, result: ValidationResult):
        """Validate individual data file naming."""
        for agency_dir in self.data_dir.iterdir():
            if not agency_dir.is_dir():
                continue
                
            for file_path in agency_dir.glob("*"):
                if file_path.is_file():
                    self._validate_single_file(file_path, agency_dir.name, result)
    
    def _validate_single_file(self, file_path: Path, dir_name: str, result: ValidationResult):
        """Validate a single data file."""
        file_name = file_path.name
        file_rel_path = f"{dir_name}/{file_name}"
        
        # Skip hidden files
        if file_name.startswith('.'):
            return
        
        # Check basic naming pattern
        if not self.timestamp_pattern.search(file_name):
            result.invalid_files.append(f"{file_rel_path}: Missing timestamp pattern (YYYYMMDD_HHMMSS)")
            return
        
        # Check file extension
        if not file_path.suffix:
            result.invalid_files.append(f"{file_rel_path}: Missing file extension")  
            return
        
        # Check if filename matches expected pattern
        if not self.agency_pattern.match(file_name):
            result.naming_issues.append(f"{file_rel_path}: Non-standard naming pattern")
        
        # Try to identify agency from directory
        agency_abbrev = self._identify_agency_from_directory(dir_name)
        if agency_abbrev:
            expected_ext = self.expected_extensions.get(agency_abbrev)
            actual_ext = file_path.suffix[1:]  # Remove the dot
            
            if expected_ext and actual_ext != expected_ext:
                result.naming_issues.append(
                    f"{file_rel_path}: Expected .{expected_ext} extension for {agency_abbrev}, got .{actual_ext}"
                )
        
        # Check for consistent prefixes within directory
        prefix = file_name.split('_')[0] if '_' in file_name else file_name
        expected_prefix = dir_name.replace('_', '').replace('-', '')
        
        if not file_name.lower().startswith(dir_name.lower().replace('_', '').replace('-', '')):
            result.naming_issues.append(
                f"{file_rel_path}: Filename prefix doesn't match directory name"
            )
        
        # If validation passes
        if file_rel_path not in [issue.split(':')[0] for issue in result.invalid_files + result.naming_issues]:
            result.valid_files.append(file_rel_path)
    
    def _identify_agency_from_directory(self, dir_name: str) -> str:
        """Try to identify agency abbreviation from directory name."""
        # Direct match
        if dir_name.upper() in AGENCIES:
            return dir_name.upper()
        
        # No legacy mappings needed - all directories should be agency abbreviations
        
        return None
    
    def _generate_recommendations(self, result: ValidationResult):
        """Generate recommendations for fixing issues."""
        if result.directory_issues:
            result.recommendations.append("Directory Naming:")
            for issue in result.directory_issues:
                result.recommendations.append(f"  - {issue}")
            result.recommendations.append("")
        
        if result.invalid_files:
            result.recommendations.append("File Naming Issues:")
            for issue in result.invalid_files:
                result.recommendations.append(f"  - {issue}")
            result.recommendations.append("")
        
        if result.naming_issues:
            result.recommendations.append("Naming Convention Issues:")
            for issue in result.naming_issues:
                result.recommendations.append(f"  - {issue}")
            result.recommendations.append("")
        
        # General recommendations
        result.recommendations.extend([
            "General Recommendations:",
            "  1. Use standardized agency abbreviations for directory names (acqgw, dhs, doc, etc.)",
            "  2. Follow naming pattern: {agency}_{YYYYMMDD_HHMMSS}.{ext}",
            "  3. All data (current and forecast) goes in single agency directory",
            "  4. Use consistent file extensions per agency type",
            "  5. Ensure all files have proper timestamps",
            "  6. Consider implementing automated file naming validation in CI/CD"
        ])
    
    def suggest_renames(self) -> Dict[str, str]:
        """Suggest rename operations for non-compliant files and directories."""
        suggestions = {}
        
        if not self.data_dir.exists():
            return suggestions
        
        # With consolidated structure, no directory renames should be needed
        # All directories should already be using agency abbreviations
        
        return suggestions


def main():
    """Main validation function."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    validator = FileNamingValidator(project_root)
    
    print("🔍 JPS Prospect Aggregate - File Naming Validation")
    print("=" * 60)
    
    result = validator.validate_project()
    
    # Print summary
    print(f"\n📊 VALIDATION SUMMARY")
    print(f"Valid files: {len(result.valid_files)}")
    print(f"Invalid files: {len(result.invalid_files)}")
    print(f"Naming issues: {len(result.naming_issues)}")
    print(f"Directory issues: {len(result.directory_issues)}")
    
    # Print details
    if result.valid_files:
        print(f"\n✅ VALID FILES ({len(result.valid_files)})")
        for file in result.valid_files[:10]:  # Show first 10
            print(f"  ✓ {file}")
        if len(result.valid_files) > 10:
            print(f"  ... and {len(result.valid_files) - 10} more")
    
    if result.invalid_files or result.naming_issues:
        print(f"\n❌ ISSUES FOUND")
        for issue in result.invalid_files + result.naming_issues:
            print(f"  ❌ {issue}")
    
    if result.directory_issues:
        print(f"\n📁 DIRECTORY ISSUES")
        for issue in result.directory_issues:
            print(f"  📁 {issue}")
    
    # Print recommendations
    if result.recommendations:
        print(f"\n💡 RECOMMENDATIONS")
        for rec in result.recommendations:
            print(rec)
    
    # Print rename suggestions
    suggestions = validator.suggest_renames()
    if suggestions:
        print(f"\n🔄 SUGGESTED RENAMES")
        for old, new in suggestions.items():
            print(f"  {old} → {new}")
    
    print(f"\n{'=' * 60}")
    print(f"✨ Validation completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Exit with appropriate code
    total_issues = len(result.invalid_files) + len(result.naming_issues) + len(result.directory_issues)
    sys.exit(0 if total_issues == 0 else 1)


if __name__ == "__main__":
    main()