import pytest

from karma.parser import KarmaItem, KarmaOperation
from karma.transaction import KarmaTransaction, make_transactions
from tests.stubs import make_irc_message_stub, make_message_stub

TEST_CASES = {
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
    ["items", "message", "expected"], TEST_CASES.values(), ids=TEST_CASES.keys()
)
def test_transactions(items, message, expected):
    actual = make_transactions(items, message)
    assert actual == expected
