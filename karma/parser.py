import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from parsita import TextParsers, opt, reg, rep
from parsita.util import constant

from utils.utils import filter_out_none


class KarmaOperation(Enum):
    POSITIVE = 1
    NEUTRAL = 0
    NEGATIVE = -1

    def __str__(self):
        mapping = {
            KarmaOperation.POSITIVE: "++",
            KarmaOperation.NEUTRAL: "+-",
            KarmaOperation.NEGATIVE: "--",
        }
        return mapping[self]


@dataclass
class KarmaItem:
    topic: str
    operation: KarmaOperation
    reason: Optional[str]
    bypass: bool = False


def make_karma(el: list):
    """Contents of el:
    First element contains topic and whether it is a bypass or not
    Second element contains karma operation
    Third element contains a list of zero or one elements with the reason in it
    """
    # TODO: add structural pattern matching when 3.10 is usable
    return KarmaItem(
        topic=el[0][0], operation=el[1], reason=next(iter(el[2]), None), bypass=el[0][1]
    )


def make_op_regex(o):
    non_op_pre = r"(?<![+-])"
    non_op_post = r"(?![+-])"
    allowed_post = r"(?=[ \t\v!,;:?]|$)"
    return rf"{non_op_pre}{o}{non_op_post}{allowed_post}"


class KarmaParser(TextParsers):
    anything = reg(r".") > constant(None)

    word_topic = reg(r'[^"\s]+?(?=[+-]{2})')
    string_topic = reg(r'".*?(?<!\\)(\\\\)*?"(?=[+-]{2})')
    topic = (word_topic > (lambda t: [t, False])) | (
        string_topic > (lambda t: [t[1:-1], True])
    )

    op_positive = reg(make_op_regex(r"\+\+")) > constant(KarmaOperation.POSITIVE)
    op_neutral = (reg(make_op_regex(r"\+-")) | reg(make_op_regex(r"-\+"))) > constant(
        KarmaOperation.NEUTRAL
    )
    op_negative = reg(make_op_regex(r"--")) > constant(KarmaOperation.NEGATIVE)
    operator = op_positive | op_neutral | op_negative

    bracket_reason = reg(r"\(.+?\)") > (lambda s: s[1:-1])
    quote_reason = reg(r'".*?(?<!\\)(\\\\)*?"(?![+-]{2})') > (lambda s: s[1:-1])
    reason_words = reg(r"(?i)because") | reg(r"(?i)for")
    text_reason = reason_words >> (reg(r'[^",]+') | quote_reason)
    reason = bracket_reason | quote_reason | text_reason

    karma = (topic & operator & opt(reason)) > make_karma

    parse_all = rep(karma | anything) > filter_out_none


def parse_message_content(content: str) -> List[KarmaItem]:
    cleaned = re.sub(r"```.*?```", " ", content, flags=re.DOTALL)
    cleaned = re.sub(r"`.*?`", " ", cleaned, flags=re.DOTALL)
    if cleaned == "" or cleaned.isspace():
        return []
    return KarmaParser.parse_all.parse(cleaned).or_die()
