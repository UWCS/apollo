"""Remove logging

Revision ID: 9b47473d8b90
Revises: 988a71e876c3
Create Date: 2022-12-31 15:45:53.589887

"""
import sqlalchemy as sa
import sqlalchemy_utils as sau
from alembic import op
from sqlalchemy.ext.declarative import declarative_base

from config.config import CONFIG
from models.karma import KarmaChange
from models.models import auto_str

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "9b47473d8b90"
down_revision = "988a71e876c3"
branch_labels = None
depends_on = None

@auto_str
class KarmaChange(Base):
    __tablename__ = "karma_changes"

    karma_id = sa.Column(sa.Integer, primary_key=True, nullable=False)
    user_id = sa.Column(sa.Integer, primary_key=True, nullable=False)
    message_id = sa.Column(sa.Integer, primary_key=True, nullable=False)
    # Fake so stops complaining
    mid_new = sa.Column(sa.BigInteger, nullable=True)
    created_at = sa.Column(sa.DateTime, nullable=False)
    reason = sa.Column(sa.String(), nullable=True)
    change = sa.Column(sa.Integer, nullable=False)
    score = sa.Column(sa.Integer, nullable=False)


@auto_str
class LoggedMessage(Base):
    __tablename__ = "messages"

    id = sa.Column(sa.Integer, primary_key=True, nullable=False)
    message_uid = sa.Column(sa.BigInteger, nullable=False)
    message_content = sa.Column(
        sau.EncryptedType(type_in=sa.String, key=CONFIG.BOT_SECRET_KEY), nullable=False
    )
    author = sa.Column(sa.Integer, nullable=False)
    created_at = sa.Column(sa.DateTime, nullable=False)
    deleted_at = sa.Column(sa.DateTime, nullable=True)
    channel_name = sa.Column(
        sau.EncryptedType(type_in=sa.String, key=CONFIG.BOT_SECRET_KEY), nullable=False
    )


def upgrade():
    bind = op.get_bind()
    session = sa.orm.Session(bind=bind)

    # Drop FK and add column
    with op.batch_alter_table("karma_changes", recreate="always") as batch_op:
        op.drop_constraint("fk_karma_changes_message_id_messages", "karma_changes")
        batch_op.add_column(
            sa.Column("mid_new", sa.BigInteger, server_default="-1"),
            insert_after="message_id",
        )

    # Update value of new column
    for change in session.query(KarmaChange):
        msg = (
            session.query(LoggedMessage)
            .where(LoggedMessage.id == change.message_id)
            .first()
        )
        change.mid_new = msg.message_uid
    session.commit()

    # Edit PK and column names
    with op.batch_alter_table("karma_changes", schema=None) as bop:
        # bop.drop_constraint("pk_karma_changes", type_='primary')
        bop.drop_constraint("pk_karma_changes", type_="primary")
        bop.create_primary_key("pk_karma_changes", ["karma_id", "user_id", "mid_new"])
        bop.alter_column("message_id", new_column_name="mid_old", nullable=True)
        bop.alter_column("mid_new", new_column_name="message_id", server_default=None)

    session.commit()

    # op.drop_table("message_edits")
    # op.drop_table("messages")


Base2 = declarative_base()


@auto_str
class KarmaChange2(Base2):
    __tablename__ = "karma_changes"

    karma_id = sa.Column(sa.Integer, primary_key=True, nullable=False)
    user_id = sa.Column(sa.Integer, primary_key=True, nullable=False)
    message_id = sa.Column(sa.BigInteger, primary_key=True, nullable=False)
    # Fake so stops complaining
    mid_old = sa.Column(sa.Integer, nullable=True)
    created_at = sa.Column(sa.DateTime, nullable=False)
    reason = sa.Column(sa.String(), nullable=True)
    change = sa.Column(sa.Integer, nullable=False)
    score = sa.Column(sa.Integer, nullable=False)


def downgrade():
    bind = op.get_bind()
    session = sa.orm.Session(bind=bind)

    # Update value of new column
    for change in session.query(KarmaChange2):
        change.message_id = change.mid_old
    session.commit()

    with op.batch_alter_table("karma_changes", schema=None) as batch_op:
        batch_op.drop_column("mid_old")

    with op.batch_alter_table("karma_changes", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_karma_changes_messages", "messages", ["message_id"], ["id"]
        )
