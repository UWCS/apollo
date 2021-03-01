from karma.parser import create_transactions, KarmaTransaction, RawKarma


def test_empty():
    assert create_transactions("", "", []) is None


def test_simple_positive():
    assert create_transactions(
        "Baz", "Baz", [RawKarma(name="Foobar", op="++", reason=None)]
    ) == [KarmaTransaction(name="Foobar", self_karma=False, net_karma=1, reasons=[])]


def test_simple_negative():
    assert create_transactions(
        "Baz", "Baz", [RawKarma(name="Foobar", op="--", reason=None)]
    ) == [KarmaTransaction(name="Foobar", self_karma=False, net_karma=-1, reasons=[])]


def test_simple_neutral():
    assert create_transactions(
        "Baz", "Baz", [RawKarma(name="Foobar", op="+-", reason=None)]
    ) == [KarmaTransaction(name="Foobar", self_karma=False, net_karma=0, reasons=[])]


def test_self_karma_single():
    assert create_transactions(
        "Baz", "Baz", [RawKarma(name="Baz", op="++", reason=None)]
    ) == [KarmaTransaction(name="Baz", self_karma=True, net_karma=1, reasons=[])]


def test_self_karma_multiple():
    assert create_transactions(
        "Baz",
        "Baz",
        [
            RawKarma(name="Baz", op="++", reason=None),
            RawKarma(name="Baz", op="++", reason=None),
        ],
    ) == [KarmaTransaction(name="Baz", self_karma=True, net_karma=1, reasons=[])]


def test_self_karma_single_with_others():
    assert create_transactions(
        "Baz",
        "Baz",
        [
            RawKarma(name="Baz", op="++", reason=None),
            RawKarma(name="Foobar", op="++", reason=None),
        ],
    ) == [
        KarmaTransaction(name="Baz", self_karma=True, net_karma=1, reasons=[]),
        KarmaTransaction(name="Foobar", self_karma=False, net_karma=1, reasons=[]),
    ]


def test_karma_double_positive():
    assert create_transactions(
        "Bar",
        "Bar",
        [
            RawKarma(name="Baz", op="++", reason=None),
            RawKarma(name="Baz", op="++", reason=None),
        ],
    ) == [KarmaTransaction(name="Baz", self_karma=False, net_karma=1, reasons=[])]


def test_karma_double_negative():
    assert create_transactions(
        "Bar",
        "Bar",
        [
            RawKarma(name="Baz", op="--", reason=None),
            RawKarma(name="Baz", op="--", reason=None),
        ],
    ) == [KarmaTransaction(name="Baz", self_karma=False, net_karma=-1, reasons=[])]


def test_karma_double_neutral():
    assert create_transactions(
        "Bar",
        "Bar",
        [
            RawKarma(name="Baz", op="+-", reason=None),
            RawKarma(name="Baz", op="-+", reason=None),
        ],
    ) == [KarmaTransaction(name="Baz", self_karma=False, net_karma=0, reasons=[])]


def test_karma_positive_neutral():
    assert create_transactions(
        "Bar",
        "Bar",
        [
            RawKarma(name="Baz", op="++", reason=None),
            RawKarma(name="Baz", op="+-", reason=None),
        ],
    ) == [KarmaTransaction(name="Baz", self_karma=False, net_karma=1, reasons=[])]


def test_karma_negative_neutral():
    assert create_transactions(
        "Bar",
        "Bar",
        [
            RawKarma(name="Baz", op="++", reason=None),
            RawKarma(name="Baz", op="+-", reason=None),
        ],
    ) == [KarmaTransaction(name="Baz", self_karma=False, net_karma=1, reasons=[])]


def test_karma_positive_negative():
    assert create_transactions(
        "Bar",
        "Bar",
        [
            RawKarma(name="Baz", op="++", reason=None),
            RawKarma(name="Baz", op="--", reason=None),
        ],
    ) == [KarmaTransaction(name="Baz", self_karma=False, net_karma=0, reasons=[])]


def test_simple_positive_reason():
    assert create_transactions(
        "Bar", "Bar", [RawKarma(name="Baz", op="++", reason="Foobar is baz")]
    ) == [
        KarmaTransaction(
            name="Baz", self_karma=False, net_karma=1, reasons=["Foobar is baz"]
        )
    ]


def test_simple_negative_reason():
    assert create_transactions(
        "Bar", "Bar", [RawKarma(name="Baz", op="--", reason="Foobar is baz")]
    ) == [
        KarmaTransaction(
            name="Baz", self_karma=False, net_karma=-1, reasons=["Foobar is baz"]
        )
    ]


def test_simple_neutral_reason():
    assert create_transactions(
        "Bar", "Bar", [RawKarma(name="Baz", op="+-", reason="Foobar is baz")]
    ) == [
        KarmaTransaction(
            name="Baz", self_karma=False, net_karma=0, reasons=["Foobar is baz"]
        )
    ]


