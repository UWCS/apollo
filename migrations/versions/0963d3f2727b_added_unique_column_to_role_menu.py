"""Added unique column to role menu

Revision ID: 0963d3f2727b
Revises: 42510fc13e04
Create Date: 2022-09-23 16:01:03.363118

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0963d3f2727b"
down_revision = "42510fc13e04"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("rolemenu", sa.Column("unique_roles", sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("rolemenu", "unique_roles")
    # ### end Alembic commands ###
