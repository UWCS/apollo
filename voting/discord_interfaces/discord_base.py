from typing import List

from models import db_session
from models.votes import DiscordVote, DiscordVoteChoice
from voting.emoji_list import default_emojis
from voting.vote_types.base_vote import base_vote


class DiscordBase:
    def __init__(self):
        self.vote_type = base_vote

    def create_vote(self, title, owner_id, choices: List[str], vote_limit=None, seats=None):
        vote_obj, choices_obj = self.vote_type.create_vote(title, owner_id, choices, vote_limit, seats)

        new_dc_vote = DiscordVote(vote=vote_obj)
        db_session.add(new_dc_vote)

        dc_choices = []
        for i, choice in enumerate(choices):
            new_dc_choice = DiscordVoteChoice(choice=choice, emoji=default_emojis[i])
            db_session.add(new_dc_choice)
            dc_choices.append(new_dc_choice)


    def react_add(self, msg, user, emoji):
        raise NotImplemented()


    def react_remove(self, msg, user, emoji):
        raise NotImplemented()


    def record_vote(self, vote, user, option):
        raise NotImplemented()

    def make_results(self, vote):
        raise NotImplemented()

    def remove(self, vote):
        raise NotImplemented()


discord_base = DiscordBase()
