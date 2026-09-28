"""Add explicit organization invitations and memberships.

Revision ID: c1d42e5a8b67
Revises: e42f2a1d3c90
"""

from alembic import op
import sqlalchemy as sa

revision = "c1d42e5a8b67"
down_revision = "e42f2a1d3c90"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "organization_members",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("invited_by", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_organization_member"),
    )
    op.create_index("ix_organization_members_organization_id", "organization_members", ["organization_id"])
    op.create_index("ix_organization_members_user_id", "organization_members", ["user_id"])


def downgrade():
    op.drop_index("ix_organization_members_user_id", table_name="organization_members")
    op.drop_index("ix_organization_members_organization_id", table_name="organization_members")
    op.drop_table("organization_members")
