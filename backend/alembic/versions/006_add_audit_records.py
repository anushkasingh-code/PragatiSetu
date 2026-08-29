"""Add Audit Records Table

Revision ID: 006_add_audit_records
Revises: 005_add_match_decisions
Create Date: 2026-08-29 23:48:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '006_add_audit_records'
down_revision = '005_add_match_decisions'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'audit_records',
        sa.Column('audit_id', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('project_id', sa.String(length=50), nullable=False),
        sa.Column('activity_id', sa.String(length=50), nullable=False),
        sa.Column('event_id', sa.String(length=50), nullable=False),
        sa.Column('report_id', sa.String(length=50), nullable=True),
        sa.Column('previous_value', sa.JSON(), nullable=False),
        sa.Column('new_value', sa.JSON(), nullable=False),
        sa.Column('system_decision', sa.String(length=50), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('reviewer', sa.String(length=100), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('matcher_version', sa.String(length=20), nullable=False),
        sa.Column('scoring_policy_version', sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(['activity_id'], ['schedule_activities.activity_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['event_id'], ['extracted_events.event_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['report_id'], ['source_reports.report_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('audit_id')
    )
    op.create_index(op.f('ix_audit_records_activity_id'), 'audit_records', ['activity_id'], unique=False)
    op.create_index(op.f('ix_audit_records_audit_id'), 'audit_records', ['audit_id'], unique=False)
    op.create_index(op.f('ix_audit_records_event_id'), 'audit_records', ['event_id'], unique=False)

def downgrade() -> None:
    op.drop_table('audit_records')
