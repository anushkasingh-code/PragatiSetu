"""add unique constraint on project_id and file_hash for source_reports

Revision ID: 008_add_unique_report_hash
Revises: 007_add_transcriptions
Create Date: 2026-08-29 23:50:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008_add_unique_report_hash'
down_revision = '007_add_transcriptions'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('source_reports', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_project_file_hash', ['project_id', 'file_hash'])

def downgrade() -> None:
    with op.batch_alter_table('source_reports', schema=None) as batch_op:
        batch_op.drop_constraint('uq_project_file_hash', type_='unique')
