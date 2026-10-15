"""unidades preparadas y servidas

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-14 11:05:12.381904

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0006'
down_revision: str | Sequence[str] | None = '0005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('prepared_quantity', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('served_quantity', sa.Integer(), server_default='0', nullable=False))
    op.execute('UPDATE order_items SET prepared_quantity = quantity WHERE prepared')
    op.execute('UPDATE order_items SET served_quantity = quantity WHERE served')
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.drop_column('served')
        batch_op.drop_column('prepared')


def downgrade() -> None:
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('prepared', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column('served', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.execute(sa.text('UPDATE order_items SET prepared = :yes WHERE prepared_quantity >= quantity').bindparams(yes=True))
    op.execute(sa.text('UPDATE order_items SET served = :yes WHERE served_quantity >= quantity').bindparams(yes=True))
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.drop_column('served_quantity')
        batch_op.drop_column('prepared_quantity')
