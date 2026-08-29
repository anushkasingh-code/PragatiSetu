"""Add Match Decisions Table

Revision ID: 005_add_match_decisions
Revises: 004_add_normalization_and_candidates
Create Date: 2026-08-29 23:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '005_add_match_decisions'
down_revision = '004_add_normalization_and_candidates'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'match_decisions',
        sa.Column('decision_id', sa.String(length=50), nullable=False),
        sa.Column('event_id', sa.String(length=50), nullable=False),
        sa.Column('top_activity_id', sa.String(length=50), nullable=True),
        sa.Column('match_confidence', sa.Float(), nullable=False),
        sa.Column('evidence_completeness', sa.Float(), nullable=False),
        sa.Column('top_2_margin', sa.Float(), nullable=True),
        sa.Column('decision', sa.String(length=50), nullable=False),
        sa.Column('reasons', sa.JSON(), nullable=True),
        sa.Column('missing_evidence', sa.JSON(), nullable=True),
        sa.Column('matcher_version', sa.String(length=20), nullable=False),
        sa.Column('scoring_policy_version', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['extracted_events.event_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['top_activity_id'], ['schedule_activities.activity_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('decision_id')
    )
    op.create_index(op.f('ix_match_decisions_decision'), 'match_decisions', ['decision'], unique=False)
    op.create_index(op.f('ix_match_decisions_decision_id'), 'match_decisions', ['decision_id'], unique=False)
    op.create_index(op.f('ix_match_decisions_event_id'), 'match_decisions', ['event_id'], unique=True)
    op.create_index(op.f('ix_match_decisions_top_activity_id'), 'match_decisions', ['top_activity_id'], unique=False)

def downgrade() -> None:
    op.drop_table('match_decisions')
