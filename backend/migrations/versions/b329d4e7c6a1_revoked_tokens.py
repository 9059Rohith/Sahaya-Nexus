"""Track revoked sign-in tokens.

Revision ID: b329d4e7c6a1
Revises: c1d42e5a8b67
"""

from alembic import op
import sqlalchemy as sa

revision = "b329d4e7c6a1"
down_revision = "c1d42e5a8b67"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_revoked_tokens_user_id", "revoked_tokens", ["user_id"])


def downgrade():
    op.drop_index("ix_revoked_tokens_user_id", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")
