import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, List, Optional, Sequence, TypeVar

from parsita import Failure, Parser, ParserContext, opt, reg, rep

from utils.utils import filter_out_none


class KarmaOperation(Enum):
    POSITIVE = 1
    NEUTRAL = 0
    NEGATIVE = -1

    def __str__(self) -> str:
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


def make_karma(el: Sequence[Any]) -> KarmaItem:
    """Contents of el:
    First element contains topic and whether it is a bypass or not
    Second element contains karma operation
    Third element contains a list of zero or one elements with the reason in it
    """

    match el:
        case [[topic, bypass], operation, [reason]]:
            return KarmaItem(topic=topic, operation=operation, reason=reason, bypass=bypass)
        case [[topic, bypass], operation, []]:
            return KarmaItem(topic=topic, operation=operation, reason=None, bypass=bypass)
        case _:
            raise ValueError(f"Unexpected karma AST structure: {el}")

def make_op_regex(o: str) -> str:
    non_op_pre = r"(?<![+-])"
    non_op_post = r"(?![+-])"
    allowed_post = r"(?=[ \t\v\n!,;:?]|$)"
    return rf"{non_op_pre}{o}{non_op_post}{allowed_post}"


T = TypeVar("T")
def const(val: T) -> Callable[[Any], T]:
    def inner(_: str) -> T:
        return val
    return inner

def make_word_topic(t: str) -> tuple[str, bool]:
    return t, False

def make_string_topic(t: str) -> tuple[str, bool]:
    return t[1:-1], True

def strip_edges(s: str) -> str:
    return s[1:-1]


class KarmaParser(ParserContext, whitespace=r"\s*"):
    anything: Parser[str, None] = reg(r".") > const(None)

    word_topic = reg(r'[^"\s]+?(?=[+-]{2})')
    string_topic = reg(r'".*?(?<!\\)(\\\\)*?"(?=[+-]{2})')
    topic = (word_topic > make_word_topic) | (
        string_topic > make_string_topic
    )

    op_positive = reg(make_op_regex(r"\+\+")) > const(KarmaOperation.POSITIVE)
    op_neutral = (reg(make_op_regex(r"\+-")) | reg(make_op_regex(r"-\+"))) > const(
        KarmaOperation.NEUTRAL
    )
    op_negative = reg(make_op_regex(r"--")) > const(KarmaOperation.NEGATIVE)
    operator = op_positive | op_neutral | op_negative

    bracket_reason = reg(r"\(.+?\)") > strip_edges
    quote_reason = reg(r'".*?(?<!\\)(\\\\)*?"(?![+-]{2})') > strip_edges
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
    
    result = KarmaParser.parse_all.parse(cleaned)
    if isinstance(result, Failure):
        raise ValueError(str(result))

    return result.unwrap()

