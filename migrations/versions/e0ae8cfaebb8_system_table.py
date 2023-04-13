"""system_table

Revision ID: e0ae8cfaebb8
Revises: 87c47906bbf3
Create Date: 2023-04-13 21:33:07.695485

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e0ae8cfaebb8'
down_revision = '87c47906bbf3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('system_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.Enum('RESTART', 'UPDATE', name='eventkind'), nullable=False),
    sa.Column('message_id', sa.BigInteger(), nullable=False),
    sa.Column('channel_id', sa.BigInteger(), nullable=False),
    sa.Column('acknowledged', sa.Boolean(), nullable=False),
    sa.Column('time', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_system_events'))
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('system_events')
    # ### end Alembic commands ###
