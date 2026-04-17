from typing import Iterable

import pytest

from utils import clean_brackets

DEFAULT_CASES: list[tuple[str, str]] = [
    ("", ""),
    ("()", ""),
    ("(abc)", "abc"),
    ("((def))", "def"),
    ("(xyz", "(xyz"),
    ("lmn)", "lmn)"),
    ("[]", "[]"),
    ("<abc>", "<abc>"),
    ("{xyz", "{xyz"),
    ("lmn`", "lmn`"),
]


CUSTOM_CASES: list[tuple[str, list[tuple[str, str]], str]] = [
    ("", [("(", ")")], ""),
    ("(<asdf>)", [], "(<asdf>)"),
    ("(<mixed>)", [("<", ">")], "(<mixed>)"),
    ("(<mixed>)", [("<", ">"), ("(", ")")], "mixed"),
    ("<(mixed)>", [("<", ">"), ("(", ")")], "mixed"),
    ("aaaaa", [("a", "a")], "a"),
]


@pytest.mark.parametrize(["string", "expected"], DEFAULT_CASES)
def test_defaults(string: str, expected: str) -> None:
    actual = clean_brackets(string)
    assert actual == expected


@pytest.mark.parametrize(["string", "brackets", "expected"], CUSTOM_CASES)
def test_customs(string: str, expected: str, brackets: Iterable[tuple[str, str]]) -> None:
    actual = clean_brackets(string, brackets)
    assert actual == expected
