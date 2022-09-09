import pytest

from utils.utils import split_into_messages

SIMPLE_TEST_CASES = [
    ("Line 1", 20, ["Line 1"]),
    ("Line 1\n", 20, ["Line 1"]),
    ("Line 1\nLine 2", 20, ["Line 1\nLine 2"]),
    ("Line 1\n\nLine 2", 20, ["Line 1\n_ _\nLine 2"]),
    (
        "Longer line that would need to be split",
        20,
        ["Longer line that", "would need to be", "split"],
    ),
    (
        "followed by another line that would",
        20,
        ["followed by another", "line that would"],
    ),
    (
        "Longer line that would need to be split\nfollowed by another line that would need to be split",
        20,
        [
            "Longer line that",
            "would need to be",
            "split",
            "followed by another",
            "line that would need",
            "to be split",
        ],
    ),
]


@pytest.mark.parametrize(["string", "limit", "expected"], SIMPLE_TEST_CASES)
def test_message_split(string, limit, expected):
    actual = split_into_messages(string, limit)
    assert actual == expected