def test_self_karma_single_reason():
    assert create_transactions(
        "Bar", "Bar", [RawKarma(name="Bar", op="++", reason="Is awesome")]
    ) == [
        KarmaTransaction(
            name="Bar", self_karma=True, net_karma=1, reasons=["Is awesome"]
        )
    ]


def test_self_karma_single_reason_with_comma():
    assert create_transactions(
        "Bar", "Bar", [RawKarma(name="Bar", op="++", reason="Is, awesome")]
    ) == [
        KarmaTransaction(
            name="Bar", self_karma=True, net_karma=1, reasons=["Is, awesome"]
        )
    ]


def test_self_karma_multiple_reason():
    assert create_transactions(
        "Bar",
        "Bar",
        [
            RawKarma(name="Bar", op="++", reason="Is awesome"),
            RawKarma(name="Bar", op="++", reason="Is awesome"),
        ],
    ) == [
        KarmaTransaction(
            name="Bar",
            self_karma=True,
            net_karma=1,
            reasons=["Is awesome", "Is awesome"],
        )
    ]


def test_self_karma_single_with_others_and_reasons():
    assert create_transactions(
        "Bar",
        "Bar",
        [
            RawKarma(name="Bar", op="++", reason="Is awesome"),
            RawKarma(name="Foo", op="++", reason="Is awesome too"),
        ],
    ) == [
        KarmaTransaction(
            name="Bar", self_karma=True, net_karma=1, reasons=["Is awesome"]
        ),
        KarmaTransaction(
            name="Foo", self_karma=False, net_karma=1, reasons=["Is awesome too"]
        ),
    ]


def test_karma_double_positive_reasons():
    assert create_transactions(
        "Bar",
        "Bar",
        [
            RawKarma(name="Baz", op="++", reason="Foobar baz 1"),
            RawKarma(name="Baz", op="++", reason="Foobar baz 2"),
        ],
    ) == [
        KarmaTransaction(
            name="Baz",
            self_karma=False,
            net_karma=1,
            reasons=["Foobar baz 1", "Foobar baz 2"],
        )
    ]


def test_karma_double_negative_reasons():
    assert create_transactions(
        "Bar",
        "Bar",
        [
            RawKarma(name="Baz", op="--", reason="Foobar baz 1"),
            RawKarma(name="Baz", op="--", reason="Foobar baz 2"),
        ],
    ) == [
        KarmaTransaction(
            name="Baz",
            self_karma=False,
            net_karma=-1,
            reasons=["Foobar baz 1", "Foobar baz 2"],
        )
    ]


def test_karma_double_neutral_reasons():
    assert create_transactions(
        "Bar",
        "Bar",
        [
            RawKarma(name="Baz", op="+-", reason="Foobar baz 1"),
            RawKarma(name="Baz", op="-+", reason="Foobar baz 2"),
        ],
    ) == [
        KarmaTransaction(
            name="Baz",
            self_karma=False,
            net_karma=0,
            reasons=["Foobar baz 1", "Foobar baz 2"],
        )
    ]


def test_karma_double_neutral_reasons_and_commas():
    assert create_transactions(
        "Bar",
        "Bar",
        [
            RawKarma(name="Baz", op="+-", reason="Foobar, baz 1"),
            RawKarma(name="Baz", op="-+", reason="Foobar, baz 2"),
        ],
    ) == [
        KarmaTransaction(
            name="Baz",
            self_karma=False,
            net_karma=0,
            reasons=["Foobar, baz 1", "Foobar, baz 2"],
        )
    ]


def test_karma_positive_neutral_reasons():
    assert create_transactions(
        "Bar",
        "Bar",
        [
            RawKarma(name="Baz", op="++", reason="Foobar baz 1"),
            RawKarma(name="Baz", op="+-", reason="Foobar baz 2"),
        ],
    ) == [
        KarmaTransaction(
            name="Baz",
            self_karma=False,
            net_karma=1,
            reasons=["Foobar baz 1", "Foobar baz 2"],
        )
    ]


def test_karma_negative_neutral_reasons():
    assert create_transactions(
        "Bar",
        "Bar",
        [
            RawKarma(name="Baz", op="--", reason="Foobar baz 1"),
            RawKarma(name="Baz", op="+-", reason="Foobar baz 2"),
        ],
    ) == [
        KarmaTransaction(
            name="Baz",
            self_karma=False,
            net_karma=-1,
            reasons=["Foobar baz 1", "Foobar baz 2"],
        )
    ]


def test_karma_positive_negative_reasons():
    assert create_transactions(
        "Bar",
        "Bar",
        [
            RawKarma(name="Baz", op="++", reason="Foobar baz 1"),
            RawKarma(name="Baz", op="--", reason="Foobar baz 2"),
        ],
    ) == [
        KarmaTransaction(
            name="Baz",
            self_karma=False,
            net_karma=0,
            reasons=["Foobar baz 1", "Foobar baz 2"],
        )
    ]
