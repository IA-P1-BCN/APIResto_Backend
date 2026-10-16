"""verificación de email: users.email_verified y email_verification_tokens

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-16 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0009'
down_revision: str | Sequence[str] | None = '0008'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('email_verified', sa.Boolean(), server_default=sa.false(), nullable=False)
        )
    users = sa.table('users', sa.column('email_verified', sa.Boolean()))
    op.execute(users.update().values(email_verified=sa.true()))

    op.create_table(
        'email_verification_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('email_verification_tokens', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_email_verification_tokens_id'), ['id'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_email_verification_tokens_token_hash'), ['token_hash'], unique=True
        )
        batch_op.create_index(
            batch_op.f('ix_email_verification_tokens_user_id'), ['user_id'], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('email_verification_tokens', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_email_verification_tokens_user_id'))
        batch_op.drop_index(batch_op.f('ix_email_verification_tokens_token_hash'))
        batch_op.drop_index(batch_op.f('ix_email_verification_tokens_id'))
    op.drop_table('email_verification_tokens')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('email_verified')
