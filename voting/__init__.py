from collections import defaultdict

from typing import Dict, Mapping

from models import db_session
from models.votes import DiscordVote, DiscordVoteMessage, Vote
from voting.discord_interfaces.discord_base import DiscordBase, base_interface
from voting.vote_types.base_vote import BaseVote, base_vote
import enum



class VoteType(enum.Enum):
    basic = 0
    fptp = 1
    approval = 2
    stv = 3
    ranked_pairs = 4



vote_interfaces: Dict[VoteType, BaseVote] = {
    VoteType.basic: base_vote,
}

