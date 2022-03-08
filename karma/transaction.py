from dataclasses import dataclass
from itertools import groupby
from typing import Iterable, List

from discord import Message
from sqlalchemy.orm import Session

from karma.parser import KarmaItem
from models import BlockedKarma
from utils.utils import user_is_irc_bot


def is_self_karma(karma_item: KarmaItem, message: Message) -> bool:
    topic = karma_item.topic.casefold()
    if user_is_irc_bot(message):
        username = message.clean_content.split(" ")[0][3:-3].casefold()
        return username == topic
    else:
        username = message.author.name.casefold()
        if username == topic:
            return True
        if message.author.nick is None:
            return False
        else:
            return message.author.nick.casefold() == topic


@dataclass
class KarmaTransaction:
    karma_item: KarmaItem
    self_karma: bool

    @staticmethod
    def from_item(karma_item: KarmaItem, message: Message):
        self_karma = is_self_karma(karma_item, message)
        return KarmaTransaction(karma_item, self_karma)

    @staticmethod
    def try_from_item(karma_item: KarmaItem, message: Message, db_session: Session):
        """Try to create a karma item, returning None if the topic is on the blacklist"""

        def query():
            """This function serves to lazily query the database."""
            return (
                db_session.query(BlockedKarma)
                .filter(BlockedKarma.topic.ilike(karma_item.topic.casefold()))
                .one_or_none()
            )

        if not karma_item.bypass and query() is not None:
            return None
        self_karma = is_self_karma(karma_item, message)
        return KarmaTransaction(karma_item, self_karma)


def make_transactions(
    karma_items: Iterable[KarmaItem], message: Message
) -> List[KarmaTransaction]:
    def key(karma_item: KarmaItem):
        return karma_item.topic

    # We only accept one change per topic in any given batch, so discard the rest with `next`
    truncated = [next(g) for _, g in groupby(karma_items, key=key)]
    # Turn each KarmaItem into a KarmaTransaction
    return [KarmaTransaction.from_item(i, message) for i in truncated]


def filter_transactions(
    transactions: Iterable[KarmaTransaction],
) -> List[KarmaTransaction]:
    def pred(transaction: KarmaTransaction) -> bool:
        return not (
            # Short items must be bypassed
            (
                len(transaction.karma_item.topic) < 3
                and not transaction.karma_item.bypass
            )
            # Whitespace items are not allowed
            or transaction.karma_item.topic.isspace()
            # Empty items are not allowed
            or len(transaction.karma_item.topic) == 0
        )

    return [t for t in transactions if pred(t)]


def apply_blacklist(
    transactions: Iterable[KarmaTransaction], db_session: Session
) -> List[KarmaTransaction]:
    def is_on_blacklist(karma_transaction: KarmaTransaction):
        """Query the database to test whether an item is on the blacklist.

        Returns true when the item is on the blacklist.
        """
        # If possible, don't query the database
        if karma_transaction.karma_item.bypass:
            return False
        query = (
            db_session.query(BlockedKarma)
            .filter(
                BlockedKarma.topic.ilike(karma_transaction.karma_item.topic.casefold())
            )
            .one_or_none()
        )
        # If we find the item then it is on the blacklist
        return query is not None

    return [
        transaction for transaction in transactions if not is_on_blacklist(transaction)
    ]
