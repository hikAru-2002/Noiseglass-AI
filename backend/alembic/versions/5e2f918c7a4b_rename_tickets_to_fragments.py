"""rename ticket concept to fragment

Revision ID: 5e2f918c7a4b
Revises: a7d3c9e51b02
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e2f918c7a4b'
down_revision: Union[str, Sequence[str], None] = 'a7d3c9e51b02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Noiseglass generalized past "support tickets": the core unit is now a
    "fragment", any piece of raw feedback text regardless of source. Pure
    rename, no data is dropped.
    """
    op.rename_table('tickets', 'fragments')
    op.rename_table('active_tickets', 'active_fragments')
    op.alter_column('analysis_runs', 'total_tickets_analyzed', new_column_name='total_fragments_analyzed')
    op.alter_column('cluster_summaries', 'total_tickets', new_column_name='total_fragments')


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('cluster_summaries', 'total_fragments', new_column_name='total_tickets')
    op.alter_column('analysis_runs', 'total_fragments_analyzed', new_column_name='total_tickets_analyzed')
    op.rename_table('active_fragments', 'active_tickets')
    op.rename_table('fragments', 'tickets')
