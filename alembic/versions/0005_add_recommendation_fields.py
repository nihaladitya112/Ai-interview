"""Add recommendation fields

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('recommendations', sa.Column('project_recommendations', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('recommendations', sa.Column('learning_sequence', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('recommendations', 'learning_sequence')
    op.drop_column('recommendations', 'project_recommendations')
