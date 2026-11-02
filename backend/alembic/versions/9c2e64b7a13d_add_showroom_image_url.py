"""store a transparent garment cutout separately for the wardrobe showroom

Revision ID: 9c2e64b7a13d
Revises: f7a2c19d4e6b
Create Date: 2026-10-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9c2e64b7a13d"
down_revision: Union[str, Sequence[str], None] = "f7a2c19d4e6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clothing_items", sa.Column("showroom_image_url", sa.String(length=1024), nullable=True))


def downgrade() -> None:
    op.drop_column("clothing_items", "showroom_image_url")
