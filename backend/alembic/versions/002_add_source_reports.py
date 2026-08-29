"""Add Source Reports Table

Revision ID: 002_add_source_reports
Revises: 001_initial_schema
Create Date: 2026-08-29 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '002_add_source_reports'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'source_reports',
        sa.Column('report_id', sa.String(length=50), nullable=False),
        sa.Column('project_id', sa.String(length=50), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('source_type', sa.String(length=20), nullable=False),
        sa.Column('report_date', sa.Date(), nullable=False),
        sa.Column('discipline', sa.String(length=100), nullable=True),
        sa.Column('raw_content', sa.Text(), nullable=True),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('stored_path', sa.String(length=500), nullable=False),
        sa.Column('processing_status', sa.String(length=50), nullable=False),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('report_id')
    )
    op.create_index(op.f('ix_source_reports_file_hash'), 'source_reports', ['file_hash'], unique=False)
    op.create_index(op.f('ix_source_reports_project_id'), 'source_reports', ['project_id'], unique=False)
    op.create_index(op.f('ix_source_reports_report_id'), 'source_reports', ['report_id'], unique=False)

def downgrade() -> None:
    op.drop_table('source_reports')
