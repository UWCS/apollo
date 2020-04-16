"""Add filament list table

Revision ID: eb0c99ae1f63
Revises: be19cf89389d
Create Date: 2019-10-01 10:50:01.579501

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'eb0c99ae1f63'
down_revision = 'be19cf89389d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'filament_types',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('name', sa.Text, nullable=False, unique=True),
        sa.Column('cost', sa.Float, nullable=False),
        sa.Column('image_path', sa.String, nullable=False, unique=True)
    )


def downgrade():
    op.drop_table('filament_types')
