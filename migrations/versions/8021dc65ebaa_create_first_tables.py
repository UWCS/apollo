"""Create first tables

Revision ID: 8021dc65ebaa
Revises: 
Create Date: 2018-02-12 15:54:35.550303

"""
from datetime import datetime

import sqlalchemy as sa
import sqlalchemy_utils as sau
from alembic import op

# revision identifiers, used by Alembic.
revision = '8021dc65ebaa'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('user_uid', sa.BigInteger, nullable=False),
        sa.Column('username', sau.EncryptedType, nullable=False),
        sa.Column('first_seen', sa.DateTime, nullable=False, default=datetime.utcnow()),
        sa.Column('last_seen', sa.DateTime, nullable=False, default=datetime.utcnow()),
        sa.Column('uni_id', sau.EncryptedType, nullable=True),
        sa.Column('verified_at', sau.EncryptedType, nullable=True))
    op.create_table(
        'karma',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('added', sau.EncryptedType, nullable=False, default=datetime.utcnow()),
        sa.Column('pluses', sa.Integer, nullable=False, default=0),
        sa.Column('minuses', sa.Integer, nullable=False, default=0),
        sa.Column('neutrals', sa.Integer, nullable=False, default=0))
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('message_uid', sa.BigInteger, nullable=False),
        sa.Column('message_content', sau.EncryptedType, nullable=False),
        sa.Column('author', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('channel_name', sau.EncryptedType, nullable=False))
    op.create_table(
        'karma_changes',
        sa.Column('karma_id', sa.Integer, sa.ForeignKey('karma.id'), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), primary_key=True, nullable=False),
        sa.Column('message_id', sa.Integer, sa.ForeignKey('messages.id'), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('reasons', sau.EncryptedType, nullable=True),
        sa.Column('change', sa.Integer, nullable=False),
        sa.Column('score', sa.Integer, nullable=False))
    op.create_table(
        'message_edits',
        sa.Column('id', sa.Integer, primary_key=True, nullable=False),
        sa.Column('original_message', sa.Integer, sa.ForeignKey('messages.id'), nullable=False),
        sa.Column('new_content', sau.EncryptedType, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False)
    )


def downgrade():
    op.drop_table('users')
    op.drop_table('karma')
    op.drop_table('karma_changes')
    op.drop_table('messages')
    op.drop_table('message_edits')
