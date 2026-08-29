"""Initial Schema Migration

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-29 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'projects',
        sa.Column('project_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('project_id')
    )
    op.create_index(op.f('ix_projects_project_id'), 'projects', ['project_id'], unique=False)

    op.create_table(
        'wbs_nodes',
        sa.Column('wbs_id', sa.String(length=50), nullable=False),
        sa.Column('project_id', sa.String(length=50), nullable=False),
        sa.Column('parent_wbs_id', sa.String(length=50), nullable=True),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['parent_wbs_id'], ['wbs_nodes.wbs_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('wbs_id')
    )
    op.create_index(op.f('ix_wbs_nodes_parent_wbs_id'), 'wbs_nodes', ['parent_wbs_id'], unique=False)
    op.create_index(op.f('ix_wbs_nodes_project_id'), 'wbs_nodes', ['project_id'], unique=False)
    op.create_index(op.f('ix_wbs_nodes_wbs_id'), 'wbs_nodes', ['wbs_id'], unique=False)

    op.create_table(
        'schedule_activities',
        sa.Column('activity_id', sa.String(length=50), nullable=False),
        sa.Column('project_id', sa.String(length=50), nullable=False),
        sa.Column('wbs_id', sa.String(length=50), nullable=True),
        sa.Column('discipline', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('equipment_or_line_id', sa.String(length=100), nullable=True),
        sa.Column('planned_start', sa.Date(), nullable=False),
        sa.Column('planned_finish', sa.Date(), nullable=False),
        sa.Column('actual_start', sa.Date(), nullable=True),
        sa.Column('actual_finish', sa.Date(), nullable=True),
        sa.Column('percent_complete', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('predecessor_activity_id', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['predecessor_activity_id'], ['schedule_activities.activity_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['wbs_id'], ['wbs_nodes.wbs_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('activity_id')
    )
    op.create_index(op.f('ix_schedule_activities_activity_id'), 'schedule_activities', ['activity_id'], unique=False)
    op.create_index(op.f('ix_schedule_activities_discipline'), 'schedule_activities', ['discipline'], unique=False)
    op.create_index(op.f('ix_schedule_activities_equipment_or_line_id'), 'schedule_activities', ['equipment_or_line_id'], unique=False)
    op.create_index(op.f('ix_schedule_activities_project_id'), 'schedule_activities', ['project_id'], unique=False)
    op.create_index(op.f('ix_schedule_activities_wbs_id'), 'schedule_activities', ['wbs_id'], unique=False)

def downgrade() -> None:
    op.drop_table('schedule_activities')
    op.drop_table('wbs_nodes')
    op.drop_table('projects')
