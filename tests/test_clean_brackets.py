import pytest

from utils import clean_brackets

DEFAULT_CASES = [
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


CUSTOM_CASES = [
    ("", [("(", ")")], ""),
    ("(<asdf>)", [], "(<asdf>)"),
    ("(<mixed>)", [("<", ">")], "(<mixed>)"),
    ("(<mixed>)", [("<", ">"), ("(", ")")], "mixed"),
    ("<(mixed)>", [("<", ">"), ("(", ")")], "mixed"),
    ("aaaaa", [("a", "a")], "a"),
]


@pytest.mark.parametrize(["string", "expected"], DEFAULT_CASES)
def test_defaults(string, expected):
    actual = clean_brackets(string)
    assert actual == expected


@pytest.mark.parametrize(["string", "brackets", "expected"], CUSTOM_CASES)
def test_customs(string, expected, brackets):
    actual = clean_brackets(string, brackets)
    assert actual == expected
