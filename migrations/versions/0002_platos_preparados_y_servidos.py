"""platos preparados y servidos

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13 16:14:53.684437

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0002'
down_revision: str | Sequence[str] | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('prepared', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column('served', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.drop_column('served')
        batch_op.drop_column('prepared')
