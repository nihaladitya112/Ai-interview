"""Add completeness to evaluation

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-15 22:14:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('evaluations', sa.Column('completeness', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('evaluations', 'completeness')
