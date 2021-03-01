"""Replace filament_types column cost with profile

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
    with op.batch_alter_table('filament_types') as bop:
        bop.drop_column('cost')


def downgrade():
    op.add_column('filament_types', sa.Column('cost', sa.Float, nullable=False))
    with op.batch_alter_table('filament_types') as bop:
        bop.drop_column('profile')
