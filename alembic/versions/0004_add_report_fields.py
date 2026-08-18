"""Add report fields

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-15 22:26:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('interview_reports', sa.Column('problem_solving_score', sa.Float(), nullable=True))
    op.add_column('interview_reports', sa.Column('communication_score', sa.Float(), nullable=True))
    op.add_column('interview_reports', sa.Column('technical_gaps', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('interview_reports', sa.Column('best_answers', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('interview_reports', sa.Column('weak_answers', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('interview_reports', sa.Column('recommended_topics', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('interview_reports', 'recommended_topics')
    op.drop_column('interview_reports', 'weak_answers')
    op.drop_column('interview_reports', 'best_answers')
    op.drop_column('interview_reports', 'technical_gaps')
    op.drop_column('interview_reports', 'communication_score')
    op.drop_column('interview_reports', 'problem_solving_score')
