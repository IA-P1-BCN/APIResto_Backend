"""esquema inicial

Revision ID: 0001
Revises: 
Create Date: 2026-10-13 15:29:18.247162

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0001'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_categories_id'), ['id'], unique=False)

    op.create_table('dining_tables',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('number', sa.Integer(), nullable=False),
    sa.Column('capacity', sa.Integer(), nullable=False),
    sa.Column('location', sa.String(length=30), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='available', nullable=False),
    sa.CheckConstraint("location IN ('indoor', 'terrace', 'bar')", name='ck_dining_tables_location'),
    sa.CheckConstraint("status IN ('available', 'occupied', 'reserved', 'out_of_service')", name='ck_dining_tables_status'),
    sa.CheckConstraint('capacity > 0', name='ck_dining_tables_capacity_positive'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('number')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=150), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('role', sa.String(length=20), server_default='customer', nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)
        batch_op.create_index(batch_op.f('ix_users_id'), ['id'], unique=False)

    op.create_table('dishes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('price', sa.Numeric(precision=8, scale=2), nullable=False),
    sa.Column('allergens', sa.String(length=255), nullable=True),
    sa.Column('is_available', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('dishes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_dishes_id'), ['id'], unique=False)

    op.create_table('orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('table_id', sa.Integer(), nullable=True),
    sa.Column('waiter_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
    sa.ForeignKeyConstraint(['table_id'], ['dining_tables.id'], ),
    sa.ForeignKeyConstraint(['waiter_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_orders_id'), ['id'], unique=False)

    op.create_table('reservations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('table_id', sa.Integer(), nullable=False),
    sa.Column('reserved_at', sa.DateTime(), nullable=False),
    sa.Column('duration_min', sa.Integer(), server_default='90', nullable=False),
    sa.Column('party_size', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='confirmed', nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint("status IN ('confirmed', 'cancelled', 'completed', 'no_show')", name='ck_reservations_status'),
    sa.CheckConstraint('duration_min > 0', name='ck_reservations_duration_positive'),
    sa.CheckConstraint('party_size > 0', name='ck_reservations_party_size_positive'),
    sa.ForeignKeyConstraint(['table_id'], ['dining_tables.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('reservations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_reservations_table_id'), ['table_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_reservations_user_id'), ['user_id'], unique=False)

    op.create_table('invoices',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('number', sa.String(length=20), nullable=False),
    sa.Column('year', sa.Integer(), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('base_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('tax_rate', sa.Numeric(precision=4, scale=2), nullable=False),
    sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('issued_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint('total >= 0', name='ck_invoices_total_positive'),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('number'),
    sa.UniqueConstraint('order_id'),
    sa.UniqueConstraint('year', 'sequence', name='uq_invoices_year_sequence')
    )
    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_invoices_id'), ['id'], unique=False)

    op.create_table('order_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=True),
    sa.Column('dish_id', sa.Integer(), nullable=True),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=8, scale=2), nullable=False),
    sa.Column('notes', sa.String(length=255), nullable=True),
    sa.CheckConstraint('quantity > 0', name='check_quantity_positive'),
    sa.ForeignKeyConstraint(['dish_id'], ['dishes.id'], ),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_order_items_id'), ['id'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_order_items_id'))

    op.drop_table('order_items')
    with op.batch_alter_table('invoices', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_invoices_id'))

    op.drop_table('invoices')
    with op.batch_alter_table('reservations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_reservations_user_id'))
        batch_op.drop_index(batch_op.f('ix_reservations_table_id'))

    op.drop_table('reservations')
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_orders_id'))

    op.drop_table('orders')
    with op.batch_alter_table('dishes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_dishes_id'))

    op.drop_table('dishes')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_id'))
        batch_op.drop_index(batch_op.f('ix_users_email'))

    op.drop_table('users')
    op.drop_table('dining_tables')
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_categories_id'))

    op.drop_table('categories')
