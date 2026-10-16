"""bebidas y postres a la estacion de barra

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-15

"""
from collections.abc import Sequence

from alembic import op

revision: str = '0007'
down_revision: str | Sequence[str] | None = '0006'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE categories SET station = 'bar' "
        "WHERE LOWER(TRIM(name)) IN ('bebidas', 'postres') AND station <> 'bar'"
    )


def downgrade() -> None:
    pass
