"""Align numeric and JSON types with SQLAlchemy models

Revision ID: align_numeric_and_json_types
Revises: 5fb5cc7eff5b
Create Date: 2025-08-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "align_numeric_and_json_types"
down_revision = "5fb5cc7eff5b"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Prospect numeric columns should be DECIMAL/NUMERIC(15,2) per model
    numeric_cols = [
        ("estimated_value",),
        ("estimated_value_min",),
        ("estimated_value_max",),
        ("estimated_value_single",),
    ]

    if dialect == "postgresql":
        for (col,) in numeric_cols:
            # Use explicit USING to avoid cast issues
            op.execute(
                sa.text(
                    f"ALTER TABLE prospects ALTER COLUMN {col} TYPE NUMERIC(15,2) USING NULLIF({col}::text, '')::NUMERIC(15,2)"
                )
            )

        # Align extras to JSONB for efficient querying
        op.execute(sa.text("ALTER TABLE prospects ALTER COLUMN extra TYPE JSONB USING extra::jsonb"))

    elif dialect == "sqlite":
        # SQLite has limited ALTER support and stores types dynamically.
        # The model uses Numeric and JSON which map to SQLite storage classes.
        # We skip altering types here to avoid table rebuilds. Existing data remains valid.
        pass
    else:
        # Generic path: try SQLAlchemy alter_column where supported
        for (col,) in numeric_cols:
            try:
                op.alter_column(
                    "prospects",
                    col,
                    type_=sa.Numeric(15, 2),
                    existing_type=sa.Float(),
                    existing_nullable=True,
                )
            except Exception:
                # Fallback to best-effort raw SQL
                op.execute(
                    sa.text(
                        f"ALTER TABLE prospects ALTER COLUMN {col} TYPE NUMERIC(15,2)"
                    )
                )

        # Try to align extra to JSON where supported
        try:
            op.alter_column(
                "prospects",
                "extra",
                type_=postgresql.JSONB(),
                existing_type=sa.Text(),
                existing_nullable=True,
            )
        except Exception:
            # If dialect doesn't support JSONB, leave as-is
            pass


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        # Revert numeric columns to double precision for compatibility with older base migration
        for col in [
            "estimated_value",
            "estimated_value_min",
            "estimated_value_max",
            "estimated_value_single",
        ]:
            op.execute(sa.text(f"ALTER TABLE prospects ALTER COLUMN {col} TYPE DOUBLE PRECISION"))

        # Revert extra back to TEXT
        op.execute(sa.text("ALTER TABLE prospects ALTER COLUMN extra TYPE TEXT USING extra::text"))
    elif dialect == "sqlite":
        # No-op for SQLite to avoid destructive table rebuilds
        pass
    else:
        # Best-effort attempt to revert types
        for col in [
            "estimated_value",
            "estimated_value_min",
            "estimated_value_max",
            "estimated_value_single",
        ]:
            try:
                op.alter_column(
                    "prospects",
                    col,
                    type_=sa.Float(),
                    existing_type=sa.Numeric(15, 2),
                    existing_nullable=True,
                )
            except Exception:
                pass

        try:
            op.alter_column(
                "prospects",
                "extra",
                type_=sa.Text(),
                existing_type=postgresql.JSONB(),
                existing_nullable=True,
            )
        except Exception:
            pass


