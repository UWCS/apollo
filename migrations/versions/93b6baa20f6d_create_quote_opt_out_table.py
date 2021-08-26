"""create quote opt-out table

Revision ID: 93b6baa20f6d
Revises: aa6b0d2498fe
Create Date: 2021-08-26 13:31:20.052759

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '93b6baa20f6d'
down_revision = 'aa6b0d2498fe'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "quotes-opt-out",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("user_type", sa.Enum("id","string", name="user_type"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("user_string", sa.String, nullable=True)
    )


def downgrade():
    op.drop_table("quotes-opt-out")
