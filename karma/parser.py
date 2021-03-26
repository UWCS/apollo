import enum
import re
from collections import namedtuple
from typing import List, Match, Optional

from discord import Message
from sqlalchemy.orm import Session

from models import BlockedKarma
from utils.utils import get_name_string, user_is_irc_bot

RawKarma = namedtuple("RawKarma", ["name", "op", "reason"])
KarmaTransaction = namedtuple(
    "KarmaTransaction", ["name", "self_karma", "net_karma", "reason"]
)


class Operation(enum.Enum):
    POSITIVE = 1
    NEGATIVE = -1
    NEUTRAL = 0

    @staticmethod
    def from_str(operation_string):
        if operation_string == "++":
            return Operation.POSITIVE
        elif operation_string == "--":
            return Operation.NEGATIVE
        else:
            return Operation.NEUTRAL


def process_topic(topic_raw: str, db_session: Session) -> Optional[str]:
    if topic_raw.startswith('"') and topic_raw.endswith('"'):
        # Remove surrounding quotes and then remove leading @
        return topic_raw.replace('"', "").lstrip("@").strip()
    else:
        # Check if the item topic is disallowed
        if (
            not db_session.query(BlockedKarma)
            .filter(BlockedKarma.topic == topic_raw.casefold())
            .all()
            and len(topic_raw) > 2
        ):
            return topic_raw.replace('"', "").lstrip("@").strip()
        else:
            return None


def process_reason(reason_raw) -> Optional[str]:
    return (
        reason_raw.group("karma_reason")
        or reason_raw.group("karma_reason_2")
        or reason_raw.group("karma_reason_3")
        or reason_raw.group("karma_reason_4")
    )


def parse_message(message: Message, db_session: Session):
    # Remove any code blocks
    # TODO: fix
    filtered_message = re.sub("```.*```", "", message.clean_content)

    # If there's no message to parse then there's nothing to return
    if not filtered_message:
        return None

    # The regex for parsing karma messages
    # Hold on tight because this will be a doozy...
    # TODO: parser
    karma_re_target = r"(?P<karma_target>([^\"\s]+)|(\"([^\"]+)\"))"
    karma_re_op = r"(?P<karma_op>[+-]{2,})"
    karma_re_reason = r'(\s(because|for)\s+((?P<karma_reason>[^",]+)|"(?P<karma_reason_2>.+)")($|,)|\s\((?P<karma_reason_3>.+)\)|\s"(?P<karma_reason_4>[^"]+)"(?![+-]{2,})|,?\s|$)'

    karma_regex = re.compile(karma_re_target + karma_re_op + karma_re_reason)
    items = karma_regex.finditer(filtered_message)

    # TODO: move to own function for running tests on
    def create_transaction(item: Match[str]) -> Optional[KarmaTransaction]:
        # Need to make sure it isn't blacklisted
        topic = process_topic(item.group("karma_target"), db_session)

        if topic is None or topic.isspace():
            return

        op = item.group("karma_op")
        reason = process_reason(item)

        casefold_topic = topic.casefold()
        self_karma = (
                casefold_topic == message.author.name.casefold()
                or (message.author.nick is not None and message.author.nick.casefold() == casefold_topic)
                or (user_is_irc_bot(message) and get_name_string(message).casefold() == casefold_topic)
        )

        return KarmaTransaction(name=topic, self_karma=self_karma, net_karma=Operation.from_str(op).value, reason=reason)

    results = [create_transaction(i) for i in items]
    # Filter out the Nones with a second list comprehension
    results: List[KarmaTransaction] = [t for t in results if t is not None]

    # If there are any results then return the list, otherwise give None
    if results:
        return results
    else:
        return None
