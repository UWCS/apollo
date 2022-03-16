from models import db_session
from models.votes import DiscordVoteMessage, Vote
from voting import vote_interfaces

from sqlalchemy.orm.exc import NoResultFound

def get_interface(msg_id):
    try:
        entry = db_session.query(DiscordVoteMessage).join(Vote).filter(DiscordVoteMessage.message_id == msg_id).one()
        return vote_interfaces[entry.type]
    except NoResultFound:
        pass
