from typing import Dict

from models import db_session
from models.votes import DiscordVoteMessage, VoteType
from voting.vote_types.base_vote import BaseVote, base_vote
from sqlalchemy.orm.exc import NoResultFound



vote_interfaces: Dict[VoteType, BaseVote] = {
    VoteType.basic: base_vote,
}


def get_interface(msg_id):
    try:
        entry = db_session.query(DiscordVoteMessage)\
            .filter(DiscordVoteMessage.message_id == msg_id).one()
        return vote_interfaces[entry.vote.type]
    except NoResultFound:
        return None
