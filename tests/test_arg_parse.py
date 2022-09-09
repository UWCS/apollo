import pytest

from voting.splitutils import split_args

DEFAULT_CASES = [
    ("", []),  # Empty case
    ("a", ["a"]),  # Single element
    ("a,b", ["a", "b"]),  # Basic comma
    ("a,,b", ["a", "b"]),  # Remove empty
    (r"a,b,c,d", ["a", "b", "c", "d"]),  # Longer comma
    (r"a, b, c, d", ["a", "b", "c", "d"]),  # Comma and spaces
    (r"a, b,c, d", ["a", "b", "c", "d"]),  # Mixed spaces
    (r"a b c d", ["a", "b", "c", "d"]),  # Space as delimiter
    (r"a; b; c;d", ["a", "b", "c", "d"]),  # Semicolon as delimiter
    ("a\nb b\n c", ["a", "b b", "c"]),  # New line as delimiter
    (r"a, b\, c, d", ["a", "b, c", "d"]),  # Escaped delimiter
    (r"a 'b b' c", ["a", "b b", "c"]),  # Quotes with spaces
    ('a; b; "c; c"', ["a", "b", "c; c"]),  # Quotes with semicolons
    (r"a \'b c' d", ["a", "'b", "c'", "d"]),  # Escaped quotes & single quote
    ('a b" c d', ["a", 'b"', "c", "d"]),  # Escaped quotes 2
    (r"a, b; c d", ["a, b", "c d"]),  # Mixed delimiters
    (r"a, b\; c, d", ["a", "b; c", "d"]),  # Mixed and escaped delimiters
    (r"a, 'b; c, d'", ["a", "b; c, d"]),  # Mixed and quoted delimiters
    (r"abc d e", ["abc", "d", "e"]),  # Spaces
    (r"abc", ["abc"]),  # Spaces
]


@pytest.mark.parametrize(["string", "expected"], DEFAULT_CASES)
def test_defaults(string, expected):
    actual = split_args(string)
    assert actual == expected
