import enum
import re
from collections import namedtuple
from typing import List, Union

from sqlalchemy.orm import Session

from models import BlockedKarma

RawKarma = namedtuple("RawKarma", ["name", "op", "reason"])
KarmaTransaction = namedtuple(
    "KarmaTransaction", ["name", "self_karma", "net_karma", "reasons"]
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


def process_topic(topic_raw: str, db_session: Session) -> Union[str, None]:
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


def process_reason(reason_raw) -> Union[str, None]:
    return (
        reason_raw.group("karma_reason")
        or reason_raw.group("karma_reason_2")
        or reason_raw.group("karma_reason_3")
        or reason_raw.group("karma_reason_4")
    )


def parse_message(message: str, db_session: Session):
    # Remove any code blocks
    filtered_message = re.sub("```.*```", "", message)

    # If there's no message to parse then there's nothing to return
    if not filtered_message:
        return None

    # The regex for parsing karma messages
    # Hold on tight because this will be a doozy...
    karma_re_target = r"(?P<karma_target>([^\"\s]+)|(\"([^\"]+)\"))"
    karma_re_op = r"(?P<karma_op>[+-]{2,})"
    karma_re_reason = '(\s(because|for)\s+((?P<karma_reason>[^",]+)|"(?P<karma_reason_2>.+)")($|,)|\s\((?P<karma_reason_3>.+)\)|\s"(?P<karma_reason_4>.+)"(?![+-]{2,})|,?\s|$)'

    karma_regex = re.compile(karma_re_target + karma_re_op + karma_re_reason)
    items = karma_regex.finditer(filtered_message)
    results = []

    # Collate all matches into a list
    for item in items:
        # Need to make sure it isn't blacklisted
        topic = process_topic(item.group("karma_target"), db_session)
        op = item.group("karma_op")
        if not topic:
            continue

        reason = process_reason(item)

        results.append(RawKarma(name=topic, op=op, reason=reason))

    # If there are any results then return the list, otherwise give None
    if results:
        return results
    else:
        return None


def create_transactions(message_author: str, message_nick: str, karma: List[RawKarma]):
    # Cover the case when nothing has been given to the function.
    if not message_author or not karma:
        return None

    # Copy the karma so we don't make any unintended changes and get the message author
    raw_karma = karma

    # Reformat the karma info to be per-karma item rather than per-token
    karma_ops = dict()
    transactions = []
    for item in raw_karma:
        karma_ops.setdefault(item.name, []).append(
            (Operation.from_str(item.op), item.reason)
        )

    # Iterate over the karma items to form a number of transactions
    for key in karma_ops.keys():
        net_karma = 0
        reasons = []

        for op, reason in karma_ops[key]:
            net_karma += op.value
            if reason:
                reasons.append(reason)

        # Bound the karma to be in the range (-1, 1)
        if net_karma < -1:
            net_karma = -1
        elif net_karma > 1:
            net_karma = 1

        # have to hard code 'irc' as only strings are passed into this function, TODO: change this
        self_karma = (
            key.casefold() == message_author.casefold()
            and not message_author.casefold() == "irc"
        ) or key.casefold() == message_nick.casefold()

        transactions.append(
            KarmaTransaction(
                name=key, self_karma=self_karma, net_karma=net_karma, reasons=reasons
            )
        )

    return transactions
