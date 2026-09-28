"""Mark closed requests after configured personal-data retention.

Revision ID: d7e8401a5c32
Revises: b329d4e7c6a1
"""

from alembic import op
import sqlalchemy as sa

revision = "d7e8401a5c32"
down_revision = "b329d4e7c6a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("requests", sa.Column("retained_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_requests_retention", "requests", ["retained_at", "updated_at"])


def downgrade():
    op.drop_index("ix_requests_retention", table_name="requests")
    op.drop_column("requests", "retained_at")
