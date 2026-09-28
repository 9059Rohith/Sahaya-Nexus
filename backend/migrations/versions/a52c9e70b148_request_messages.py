"""Add request-scoped participant messages.

Revision ID: a52c9e70b148
Revises: 8f36a2d04c11
"""

from alembic import op
import sqlalchemy as sa

revision = "a52c9e70b148"
down_revision = "8f36a2d04c11"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("request_id", sa.String(length=36), sa.ForeignKey("requests.id"), nullable=False),
        sa.Column("sender_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_request_id", "messages", ["request_id"])
    op.create_index("ix_messages_sender_id", "messages", ["sender_id"])


def downgrade():
    op.drop_index("ix_messages_sender_id", table_name="messages")
    op.drop_index("ix_messages_request_id", table_name="messages")
    op.drop_table("messages")
