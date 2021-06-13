from textwrap import dedent

import pytest

from karma.parser import KarmaItem, KarmaOperation, parse_message_content
from tests.stubs import make_message_stub

TEST_CASES = {
    # Cases with no karma
    "empty": ("", []),
    "no karma": ("Hello, world!", []),
    "no karma long sentence": (
        "Hello, world! This is a test input string with 30+ characters",
        [],
    ),
    "no karma unbalanced quoted": ('"foo bar baz', []),
    "no karma topic": ("++", []),
    "too short operator": ("foobar+", []),
    "too long operator": ('"foobar"++++', []),
    "unrecognised operator": ("foobar==", []),
    "space between topic and operator": ("foobar ++", []),
    "no karma operator with reason": ('"foobar" for reason', []),
    "operator embedded in link": ("https://foobar.com?slug=--asdf", []),
    # Cases with no karma because of code blocks
    "no karma code block": (
        "```foobar++```",
        [],
    ),
    "no karma multi-line code block": (
        dedent(
            """
                ```
                example
                multi
                line
                foobar++
                code
                block
                ```
                """
        ),
        [],
    ),
    "no karma multi-line code block with text before": (
        dedent(
            """
                text before code block```
                code
                block
                ```++
                """
        ),
        [],
    ),
    "no karma inline code block": (
        "`foobar++`",
        [],
    ),
    "no karma multi-line inline code block": (
        dedent(
            """
                `foo
                bar++
                baz`
            """
        ),
        [],
    ),
    "no karma inline code block separates topic and operator": (
        "foobar`code block here`++",
        [],
    ),
    # Simple karma cases
    "simple add": (
        "foobar++",
        [KarmaItem("foobar", KarmaOperation.POSITIVE, None)],
    ),
    "simple neutral +-": (
        "foobar+-",
        [KarmaItem("foobar", KarmaOperation.NEUTRAL, None)],
    ),
    "simple neutral -+": (
        "foobar-+",
        [KarmaItem("foobar", KarmaOperation.NEUTRAL, None)],
    ),
    "simple negative": (
        "foobar--",
        [KarmaItem("foobar", KarmaOperation.NEGATIVE, None)],
    ),
    "quoted": (
        '"foobar"++',
        [KarmaItem("foobar", KarmaOperation.POSITIVE, None, bypass=True)],
    ),
    "quoted with space": (
        '"foo bar"++',
        [KarmaItem("foo bar", KarmaOperation.POSITIVE, None, bypass=True)],
    ),
    "simple with text after": (
        "foobar++ baz quz quz",
        [KarmaItem("foobar", KarmaOperation.POSITIVE, None)],
    ),
    "simple with text before": (
        "baz quz qux foobar++",
        [KarmaItem("foobar", KarmaOperation.POSITIVE, None)],
    ),
    "simple inside text": (
        "baz quz foobar++ qux",
        [KarmaItem("foobar", KarmaOperation.POSITIVE, None)],
    ),
    # Karma reasons
    "paren (reason)": (
        "foobar++ (reason)",
        [KarmaItem("foobar", KarmaOperation.POSITIVE, "reason")],
    ),
    'quote "reason"': (
        'foobar++ "reason"',
        [KarmaItem("foobar", KarmaOperation.POSITIVE, "reason")],
    ),
    "for reason": (
        "foobar++ for reason",
        [KarmaItem("foobar", KarmaOperation.POSITIVE, "reason")],
    ),
    "because reason": (
        "foobar++ because reason",
        [KarmaItem("foobar", KarmaOperation.POSITIVE, "reason")],
    ),
    "paren (reason, comma)": (
        "foobar++ (reason, comma)",
        [KarmaItem("foobar", KarmaOperation.POSITIVE, "reason, comma")],
    ),
    "empty paren reason": (
        "foobar++ ()",
        [KarmaItem("foobar", KarmaOperation.POSITIVE, None)],
    ),
    "for reason with parens": (
        "foobar++ for reason (parens)",
        [KarmaItem("foobar", KarmaOperation.POSITIVE, "reason (parens)")],
    ),
    "for reason with comma": (
        # An early comma will cut the karma reason short
        "foobar++ for reason, comma",
        [KarmaItem("foobar", KarmaOperation.POSITIVE, "reason")],
    ),
    "for quoted reason": (
        'foobar++ for "reason"',
        [KarmaItem("foobar", KarmaOperation.POSITIVE, "reason")],
    ),
    "for quoted reason with comma": (
        'foobar++ for "reason, comma"',
        [KarmaItem("foobar", KarmaOperation.POSITIVE, "reason, comma")],
    ),
    "for quoted reason with space": (
        'foobar++ for "reason reason"',
        [KarmaItem("foobar", KarmaOperation.POSITIVE, "reason reason")],
    ),
    "mid sentence for reason": (
        "Hello, world! foobar++ for reason, rest of sentence",
        [KarmaItem("foobar", KarmaOperation.POSITIVE, "reason")],
    ),
    # Multiple karma
    "multiple karma": (
        "foo++ bar-- baz+- quz-+",
        [
            KarmaItem("foo", KarmaOperation.POSITIVE, None),
            KarmaItem("bar", KarmaOperation.NEGATIVE, None),
            KarmaItem("baz", KarmaOperation.NEUTRAL, None),
            KarmaItem("quz", KarmaOperation.NEUTRAL, None),
        ],
    ),
    "multiple karma comma-separated": (
        "foo++, bar--, baz+-, quz-+",
        [
            KarmaItem("foo", KarmaOperation.POSITIVE, None),
            KarmaItem("bar", KarmaOperation.NEGATIVE, None),
            KarmaItem("baz", KarmaOperation.NEUTRAL, None),
            KarmaItem("quz", KarmaOperation.NEUTRAL, None),
        ],
    ),
    "multiple quoted karma": (
        '"item 1"++ "item 2"++',
        [
            KarmaItem("item 1", KarmaOperation.POSITIVE, None, True),
            KarmaItem("item 2", KarmaOperation.POSITIVE, None, True),
        ],
    ),
    "multiple karma with parens reasons": (
        "item1++ (reason1) item2++ (reason2)",
        [
            KarmaItem("item1", KarmaOperation.POSITIVE, "reason1"),
            KarmaItem("item2", KarmaOperation.POSITIVE, "reason2"),
        ],
    ),
    "multiple karma with parens reasons comma-separated": (
        "item1++ (reason1), item2++ (reason2)",
        [
            KarmaItem("item1", KarmaOperation.POSITIVE, "reason1"),
            KarmaItem("item2", KarmaOperation.POSITIVE, "reason2"),
        ],
    ),
    "multiple karma with for reasons": (
        # Karma with for/because reasons but be separated with commas due to the way parsing works
        "item1++ for reason1, item2++ for reason2",
        [
            KarmaItem("item1", KarmaOperation.POSITIVE, "reason1"),
            KarmaItem("item2", KarmaOperation.POSITIVE, "reason2"),
        ],
    ),
    "multiple karma with quote reasons": (
        'item1++ "reason 1" item2++ "reason 2"',
        [
            KarmaItem("item1", KarmaOperation.POSITIVE, "reason 1"),
            KarmaItem("item2", KarmaOperation.POSITIVE, "reason 2"),
        ],
    ),
    "multiple karma with mixed reasons": (
        'item1++ for reason1, item2++ because reason2, item3++ (reason 3), item4++ "reason 4"',
        [
            KarmaItem("item1", KarmaOperation.POSITIVE, "reason1"),
            KarmaItem("item2", KarmaOperation.POSITIVE, "reason2"),
            KarmaItem("item3", KarmaOperation.POSITIVE, "reason 3"),
            KarmaItem("item4", KarmaOperation.POSITIVE, "reason 4"),
        ],
    ),
}


# A note on parametrised tests/table testing:
# Don't change the test to add a new case - the test itself should be as simple as possible.
# If adding a new test case would require changes to this test, it would be better suited as a new test function.
@pytest.mark.parametrize(
    ["message", "expected"], TEST_CASES.values(), ids=TEST_CASES.keys()
)
def test_parser(message, expected):
    actual = parse_message_content(message)
    assert actual == expected
