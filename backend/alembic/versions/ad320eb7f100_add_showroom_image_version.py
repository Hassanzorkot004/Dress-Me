"""track transparent showroom cutout format version

Revision ID: ad320eb7f100
Revises: 9c2e64b7a13d
Create Date: 2026-10-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "ad320eb7f100"
down_revision: Union[str, Sequence[str], None] = "9c2e64b7a13d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clothing_items", sa.Column("showroom_image_version", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("clothing_items", "showroom_image_version")
