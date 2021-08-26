"""create quote table

Revision ID: aa6b0d2498fe
Revises: 4fd69f28b6b9
Create Date: 2021-08-25 19:04:15.265036

"""
from datetime import datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'aa6b0d2498fe'
down_revision = '4fd69f28b6b9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "quotes",
        sa.Column("quote_id", sa.Integer, primary_key=True, autoincrement=True, nullable=False),
        sa.Column("submitter_type", sa.Enum("id","string", name = "submitter_type"), nullable=False),
        sa.Column("submitter_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("submitter_string", sa.String, nullable=True),
        sa.Column("author_type", sa.Enum("id","string", name = "author_type"), nullable=False),
        sa.Column("author_id", sa.Integer,  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("author_string", sa.String, nullable=True),
        sa.Column("quote", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, default=datetime.utcnow()),
        sa.Column("edited", sa.Boolean, nullable=False),
        sa.Column("edited_at", sa.DateTime, nullable=True)
    )


def downgrade():
    op.drop_table("quotes")
