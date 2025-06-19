#!/usr/bin/env python3
"""
Data directory migration script for JPS Prospect Aggregate project.

This script renames data directories to use standardized agency abbreviations
and creates a mapping for the transition.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.constants.agency_mapping import (
    get_data_directory_mapping, 
    AGENCIES
)


class DataDirectoryMigrator:
    """Handles migration of data directories to standardized naming."""
    
    def __init__(self, project_root: str, dry_run: bool = True):
        self.project_root = Path(project_root)
        self.data_dir = self.project_root / "data" / "raw"
        self.dry_run = dry_run
        self.migration_log = []
        
    def analyze_directories(self) -> Dict[str, str]:
        """Analyze current directories and create migration plan."""
        if not self.data_dir.exists():
            print(f"❌ Data directory not found: {self.data_dir}")
            return {}
        
        data_mapping = get_data_directory_mapping()
        forecast_mapping = get_forecast_directory_mapping()
        migration_plan = {}
        
        print(f"📂 Analyzing directories in: {self.data_dir}")
        print("=" * 60)
        
        for item in self.data_dir.iterdir():
            if not item.is_dir():
                continue
                
            dir_name = item.name
            print(f"📁 {dir_name}")
            
            # Check if already using new naming convention
            if dir_name.upper() in AGENCIES:
                print(f"   ✅ Already using standard abbreviation: {dir_name.upper()}")
                continue
            
            # Check if it's a legacy directory name
            if dir_name in data_mapping:
                new_name = data_mapping[dir_name].lower()
                migration_plan[dir_name] = new_name
                print(f"   🔄 Will rename to: {new_name}")
                continue
            
            # Check if it's a forecast directory
            if dir_name in forecast_mapping:
                abbrev = forecast_mapping[dir_name]
                new_name = f"{abbrev.lower()}_forecast"
                migration_plan[dir_name] = new_name
                print(f"   🔄 Will rename to: {new_name}")
                continue
            
            # Unknown directory
            print(f"   ⚠️  Unknown directory (will be skipped)")
        
        print(f"\n📋 Migration Plan: {len(migration_plan)} directories to rename")
        return migration_plan
    
    def execute_migration(self, migration_plan: Dict[str, str]) -> bool:
        """Execute the directory migration."""
        if not migration_plan:
            print("✅ No directories need to be migrated.")
            return True
        
        print(f"\n{'🔥 DRY RUN MODE' if self.dry_run else '🚀 EXECUTING MIGRATION'}")
        print("=" * 60)
        
        success_count = 0
        error_count = 0
        
        for old_name, new_name in migration_plan.items():
            old_path = self.data_dir / old_name
            new_path = self.data_dir / new_name
            
            try:
                if new_path.exists():
                    print(f"❌ {old_name} → {new_name} (Target already exists)")
                    error_count += 1
                    continue
                
                if self.dry_run:
                    print(f"🔄 {old_name} → {new_name} (Would rename)")
                else:
                    old_path.rename(new_path)
                    print(f"✅ {old_name} → {new_name} (Renamed)")
                    self.migration_log.append(f"Renamed {old_name} to {new_name}")
                
                success_count += 1
                
            except Exception as e:
                print(f"❌ {old_name} → {new_name} (Error: {e})")
                error_count += 1
        
        print(f"\n📊 Migration Results:")
        print(f"   ✅ Successful: {success_count}")
        print(f"   ❌ Errors: {error_count}")
        
        if not self.dry_run and self.migration_log:
            self._write_migration_log()
        
        return error_count == 0
    
    def validate_migration(self) -> bool:
        """Validate that migration was successful."""
        print(f"\n🔍 Validating migration results...")
        
        data_mapping = get_data_directory_mapping()
        forecast_mapping = get_forecast_directory_mapping()
        
        issues = []
        
        # Check that old directories no longer exist
        for old_name in data_mapping.keys():
            old_path = self.data_dir / old_name
            if old_path.exists():
                issues.append(f"Old directory still exists: {old_name}")
        
        for old_name in forecast_mapping.keys():
            old_path = self.data_dir / old_name
            if old_path.exists():
                issues.append(f"Old forecast directory still exists: {old_name}")
        
        # Check that new directories exist and contain files
        for old_name, abbrev in data_mapping.items():
            new_name = abbrev.lower()
            new_path = self.data_dir / new_name
            if not new_path.exists():
                issues.append(f"Expected new directory missing: {new_name}")
            elif not any(new_path.iterdir()):
                issues.append(f"New directory is empty: {new_name}")
        
        if issues:
            print("❌ Validation failed:")
            for issue in issues:
                print(f"   - {issue}")
            return False
        else:
            print("✅ Migration validation passed!")
            return True
    
    def _write_migration_log(self):
        """Write migration log to file."""
        log_file = self.project_root / "migration_log.txt"
        with open(log_file, 'w') as f:
            f.write(f"Data Directory Migration Log\\n")
            f.write(f"Executed: {os.system('date')}\\n")
            f.write(f"{'='*50}\\n\\n")
            for entry in self.migration_log:
                f.write(f"{entry}\\n")
        print(f"📝 Migration log written to: {log_file}")
    
    def generate_migration_script(self, migration_plan: Dict[str, str]) -> str:
        """Generate a bash script for manual migration."""
        if not migration_plan:
            return ""
        
        script_lines = [
            "#!/bin/bash",
            "# Data directory migration script",
            "# Generated by migrate_data_directories.py",
            "",
            f"cd {self.data_dir}",
            ""
        ]
        
        for old_name, new_name in migration_plan.items():
            script_lines.append(f"mv '{old_name}' '{new_name}'")
        
        script_content = "\\n".join(script_lines)
        
        script_file = self.project_root / "migrate_directories.sh"
        with open(script_file, 'w') as f:
            f.write(script_content)
        
        # Make script executable
        os.chmod(script_file, 0o755)
        
        print(f"📝 Migration script written to: {script_file}")
        return script_content


def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate data directories to standardized naming")
    parser.add_argument("--execute", action="store_true", help="Execute migration (default is dry-run)")
    parser.add_argument("--validate", action="store_true", help="Validate existing migration")
    parser.add_argument("--generate-script", action="store_true", help="Generate bash migration script")
    
    args = parser.parse_args()
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    migrator = DataDirectoryMigrator(project_root, dry_run=not args.execute)
    
    print("🏗️  JPS Prospect Aggregate - Data Directory Migration")
    print("=" * 60)
    
    if args.validate:
        success = migrator.validate_migration()
        sys.exit(0 if success else 1)
    
    # Analyze current state
    migration_plan = migrator.analyze_directories()
    
    if args.generate_script:
        migrator.generate_migration_script(migration_plan)
        return
    
    # Execute migration
    success = migrator.execute_migration(migration_plan)
    
    if not migrator.dry_run and success:
        # Validate results
        migrator.validate_migration()
    
    if migrator.dry_run and migration_plan:
        print(f"\\n💡 To execute migration, run:")
        print(f"   python {__file__} --execute")
        print(f"\\n💡 To generate bash script, run:")
        print(f"   python {__file__} --generate-script")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()