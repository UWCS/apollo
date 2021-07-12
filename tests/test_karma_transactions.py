import pytest

from karma.parser import KarmaItem, KarmaOperation
from karma.transaction import KarmaTransaction, filter_transactions, make_transactions
from tests.stubs import make_irc_message_stub, make_message_stub

MAKE_TEST_CASES = {
    # Simple cases
    "no item": (
        [],
        make_message_stub("just a normal sentence"),
        [],
    ),
    "single item positive": (
        [KarmaItem("asdf", KarmaOperation.POSITIVE, None)],
        make_message_stub("asdf++"),
        [KarmaTransaction(KarmaItem("asdf", KarmaOperation.POSITIVE, None), False)],
    ),
    "single item neutral": (
        [KarmaItem("asdf", KarmaOperation.NEUTRAL, None)],
        make_message_stub("asdf+-"),
        [KarmaTransaction(KarmaItem("asdf", KarmaOperation.NEUTRAL, None), False)],
    ),
    "single item negative": (
        [KarmaItem("asdf", KarmaOperation.NEGATIVE, None)],
        make_message_stub("asdf--"),
        [KarmaTransaction(KarmaItem("asdf", KarmaOperation.NEGATIVE, None), False)],
    ),
    "single item with reason": (
        [KarmaItem("asdf", KarmaOperation.POSITIVE, "reason")],
        make_message_stub("asdf++ (reason)"),
        [KarmaTransaction(KarmaItem("asdf", KarmaOperation.POSITIVE, "reason"), False)],
    ),
    # Cases with more than one karma item
    # Only the first item is retained
    "duplicate item": (
        [
            KarmaItem("asdf", KarmaOperation.POSITIVE, None),
            KarmaItem("asdf", KarmaOperation.POSITIVE, None),
        ],
        make_message_stub("asdf++ asdf++"),
        [KarmaTransaction(KarmaItem("asdf", KarmaOperation.POSITIVE, None), False)],
    ),
    "duplicate topic, different operation": (
        [
            KarmaItem("asdf", KarmaOperation.POSITIVE, None),
            KarmaItem("asdf", KarmaOperation.NEGATIVE, None),
        ],
        make_message_stub("asdf++ asdf--"),
        [KarmaTransaction(KarmaItem("asdf", KarmaOperation.POSITIVE, None), False)],
    ),
    # Cases with self-karma
    "self karma": (
        [KarmaItem("Name", KarmaOperation.POSITIVE, None)],
        make_message_stub("Name++"),
        [KarmaTransaction(KarmaItem("Name", KarmaOperation.POSITIVE, None), True)],
    ),
    "self karma nickname": (
        [KarmaItem("Nick", KarmaOperation.POSITIVE, None)],
        make_message_stub("Nick++"),
        [KarmaTransaction(KarmaItem("Nick", KarmaOperation.POSITIVE, None), True)],
    ),
    "irc self karma": (
        [KarmaItem("ircname", KarmaOperation.POSITIVE, None)],
        make_irc_message_stub("ircname++"),
        [KarmaTransaction(KarmaItem("ircname", KarmaOperation.POSITIVE, None), True)],
    ),
}


@pytest.mark.parametrize(
    ["items", "message", "expected"],
    MAKE_TEST_CASES.values(),
    ids=MAKE_TEST_CASES.keys(),
)
def test_make_transactions(items, message, expected):
    actual = make_transactions(items, message)
    assert actual == expected


FILTER_TEST_CASES = {
    # Cases that should be filtered out
    "empty topic": (
        [KarmaTransaction(KarmaItem("", KarmaOperation.POSITIVE, None), False)],
        [],
    ),
    "short topic": (
        [KarmaTransaction(KarmaItem("C", KarmaOperation.POSITIVE, None), False)],
        [],
    ),
    "whitespace topic": (
        [KarmaTransaction(KarmaItem("     ", KarmaOperation.POSITIVE, None), False)],
        [],
    ),
    "bypassed empty topic": (
        [KarmaTransaction(KarmaItem("", KarmaOperation.POSITIVE, None, True), False)],
        [],
    ),
    "bypassed whitespace topic": (
        [
            KarmaTransaction(
                KarmaItem("     ", KarmaOperation.POSITIVE, None, True), False
            )
        ],
        [],
    ),
    # Cases that should be unchanged
    "typical item": (
        [KarmaTransaction(KarmaItem("foobar", KarmaOperation.POSITIVE, None), False)],
        [KarmaTransaction(KarmaItem("foobar", KarmaOperation.POSITIVE, None), False)],
    ),
    "bypassed short topic": (
        [KarmaTransaction(KarmaItem("C", KarmaOperation.POSITIVE, None, True), False)],
        [KarmaTransaction(KarmaItem("C", KarmaOperation.POSITIVE, None, True), False)],
    ),
}


@pytest.mark.parametrize(
    ["items", "expected"], FILTER_TEST_CASES.values(), ids=FILTER_TEST_CASES.keys()
)
def test_filter_transactions(items, expected):
    actual = filter_transactions(items)
    assert actual == expected
