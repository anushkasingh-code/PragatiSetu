"""Add Extracted Events Table

Revision ID: 003_add_extracted_events
Revises: 002_add_source_reports
Create Date: 2026-08-29 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '003_add_extracted_events'
down_revision = '002_add_source_reports'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'extracted_events',
        sa.Column('event_id', sa.String(length=50), nullable=False),
        sa.Column('report_id', sa.String(length=50), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('event_date', sa.Date(), nullable=True),
        sa.Column('event_date_source', sa.String(length=20), nullable=True),
        sa.Column('discipline', sa.String(length=100), nullable=True),
        sa.Column('action', sa.String(length=150), nullable=True),
        sa.Column('object', sa.String(length=150), nullable=True),
        sa.Column('identifier', sa.String(length=100), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('percent_complete', sa.Float(), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=True),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('source_position', sa.JSON(), nullable=True),
        sa.Column('extraction_method', sa.String(length=50), nullable=False),
        sa.Column('extraction_version', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['source_reports.report_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('event_id')
    )
    op.create_index(op.f('ix_extracted_events_event_id'), 'extracted_events', ['event_id'], unique=False)
    op.create_index(op.f('ix_extracted_events_identifier'), 'extracted_events', ['identifier'], unique=False)
    op.create_index(op.f('ix_extracted_events_report_id'), 'extracted_events', ['report_id'], unique=False)
    op.create_index(op.f('ix_extracted_events_status'), 'extracted_events', ['status'], unique=False)

def downgrade() -> None:
    op.drop_table('extracted_events')
