from typing import List, Tuple

from models import db_session
from models.votes import VoteType, Vote, VoteChoice


class BaseVote:

    def create_vote(self, title, owner_id, choices: List[str], type=VoteType.basic, vote_limit=None, seats=None) -> Tuple[Vote, List[VoteChoice]]:

        new_vote = Vote(title=title, owner_id=owner_id, type=type, vote_limit=vote_limit, seats=seats)
        db_session.add(new_vote)
        db_session.flush()  # Ensure vote id is fetched

        choice_objs = []
        for i, choice in enumerate(choices):
            new_choice = VoteChoice(vote=new_vote, choice_index=i, choice=choice)
            db_session.add(new_choice)
            choice_objs.append(new_choice)

        return new_vote, choice_objs


    def register_vote(self, vote, user, option):
        raise NotImplemented()

    def deregister_vote(self, vote, user, option):
        raise NotImplemented()

    def make_results(self, vote):
        raise NotImplemented()

    def remove(self, vote):
        raise NotImplemented()


base_vote = BaseVote()