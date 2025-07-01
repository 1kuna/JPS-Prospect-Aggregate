#!/usr/bin/env python3
"""
Comprehensive database setup script that:
1. Initializes the user authentication database
2. Runs Flask migrations for the business database
3. Populates initial data sources
4. Verifies database creation

Run this for complete database setup.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

def run_command(command, description):
    """Run a command and handle output."""
    print(f"\n🔄 {description}...")
    try:
        # Use the current Python interpreter explicitly
        if command.startswith("python "):
            command = command.replace("python ", f"{sys.executable} ", 1)
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - Success!")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"❌ {description} - Failed!")
            if result.stderr:
                print(f"Error: {result.stderr}")
            if result.stdout:
                print(f"Output: {result.stdout}")
            return False
    except Exception as e:
        print(f"❌ {description} - Exception: {str(e)}")
        return False
    return True

def main():
    print("🚀 Setting up Go/No-Go Feature Databases")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('requirements.txt'):
        print("❌ Error: Please run this script from the project root directory")
        return False
    
    # Step 1: Initialize user database
    print("\n📦 Step 1: Initializing User Database")
    if not run_command(
        "python scripts/init_user_database.py",
        "Creating user authentication database"
    ):
        print("\n❌ Failed to initialize user database. Please check the error above.")
        return False
    
    # Step 2: Run Flask migrations for business database
    print("\n📦 Step 2: Running Database Migrations")
    # Use python -m flask to ensure we use the right Flask
    if not run_command(
        f"{sys.executable} -m flask db upgrade heads",
        "Applying database migrations"
    ):
        print("\n❌ Failed to run migrations. Please check the error above.")
        return False
    
    # Step 3: Populate data sources
    print("\n📦 Step 3: Populating Data Sources")
    if not run_command(
        "python scripts/populate_data_sources.py",
        "Adding initial data sources"
    ):
        print("\n⚠️  Warning: Failed to populate data sources. You can run this manually later.")
        # Don't fail the setup for this
    
    # Step 4: Check if databases were created
    print("\n📦 Step 4: Verifying Database Creation")
    data_dir = Path("data")
    user_db = data_dir / "jps_users.db"
    business_db = data_dir / "jps_aggregate.db"
    
    if user_db.exists():
        print(f"✅ User database created: {user_db}")
    else:
        print(f"❌ User database not found at: {user_db}")
        return False
    
    if business_db.exists():
        print(f"✅ Business database exists: {business_db}")
    else:
        print(f"⚠️  Business database not found at: {business_db}")
        print("   This is normal if this is your first setup.")
    
    print("\n" + "=" * 50)
    print("✨ Setup Complete!")
    print("\nNext steps:")
    print("1. Start your Flask server: python run.py")
    print("2. Start your frontend: cd frontend-react && npm run dev")
    print("3. Visit the app and create an account!")
    
    return True

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        sys.exit(1)