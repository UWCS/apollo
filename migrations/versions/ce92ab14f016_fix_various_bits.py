"""Fix various bits

Revision ID: ce92ab14f016
Revises: 9b47473d8b90
Create Date: 2023-04-10 12:05:25.996003

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ce92ab14f016"
down_revision = "9b47473d8b90"
branch_labels = None
depends_on = None

# https://alembic.sqlalchemy.org/en/latest/batch.html#dropping-unnamed-or-named-foreign-key-constraints
nc = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "%(table_name)s_pkey",
}

def upgrade():
    bind = op.get_bind()
    inspector = sa.engine.reflection.Inspector(bind)
    tables = inspector.get_table_names()

    with op.batch_alter_table("karma_changes", schema=None, naming_convention=nc) as batch_op:
        batch_op.alter_column("message_id", existing_type=sa.BIGINT(), nullable=False)
        
        batch_op.drop_constraint(
            "fk_karma_changes_message_id_messages", type_="foreignkey"
        )
        batch_op.drop_column("mid_old")



def downgrade():    
    with op.batch_alter_table("karma_changes", schema=None, naming_convention=nc) as batch_op:
        batch_op.add_column(sa.Column("mid_old", sa.INTEGER(), nullable=True))
        batch_op.create_foreign_key(
            "fk_karma_changes_message_id_messages", "messages", ["mid_old"], ["id"]
        )
        batch_op.alter_column("message_id", existing_type=sa.BIGINT(), nullable=True)
    
