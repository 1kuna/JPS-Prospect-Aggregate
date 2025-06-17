"""add user and go_no_go_decision tables

Revision ID: b7a9d8e5f4c3
Revises: fbc0e1fbf50d
Create Date: 2025-06-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7a9d8e5f4c3'
down_revision = 'fbc0e1fbf50d'
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('last_login_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=False)

    # Create go_no_go_decisions table
    op.create_table('go_no_go_decisions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('prospect_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('decision', sa.String(10), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['prospect_id'], ['prospects.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], )
    )
    op.create_index('ix_go_no_go_decisions_prospect_id', 'go_no_go_decisions', ['prospect_id'], unique=False)
    op.create_index('ix_go_no_go_decisions_user_id', 'go_no_go_decisions', ['user_id'], unique=False)
    op.create_index('ix_go_no_go_decisions_decision', 'go_no_go_decisions', ['decision'], unique=False)


def downgrade():
    # Drop indexes first
    op.drop_index('ix_go_no_go_decisions_decision', 'go_no_go_decisions')
    op.drop_index('ix_go_no_go_decisions_user_id', 'go_no_go_decisions')
    op.drop_index('ix_go_no_go_decisions_prospect_id', 'go_no_go_decisions')
    op.drop_index('ix_users_email', 'users')
    
    # Drop tables
    op.drop_table('go_no_go_decisions')
    op.drop_table('users')