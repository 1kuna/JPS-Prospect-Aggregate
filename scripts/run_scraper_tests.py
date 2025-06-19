#!/usr/bin/env python3
"""
Run scraper tests.
This script runs the comprehensive test suite for all scrapers.

Usage:
    python run_scraper_tests.py
    python run_scraper_tests.py --verbose
    python run_scraper_tests.py --scraper dhs
"""

import subprocess
import sys
import argparse
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def run_all_tests(verbose=False):
    """Run all scraper tests."""
    cmd = [
        sys.executable, "-m", "pytest", 
        "tests/core/scrapers/test_scrapers.py",
        "-v" if verbose else "-q",
        "--tb=short"
    ]
    
    print("Running all scraper tests...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def run_single_scraper_test(scraper_name, verbose=False):
    """Run tests for a specific scraper."""
    test_method_map = {
        'acquisition_gateway': 'test_acquisition_gateway_scraper',
        'dhs': 'test_dhs_scraper',
        'treasury': 'test_treasury_scraper',
        'dot': 'test_dot_scraper',
        'hhs': 'test_hhs_scraper',
        'ssa': 'test_ssa_scraper',
        'doc': 'test_doc_scraper',
        'doj': 'test_doj_scraper',
        'dos': 'test_dos_scraper'
    }
    
    if scraper_name not in test_method_map:
        print(f"Unknown scraper: {scraper_name}")
        print(f"Available scrapers: {', '.join(test_method_map.keys())}")
        return False
    
    test_method = test_method_map[scraper_name]
    
    cmd = [
        sys.executable, "-m", "pytest", 
        f"tests/core/scrapers/test_scrapers.py::TestConsolidatedScrapers::{test_method}",
        "-v" if verbose else "-q",
        "--tb=short"
    ]
    
    print(f"Running test for {scraper_name} scraper...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def run_initialization_test(verbose=False):
    """Run the initialization test for all scrapers."""
    cmd = [
        sys.executable, "-m", "pytest", 
        "tests/core/scrapers/test_scrapers.py::TestConsolidatedScrapers::test_all_scrapers_initialize",
        "-v" if verbose else "-q",
        "--tb=short"
    ]
    
    print("Running scraper initialization test...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def run_transformation_test(verbose=False):
    """Run the custom transformation test."""
    cmd = [
        sys.executable, "-m", "pytest", 
        "tests/core/scrapers/test_consolidated_scrapers.py::TestConsolidatedScrapers::test_custom_transformations",
        "-v" if verbose else "-q",
        "--tb=short"
    ]
    
    print("Running custom transformation test...")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)
    
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Run scraper tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_scraper_tests.py                    # Run all tests
  python run_scraper_tests.py --verbose          # Run all tests with verbose output
  python run_scraper_tests.py --scraper dhs      # Run only DHS scraper test
  python run_scraper_tests.py --init-only        # Run only initialization test
  python run_scraper_tests.py --transform-only   # Run only transformation test
        """
    )
    
    parser.add_argument(
        '--scraper',
        help='Run test for specific scraper',
        choices=['acquisition_gateway', 'dhs', 'treasury', 'dot', 'hhs', 'ssa', 'doc', 'doj', 'dos']
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    parser.add_argument(
        '--init-only',
        action='store_true',
        help='Run only initialization test'
    )
    
    parser.add_argument(
        '--transform-only',
        action='store_true',
        help='Run only transformation test'
    )
    
    args = parser.parse_args()
    
    success = True
    
    if args.init_only:
        success = run_initialization_test(args.verbose)
    elif args.transform_only:
        success = run_transformation_test(args.verbose)
    elif args.scraper:
        success = run_single_scraper_test(args.scraper, args.verbose)
    else:
        success = run_all_tests(args.verbose)
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()