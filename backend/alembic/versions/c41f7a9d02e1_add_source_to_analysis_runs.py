"""add source column to analysis_runs

Revision ID: c41f7a9d02e1
Revises: 9bb09b3047de
Create Date: 2026-07-04 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c41f7a9d02e1'
down_revision: Union[str, Sequence[str], None] = '9bb09b3047de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('analysis_runs', sa.Column('source', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('analysis_runs', 'source')
