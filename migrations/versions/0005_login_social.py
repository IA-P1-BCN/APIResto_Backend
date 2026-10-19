"""login social: social_accounts y password_hash nulo

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-14 16:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0005'
down_revision: str | Sequence[str] | None = '0004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'social_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=20), nullable=False),
        sa.Column('provider_user_id', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'provider_user_id', name='uq_social_accounts_provider_user'),
    )
    with op.batch_alter_table('social_accounts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_social_accounts_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_social_accounts_user_id'), ['user_id'], unique=False)
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('password_hash', existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE users SET password_hash = '' WHERE password_hash IS NULL")
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('password_hash', existing_type=sa.String(length=255), nullable=False)
    with op.batch_alter_table('social_accounts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_social_accounts_user_id'))
        batch_op.drop_index(batch_op.f('ix_social_accounts_id'))
    op.drop_table('social_accounts')
