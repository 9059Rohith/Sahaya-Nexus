"""Add per-user idempotent request submission IDs.

Revision ID: 8f36a2d04c11
Revises: 332f4b3677cd
"""

from alembic import op
import sqlalchemy as sa

revision = "8f36a2d04c11"
down_revision = "332f4b3677cd"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("requests") as batch:
        batch.add_column(sa.Column("client_submission_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("submission_hash", sa.String(length=64), nullable=True))
        batch.create_unique_constraint("uq_request_owner_submission", ["owner_id", "client_submission_id"])


def downgrade():
    with op.batch_alter_table("requests") as batch:
        batch.drop_constraint("uq_request_owner_submission", type_="unique")
        batch.drop_column("submission_hash")
        batch.drop_column("client_submission_id")
