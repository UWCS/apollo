"""Modify FilamentType to use a profile instead of cost

Revision ID: 36b213001624
Revises: e64fcfd066ac
Create Date: 2020-06-14 13:52:56.574015

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '36b213001624'
down_revision = 'e64fcfd066ac'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('filament_types', sa.Column('profile', sa.String, default='fillamentum'))
    op.drop_column('filament_types', 'cost')


def downgrade():
    op.add_column('filament_types', sa.Column('cost', sa.Float, nullable=False))
    op.drop_column('filament_types', 'profile')
