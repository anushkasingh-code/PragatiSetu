"""Add Normalization Columns and Match Candidates Table

Revision ID: 004_add_normalization_and_candidates
Revises: 003_add_extracted_events
Create Date: 2026-08-29 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '004_add_normalization_and_candidates'
down_revision = '003_add_extracted_events'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add normalized columns to extracted_events
    with op.batch_alter_table('extracted_events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('normalized_identifier', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('normalized_action', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('normalized_object', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('normalized_location', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('normalization_version', sa.String(length=20), nullable=True))
        batch_op.create_index(batch_op.f('ix_extracted_events_normalized_identifier'), ['normalized_identifier'], unique=False)

    # Create match_candidates table
    op.create_table(
        'match_candidates',
        sa.Column('candidate_id', sa.String(length=50), nullable=False),
        sa.Column('event_id', sa.String(length=50), nullable=False),
        sa.Column('activity_id', sa.String(length=50), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('identifier_score', sa.Float(), nullable=False),
        sa.Column('discipline_score', sa.Float(), nullable=False),
        sa.Column('location_score', sa.Float(), nullable=False),
        sa.Column('action_score', sa.Float(), nullable=False),
        sa.Column('fuzzy_score', sa.Float(), nullable=False),
        sa.Column('semantic_score', sa.Float(), nullable=False),
        sa.Column('temporal_score', sa.Float(), nullable=False),
        sa.Column('dependency_score', sa.Float(), nullable=False),
        sa.Column('top_2_margin', sa.Float(), nullable=True),
        sa.Column('matcher_version', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['activity_id'], ['schedule_activities.activity_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['event_id'], ['extracted_events.event_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('candidate_id')
    )
    op.create_index(op.f('ix_match_candidates_activity_id'), 'match_candidates', ['activity_id'], unique=False)
    op.create_index(op.f('ix_match_candidates_candidate_id'), 'match_candidates', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_match_candidates_event_id'), 'match_candidates', ['event_id'], unique=False)

def downgrade() -> None:
    op.drop_table('match_candidates')
    with op.batch_alter_table('extracted_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_extracted_events_normalized_identifier'))
        batch_op.drop_column('normalization_version')
        batch_op.drop_column('normalized_location')
        batch_op.drop_column('normalized_object')
        batch_op.drop_column('normalized_action')
        batch_op.drop_column('normalized_identifier')
