import pytest
from parsita import ParseError

import roll.exceptions as rollerr
from roll.parser import parse_program

SIMPLE_TEST_CASES = [
    #  Literals
    (r"1", 1),
    (r"200123500000000", 200123500000000),
    (r"-99", -99),
    (r"--999", 999),
    (r"---9999", -9999),
    (r"------------------99999", 99999),
    (r"-------------------999999", -999999),
    (r'""', ""),
    (r"''", ""),
    (r'"Foo"', "Foo"),
    (r"'Foo'", "Foo"),
    #  Basic arithmetic
    (r"1+1", 2),
    (r"10-4", 6),
    (r"12*3", 36),
    (r"18/2", 9),
    (r"36/5", 7.2),
    (r"2^2", 4),
    #  Operation order
    (r"1+2*3", 7),
    (r"(1+2)*3", 9),
    (r"10-1-1-1-1-1", 5),
    (r"100/5/2", 10),
    (r"100/(5/2)", 40),
    (r"4^3^2^1", 262144),
    (r"(4^3)^(2^1)", 4096),
    (r"15+2*9/3^2-3", 14),
    (r"(15+2)*9/3^(2-3)", 459),
    #  Ternary
    (r"1?69:96", 69),
    (r"0?24:420", 420),
    (r"1000?1337:-1337", 1337),
    (r"2+5?-5:5", -3),
    (r"2^0?2/10:10/2", 32),
    (r'""?"Foo":"Bar"', "Bar"),
    (r'"ASDF"?"Foo":"Bar"', "Foo"),
    #  Case
    (r'1$(1->"Foo";2->"Bar")', "Foo"),
    (r'2$(1->"Foo";2->"Bar")', "Bar"),
    (r'"a"$("a"->"Foo";2->"Bar")', "Foo"),
    (r'""$(0->"Foo";""->"Bar")', "Bar"),
    #  Logic
    (r"!0", 1),
    (r"!1", 0),
    (r"!12341", 0),
    (r'!""', 1),
    (r'!"asdf"', 0),
    (r"!0+67", 68),
    (r"!(2-2)", 1),
    (r"0&0", 0),
    (r"0&1", 0),
    (r"1&0", 0),
    (r"1&1", 1),
    (r"0&0&0", 0),
    (r"0&0&1", 0),
    (r"0&1&0", 0),
    (r"0&1&1", 0),
    (r"1&0&0", 0),
    (r"1&0&1", 0),
    (r"1&1&0", 0),
    (r"1&1&1", 1),
    (r"0|0", 0),
    (r"0|1", 1),
    (r"1|0", 1),
    (r"1|1", 1),
    (r"0|0|0", 0),
    (r"0|0|1", 1),
    (r"0|1|0", 1),
    (r"0|1|1", 1),
    (r"1|0|0", 1),
    (r"1|0|1", 1),
    (r"1|1|0", 1),
    (r"1|1|1", 1),
    (r"(1|0)&!(1&0)", 1),
    (r"0&1|1", 1),
    (r"0&(1|1)", 0),
    #  Let
    (r"^x=1$x", 1),
    (r"^x='str'$x", "str"),
    (r"^x=11;y=12$x+y", 23),
    (r"^x=100$^y=1$x+y", 101),
    (r"^x=5$^y=x$x+y", 10),
    (r"^x=17;y=x+1$y-x", 1),
    #  Functions
    (r"(\x->x) 13337", 13337),
    (r"(\foo->foo) 'abcd'", "abcd"),
    (r"(\x -> \y -> x+y) 10 20", 30),
    (r"(\x y -> y x) 1 (\z->z+1)", 2),
    (r"(\x y -> y x) 1 (\x->x+1)", 2),
    #  Whitespace
    (r"10 + 10 + 1", 21),
    (r"(  15 + 2)  * 9/    3 ^(2 -   3    )", 459),
    (r"( 15 + 1 ) / 2 ; 1 ; 2 ; 3 ; 4", 8),
]

SIMPLE_ND_TEST_CASES = [
    (r"1d6", range(1, 7)),
    (r"1d1000", range(1, 1001)),
    (r"1d1", [1]),
    (r"4321d1", [4321]),
    (r"1d(1d(1d(1d(1d(1d1000)))))", range(1, 1001)),
    (r"(1d3)d1", range(1, 4)),
    (r"(2d6)d(1d20)", range(2, 241)),
]

FUNCTION_TEST_CASES = [
    (r"@id = \x->x;id 1", 1),
    (r"@rec = \x -> x?rec x-1:0;rec 1", 0),
    (r"@fact = \x -> x ? x*(fact x-1) : 1 ; fact 10", 3628800),
    (r"@fact = \x -> ^loop=(\n a -> n ? loop(n - 1) (n * a) : a)$loop x 1;fact 5", 120),
    (
        r"@fib = \x -> ^loop=(\a1 a2 n -> (n == 0) ? a1 : ((n == 1) ? a2 : loop a2 (a1 + a2) (n - 1))) $ loop 0 1 x;fib 10",
        55,
    ),
    (r"fwd;@fwd = 1984", 1984),
    (r"double;double;@double = 'two'", "two"),
]

ERROR_TEST_CASES = [
    (r"1+++", ParseError),
    (r'"asdf', ParseError),
    (r'newt"', ParseError),
    (r"'xsdfg", ParseError),
    (r"lemon'", ParseError),
    (r"(1+1", ParseError),
    (r"12/3)", ParseError),
    (r"^x=1", ParseError),
    (r"2$", ParseError),
    (r"x", rollerr.UndefinedIdentifierError),
    (r"^x=0$y", rollerr.UndefinedIdentifierError),
    (r"\x->y", rollerr.UndefinedIdentifierError),
    (r"0d6", rollerr.ZeroDiceCountError),
    (r"1d0", rollerr.ZeroDiceSidesError),
    (r"0.5d20", rollerr.FloatingPointDiceCountError),
    (r"5d1.2", rollerr.FloatingPointDiceSidesError),
    (r"(-1)d10", rollerr.NegativeDiceCountError),
    (r"2d(-4)", rollerr.NegativeDiceSidesError),
    (r"1$(2->1)", rollerr.CaseFailureError),
    (r"1/0", rollerr.ZeroDivisionError)
    # (r"^x=x$x", Loop)
    # (r"^x=x$1", ???)
    # (r"^x=y;y=x$x+y", Loop)
    # (r"^x=10+y;y=(1?x:0)$x+y", Loop)
]


@pytest.mark.parametrize(["string", "expected"], SIMPLE_TEST_CASES)
def test_roll_deterministic(string, expected):
    actual = parse_program(string).reduce()[0].pure
    assert actual == expected


@pytest.mark.parametrize(["string", "expected"], SIMPLE_ND_TEST_CASES)
def test_roll_nd(string, expected):
    for i in range(100):
        actual = parse_program(string).reduce()[0].pure
        assert actual in expected


@pytest.mark.parametrize(["string", "expected"], FUNCTION_TEST_CASES)
def test_roll_functions(string, expected):
    actual = parse_program(string).reduce()[0].pure
    assert actual == expected


@pytest.mark.parametrize(["string", "error"], ERROR_TEST_CASES)
def test_roll_errors(string, error):
    with pytest.raises(error):
        parse_program(string).reduce()
