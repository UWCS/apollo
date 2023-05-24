"""user_decrypt

Revision ID: 7223a8e3ec03
Revises: 73f11ec6d004
Create Date: 2023-04-12 20:20:21.781125

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy_utils import EncryptedType

from config import CONFIG

# revision identifiers, used by Alembic.
revision = "7223a8e3ec03"
down_revision = "73f11ec6d004"
branch_labels = None
depends_on = None


secret_key = CONFIG.BOT_SECRET_KEY
if secret_key is None:
    raise Exception("Set a secret key in config.yaml")


def upgrade():
    encrypt_type = EncryptedType(type_in=sa.String, key=CONFIG.BOT_SECRET_KEY)
    # add temp username column
    op.add_column("users", sa.Column("username_new", sa.String, nullable=True))
    with op.batch_alter_table("users", schema=None) as batch_op:
        # get encrypted usernames
        result = batch_op.get_bind().execute(sa.text("SELECT username FROM users"))
        for row in result:
            name_encrypted = row[0]
            name_decrypted = encrypt_type.process_result_value(
                name_encrypted, postgresql.dialect
            )
            batch_op.get_bind().execute(
                sa.text(
                    "UPDATE users SET username_new = :name WHERE username = :name_enc"
                ),
                {"name": name_decrypted, "name_enc": name_encrypted},
            )

    with op.batch_alter_table("users", schema=None) as batch_op:
        # switch out the username columns
        batch_op.drop_column("username")
        batch_op.alter_column("username_new", new_column_name="username")

    with op.batch_alter_table("users", schema=None) as batch_op:
        # make non-nullable
        batch_op.alter_column("username", nullable=False)

        batch_op.drop_column("verified_at")
        batch_op.drop_column("first_seen")
        batch_op.drop_column("uni_id")
        batch_op.drop_column("last_seen")


def downgrade():
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "first_seen",
                sa.DateTime,
                nullable=False,
                server_default=sa.func.current_timestamp(),
            ),
        )
        batch_op.add_column(
            sa.Column(
                "last_seen",
                sa.DateTime,
                nullable=False,
                server_default=sa.func.current_timestamp(),
            ),
        )
        batch_op.add_column(
            sa.Column("verified_at", sa.LargeBinary, autoincrement=False, nullable=True)
        )
        batch_op.add_column(
            sa.Column("uni_id", sa.LargeBinary, autoincrement=False, nullable=True)
        )
