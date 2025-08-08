#!/usr/bin/env python3
"""
Wrapper script for CSV export functionality.

This allows both direct execution and module execution:
    python scripts/export_csv.py
    python -m scripts.export_csv
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

if __name__ == "__main__":
    # Import and run the actual export script
    from scripts.utils import export_db_to_csv
    export_db_to_csv.main()