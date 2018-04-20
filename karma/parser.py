import enum
import re
from collections import namedtuple
from typing import List

from sqlalchemy.orm import Session

from models import BlockedKarma

RawKarma = namedtuple('RawKarma', ['name', 'op', 'reason'])
KarmaTransaction = namedtuple('KarmaTransaction', ['name', 'self_karma', 'net_karma', 'reasons'])


class Operation(enum.Enum):
    POSITIVE = 1
    NEGATIVE = -1
    NEUTRAL = 0

    @staticmethod
    def from_str(operation_string):
        if operation_string == '++':
            return Operation.POSITIVE
        elif operation_string == '--':
            return Operation.NEGATIVE
        else:
            return Operation.NEUTRAL


def parse_message(message: str, db_session: Session):
    # Remove any code blocks
    filtered_message = re.sub(u'```.*```', '', message)

    # If there's no message to parse then there's nothing to return
    if not filtered_message:
        return None

    # The regex for parsing karma messages
    # Hold on tight because this will be a doozy...
    karma_regex = re.compile(
        r'(?P<karma_target>([^\"\s]+)|(\"([^\"]+)\"))(?P<karma_op>(\+\+|\+\-|\-\+|\-\-))(\s(because|for)\s+(?P<karma_reason>[^,]+)($|,)|\s\((?P<karma_reason_2>.+)\)|,?\s|$)')
    items = karma_regex.finditer(filtered_message)
    results = []

    # Collate all matches into a list
    for item in items:
        # If the karma item is not in quotes, need to make sure it isn't blacklisted
        if not (item.group('karma_target').startswith('"') and item.group('karma_target').endswith('"')):
            # Check to make sure non quoted item is not in blacklist
            if not db_session.query(BlockedKarma)\
                    .filter(BlockedKarma.name == item.group('karma_target').casefold()).all():
                results.append(RawKarma(name=item.group('karma_target').replace('"', '').lstrip('@'),
                                        op=item.group('karma_op'),
                                        reason=item.group('karma_reason') or item.group('karma_reason_2')))
        else:
            results.append(RawKarma(name=item.group('karma_target').replace('"', '').lstrip('@'),
                                    op=item.group('karma_op'),
                                    reason=item.group('karma_reason') or item.group('karma_reason_2')))

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
        karma_ops.setdefault(item.name, []).append((Operation.from_str(item.op), item.reason))

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
        self_karma = ((key.casefold() == message_author.casefold() and not message_author.casefold() == 'irc')
                      or key.casefold() == message_nick.casefold())

        transactions.append(KarmaTransaction(name=key, self_karma=self_karma, net_karma=net_karma, reasons=reasons))

    return transactions
