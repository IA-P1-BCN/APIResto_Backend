"""verificacion en dos pasos: totp_secret, totp_enabled y totp_recovery_codes en users

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-16 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0010'
down_revision: str | Sequence[str] | None = '0009'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('totp_secret', sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column('totp_enabled', sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column('totp_recovery_codes', sa.String(length=600), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('totp_recovery_codes')
        batch_op.drop_column('totp_enabled')
        batch_op.drop_column('totp_secret')
