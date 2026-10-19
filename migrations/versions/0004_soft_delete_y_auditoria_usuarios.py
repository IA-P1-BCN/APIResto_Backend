"""soft delete y auditoría de usuarios

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-14 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0004'
down_revision: str | Sequence[str] | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True))
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('created_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('updated_by', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_users_created_by', 'users', ['created_by'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key('fk_users_updated_by', 'users', ['updated_by'], ['id'], ondelete='SET NULL')
    op.execute('UPDATE users SET updated_at = created_at')


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('fk_users_updated_by', type_='foreignkey')
        batch_op.drop_constraint('fk_users_created_by', type_='foreignkey')
        batch_op.drop_column('updated_by')
        batch_op.drop_column('created_by')
        batch_op.drop_column('deleted_at')
        batch_op.drop_column('updated_at')
