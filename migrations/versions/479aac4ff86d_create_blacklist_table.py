"""create blacklist table

Revision ID: 479aac4ff86d
Revises: 941acb4f5c2f
Create Date: 2018-04-12 23:03:58.458848

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "479aac4ff86d"
down_revision = "941acb4f5c2f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "blacklist",
        sa.Column("name", sa.String, nullable=False, primary_key=True),
        sa.Column("added_by", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
    )


def downgrade():
    op.drop_table("blacklist")
