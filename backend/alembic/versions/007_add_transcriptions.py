"""add transcriptions table

Revision ID: 007_add_transcriptions
Revises: 006_add_audit_records
Create Date: 2026-08-29 23:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007_add_transcriptions'
down_revision = '006_add_audit_records'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'transcriptions',
        sa.Column('transcription_id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), sa.ForeignKey('projects.project_id', ondelete='SET NULL'), nullable=True),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('file_hash', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('language', sa.String(), nullable=True),
        sa.Column('transcript', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('transcription_id')
    )
    op.create_index(op.f('ix_transcriptions_project_id'), 'transcriptions', ['project_id'], unique=False)
    op.create_index(op.f('ix_transcriptions_file_hash'), 'transcriptions', ['file_hash'], unique=False)
    op.create_index(op.f('ix_transcriptions_status'), 'transcriptions', ['status'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_transcriptions_status'), table_name='transcriptions')
    op.drop_index(op.f('ix_transcriptions_file_hash'), table_name='transcriptions')
    op.drop_index(op.f('ix_transcriptions_project_id'), table_name='transcriptions')
    op.drop_table('transcriptions')
