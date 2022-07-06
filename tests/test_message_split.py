import pytest
from utils.utils import split_into_messages

SIMPLE_TEST_CASES = [
    ("Line 1", ["Line 1"]),
    ("Line 1\n", ["Line 1"]),
    ("Line 1\nLine 2", ["Line 1\nLine 2"]),
    ("Line 1\n\nLine 2", ["Line 1\n_ _\nLine 2"]),
    ("Longer line that would need to be split", ["Longer line that", "would need to be", "split"]),
    ("followed by another line that would", ["followed by another", "line that would"]),
    ("Longer line that would need to be split\nfollowed by another line that would need to be split", ["Longer line that", "would need to be", "split", "followed by another", "line that would need", "to be split"]),
]


@pytest.mark.parametrize(["string", "expected"], SIMPLE_TEST_CASES)
def test_message_split(string, expected):
    actual = split_into_messages(string, 20)
    assert actual == expected

