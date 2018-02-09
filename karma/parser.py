import enum
import re
from collections import namedtuple
from typing import List

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


def parse_message(message: str):
    # Remove any code blocks
    filtered_message = re.sub(u'```.*```', '', message)

    # If there's no message to parse then there's nothing to return
    if not filtered_message:
        return None

    # The regex for parsing karma messages
    # Hold on tight because this will be a doozy...
    karma_regex = re.compile(
        r'(?P<karma_target>([^\"\s]+)|(\"([^\"]+)\"))(?P<karma_op>(\+\+|\+\-|\-\+|\-\-))(\s(because|for)\s+(?P<karma_reason>[^,]+)($|,)|\s\(.+\)+|,?\s|$)')
    items = karma_regex.finditer(filtered_message)
    results = []

    # Collate all matches into a list
    for item in items:
        results.append(RawKarma(name=item.group('karma_target').replace('"', ''), op=item.group('karma_op'),
                                reason=item.group('karma_reason')))

    # If there are any results then return the list, otherwise give None
    if results:
        return results
    else:
        return None


def create_transactions(message_author: str, karma: List[RawKarma]):
    # Cover the case when nothing has been given to the function.
    if not message_author or not karma:
        return None

    # Copy the karma so we don't make any unintended changes
    raw_karma = karma

    # Filter out self-karma operations
    self_karma = [x for x in raw_karma if x.name.lower() == message_author.lower()]
    transactions = []

    if self_karma:
        # If the user has karma'd themselves the same number of times tbere are karma'd items, no changes
        # should be made. Otherwise, filter out the self-karma items
        if len(self_karma) == len(raw_karma):
            return [KarmaTransaction(name=message_author, self_karma=True, net_karma=0, reasons=[])]
        else:
            transactions.append(KarmaTransaction(name=message_author, self_karma=True, net_karma=0, reasons=[]))
            raw_karma = [x for x in raw_karma if x not in self_karma]

    # Reformat the karma info to be per-karma item rather than per-token
    karma_ops = dict()
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

        transactions.append(KarmaTransaction(name=key, self_karma=False, net_karma=net_karma, reasons=reasons))

    return transactions
