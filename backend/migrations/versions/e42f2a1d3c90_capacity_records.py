"""Record every resource capacity and availability change.

Revision ID: e42f2a1d3c90
Revises: a52c9e70b148
"""

from alembic import op
import sqlalchemy as sa

revision = "e42f2a1d3c90"
down_revision = "a52c9e70b148"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "capacity_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("resource_id", sa.String(length=36), sa.ForeignKey("resources.id"), nullable=False),
        sa.Column("actor_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("request_id", sa.String(length=36), sa.ForeignKey("requests.id"), nullable=True),
        sa.Column("previous_capacity", sa.Integer(), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("previous_workload", sa.Integer(), nullable=True),
        sa.Column("workload", sa.Integer(), nullable=False),
        sa.Column("previous_available", sa.Boolean(), nullable=True),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(length=180), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_capacity_records_resource_id", "capacity_records", ["resource_id"])


def downgrade():
    op.drop_index("ix_capacity_records_resource_id", table_name="capacity_records")
    op.drop_table("capacity_records")
