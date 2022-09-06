from typing import Dict

from models import db_session
from models.votes import DiscordVoteMessage, VoteType
from voting.discord_interfaces.discord_base import DiscordBase, discord_base

vote_interfaces: Dict[VoteType, DiscordBase] = {
    VoteType.basic: discord_base,
}


def get_interface(msg_id):
    entry = db_session.query(DiscordVoteMessage)\
        .filter(DiscordVoteMessage.message_id == msg_id).one_or_none()
    if entry is None: return None, None
    return vote_interfaces[entry.vote.type], entry
