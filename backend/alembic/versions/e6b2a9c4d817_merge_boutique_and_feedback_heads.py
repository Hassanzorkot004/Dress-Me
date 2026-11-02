"""merge boutique orders and recommendation feedback migration branches

Revision ID: e6b2a9c4d817
Revises: c93e7a5b1d42, ab73d9e1c540
Create Date: 2026-11-02
"""
from typing import Sequence, Union

revision: str = "e6b2a9c4d817"
down_revision: Union[str, Sequence[str], None] = (
    "c93e7a5b1d42",
    "ab73d9e1c540",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
