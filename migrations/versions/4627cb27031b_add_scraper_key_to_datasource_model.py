"""Add scraper_key to DataSource model - populate default values

Revision ID: 4627cb27031b
Revises: 000_create_base_tables
Create Date: 2024-07-16 14:51:39.597019

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4627cb27031b'
down_revision = '000_create_base_tables'
branch_labels = None
depends_on = None


def upgrade():
    # The scraper_key column is already created in the base migration
    # This migration just populates default values for existing data sources
    
    data_source_updates = [
        {"name": "Acquisition Gateway", "scraper_key": "acq_gateway"},
        {"name": "Department of Commerce", "scraper_key": "doc"},
        {"name": "Department of Homeland Security", "scraper_key": "dhs"},
        {"name": "Department of Justice", "scraper_key": "doj"},
        {"name": "Department of State", "scraper_key": "dos"},
        {"name": "Department of Health and Human Services", "scraper_key": "hhs"},
        {"name": "Social Security Administration", "scraper_key": "ssa"},
        {"name": "Treasury Forecast", "scraper_key": "treasury"},
        {"name": "DOT Forecast", "scraper_key": "dot"},
        # Add other specific mappings if they exist by different names in the DB
    ]

    for update_info in data_source_updates:
        op.execute(
            sa.text("UPDATE data_sources SET scraper_key = :scraper_key WHERE name = :name AND scraper_key IS NULL")
            .bindparams(scraper_key=update_info["scraper_key"], name=update_info["name"])
        )


def downgrade():
    # Reset scraper_key values to NULL
    op.execute(sa.text("UPDATE data_sources SET scraper_key = NULL"))
