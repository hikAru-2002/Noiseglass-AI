"""add workspace isolation: workspace_id columns + analysis_cache table

Revision ID: a7d3c9e51b02
Revises: c41f7a9d02e1
Create Date: 2026-07-04 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7d3c9e51b02'
down_revision: Union[str, Sequence[str], None] = 'c41f7a9d02e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'analysis_runs',
        sa.Column('workspace_id', sa.String(), nullable=False, server_default='public'),
    )
    op.create_index('ix_analysis_runs_workspace_id', 'analysis_runs', ['workspace_id'])

    # active_tickets is transient working data; clearing it is safe and lets
    # us rebuild the primary key as (workspace_id, id) so two workspaces can
    # hold the same ticket id (e.g. both loaded GH-123).
    op.execute('DELETE FROM active_tickets')
    op.add_column(
        'active_tickets',
        sa.Column('workspace_id', sa.String(), nullable=False, server_default='public'),
    )
    op.drop_constraint('active_tickets_pkey', 'active_tickets', type_='primary')
    op.create_primary_key('active_tickets_pkey', 'active_tickets', ['workspace_id', 'id'])

    op.create_table(
        'analysis_cache',
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('workspace_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('analysis_cache')
    op.execute('DELETE FROM active_tickets')
    op.drop_constraint('active_tickets_pkey', 'active_tickets', type_='primary')
    op.drop_column('active_tickets', 'workspace_id')
    op.create_primary_key('active_tickets_pkey', 'active_tickets', ['id'])
    op.drop_index('ix_analysis_runs_workspace_id', table_name='analysis_runs')
    op.drop_column('analysis_runs', 'workspace_id')
