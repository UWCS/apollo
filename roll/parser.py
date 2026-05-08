# ruff:  noqa: F821 some abuse of python's binding mechanism goes on here I think
import re
from typing import Any, Callable, Sequence, TypeVar, cast

from parsita import (
    Failure,
    ParseError,
    Parser,
    ParserContext,
    fwd,
    lit,
    opt,
    reg,
    rep,
    rep1,
    rep1sep,
    repsep,
)

from roll.ast import (
    Assignment,
    Operator,
    Program,
    TokenApplication,
    TokenCase,
    TokenFunction,
    TokenLet,
    TokenNumber,
    TokenOperator,
    TokenRoll,
    TokenString,
    TokenTernary,
    TokenVariable,
)


def bin_operator(xs: Sequence[Any]) -> Any:
    """xs = [item, [[sep, item], ... ]]"""

    def rec_operator(left: Any, pairs: list[list[Any]]) -> Any:
        if len(pairs) == 0:
            return left
        op = TokenOperator(pairs[0][0], [left, pairs[0][1]])
        if len(pairs) == 1:
            return op
        return rec_operator(op, pairs[1:])

    item = xs[0]
    suffix = xs[1]
    return rec_operator(item, suffix)


def bin_operator_right(xs: Sequence[Any]) -> Any:
    """xs = [item, [[sep, item], ... ]]"""

    def rec_operator(pairs: list[list[Any]], right: Any) -> Any:
        if len(pairs) == 0:
            return right
        op = TokenOperator(pairs[-1][0], [pairs[-1][1], right])
        if len(pairs) == 1:
            return op
        return rec_operator(pairs[:-1], op)

    item = xs[0]
    suffix = xs[1]
    separators = [pair[0] for pair in suffix]
    items = [item] + [pair[1] for pair in suffix]
    right = items[-1]
    prefix = [[separators[i], items[i]] for i in range(len(separators))]
    return rec_operator(prefix, right)


def mon_operator(xs: Any) -> Any:
    """xs = [unary_op, unary] OR primary"""
    if not isinstance(xs, list):
        return xs

    return TokenOperator(cast(Operator, xs[0]), [xs[1]])


def maybe_dice(xs: Sequence[Any]) -> Any:
    """unary & opt("d" >> unary)
    xs = [unary, [unary]]
    """
    if len(xs[1]) == 0:
        return xs[0]
    return TokenRoll(xs[0], xs[1][0])


def maybe_ternary(xs: Sequence[Any]) -> Any:
    """case & opt("?" >> expr << ":" & expr)
    xs = [case, []]
    """
    if len(xs[1]) == 0:
        return xs[0]
    return TokenTernary(xs[0], xs[1][0][0], xs[1][0][1])


def maybe_case(xs: Sequence[Any]) -> Any:
    """unary & opt(":" >> "(" >> rep1sep(case_pair, ";") << ")")
    xs = [unary, [[]]]
    """
    if len(xs[1]) == 0:
        return xs[0]
    return TokenCase(xs[0], xs[1][0])


def let(xs: Sequence[Any]) -> TokenLet:
    """assignment = identifier << "=" & expr
    let_stmt = "^" >> rep1sep(assignment, ";") << "$" & expr
    xs = [[(id, expr)*], expr]
    """
    decls = xs[0]
    expr = xs[1]
    new_env = [Assignment(decl[0], decl[1]) for decl in decls]
    return TokenLet(new_env, expr)


def anon(xs: Sequence[Any]) -> TokenFunction:
    """rep1(identifier) & expr
    xs = [[id], expr]
    """
    ids = xs[0]
    expr = xs[1]
    if len(ids) == 1:
        return TokenFunction(ids[0], expr)
    return TokenFunction(ids[0], anon([ids[1:], expr]))


def maybe_application(xs: Sequence[Any]) -> Any:
    """xs = [expr, expr, ...]"""
    if len(xs) == 1:
        return xs[0]
    return TokenApplication(xs[0], list(xs)[1:])


def function(xs: Sequence[Any]) -> Assignment:
    """identifier & func_decl
    xs = [id, expr]
    """
    return Assignment(xs[0], xs[1])

def split1(item: Any, separator: Any) -> Any:
    return item & rep(separator & item)


def split(item: Any, separator: Any) -> Any:
    return opt(split1(item, separator))

def tstr(s: str) -> TokenString:
    return TokenString(s[1:-1])

def num_sign(x: float | int) -> float | int:
    return -x

def make_prog(blocks: Sequence[Any]) -> Program:
    return Program(list(blocks))

T = TypeVar("T")

def const(val: T) -> Callable[[str], T]:
    def inner(_: str) -> T:
        return val
    return inner

class ProgramParser(ParserContext, whitespace=r"\s*"):
    # Actual grammar
    identifier: Parser[str, str] = reg(r"[a-zA-Z]\w*")

    string: Parser[str, TokenString] = reg(r'".*?(?<!\\)(\\\\)*?"') | reg(r"'.*?(?<!\\)(\\\\)*?'") > tstr

    num_int: Parser[str, int] = reg(r"\d+") > int
    num_float: Parser[str, float] = reg(r"(\d*\.\d+|\d+\.\d*)") > float
    num_positive: Parser[str, float | int] = num_float | num_int

    num: Parser[str, float | int] = fwd()

    num_negative: Parser[str, float | int] = "-" >> num > num_sign
    num.define(num_negative | num_positive)
    number: Parser[str, TokenNumber] = num > TokenNumber

    op_eq: Parser[str, Operator] = lit("==") > const(Operator.EQ)
    op_ne: Parser[str, Operator] = lit("!=") > const(Operator.NE)
    op_ge: Parser[str, Operator] = lit(">=") > const(Operator.GE)
    op_gt: Parser[str, Operator] = lit(">") > const(Operator.GT)
    op_le: Parser[str, Operator] = lit("<=") > const(Operator.LE)
    op_lt: Parser[str, Operator] = lit("<") > const(Operator.LT)
    op_and: Parser[str, Operator] = lit("&") > const(Operator.AND)
    op_or: Parser[str, Operator] = lit("|") > const(Operator.OR)
    op_add: Parser[str, Operator] = lit("+") > const(Operator.ADD)
    op_sub: Parser[str, Operator] = lit("-") > const(Operator.SUB)
    op_mul: Parser[str, Operator] = lit("*") > const(Operator.MUL)
    op_div: Parser[str, Operator] = lit("/") > const(Operator.DIV)
    op_pow: Parser[str, Operator] = lit("^") > const(Operator.POW)
    op_not: Parser[str, Operator] = lit("!") > const(Operator.NOT)
    op_neg: Parser[str, Operator] = lit("-") > const(Operator.NEG)

    equality_op: Parser[str, Operator] = op_eq | op_ne
    comparison_op: Parser[str, Operator] = op_ge | op_gt | op_le | op_lt
    logic_op: Parser[str, Operator] = op_and | op_or
    term_op: Parser[str, Operator] = op_add | op_sub
    factor_op: Parser[str, Operator] = op_mul | op_div
    power_op: Parser[str, Operator] = op_pow
    unary_op: Parser[str, Operator] = op_neg | op_not

    expr: Parser[str, Any] = fwd()
    unary: Parser[str, Any] = fwd()

    case_pair: Parser[str, Sequence[Any]] = expr << "->" & expr

    assignment: Parser[str, Sequence[Any]] = identifier << "=" & expr
    let_stmt: Parser[str, TokenLet] = ("^" >> rep1sep(assignment, ";") << "$" & expr) > let

    anon_func: Parser[str, Any] = (lit("\\") | lit("\\\\")) >> rep1(identifier) & "->" >> expr > anon

    variable: Parser[str, Any] = identifier > TokenVariable

    bracketed: Parser[str, Any] = "(" >> expr << ")"

    primary: Parser[str, Any] = number | string | bracketed | let_stmt | anon_func | variable

    unary.define(unary_op & unary | primary > mon_operator)
    dice: Parser[str, Any] = unary & opt("d" >> unary) > maybe_dice
    case: Parser[str, Any] = dice & opt(lit("$") >> "(" >> rep1sep(case_pair, ";") << ")") > maybe_case
    ternary: Parser[str, Any] = case & opt("?" >> expr << ":" & expr) > maybe_ternary

    power: Parser[str, Any] = split1(ternary, power_op) > bin_operator_right
    factor: Parser[str, Any] = split1(power, factor_op) > bin_operator
    term: Parser[str, Any] = split1(factor, term_op) > bin_operator
    logic: Parser[str, Any] = split1(term, logic_op) > bin_operator
    comparison: Parser[str, Any] = split1(logic, comparison_op) > bin_operator
    equality: Parser[str, Any] = split1(comparison, equality_op) > bin_operator

    expr.define(rep1sep(equality, reg(r"\s*")) > maybe_application)

    func: Parser[str, Any] = identifier & "=" >> expr > function

    program: Parser[str, Program] = (repsep("@" >> func | expr, ";") << opt(";")) > make_prog

    main: Parser[str, Program] = program


class DiscordParser(ParserContext, whitespace=r"\s*"):
    """Removes surrounding code blocks before the program can reach the main parser"""

    main = (
        "```" >> reg(r"(?s).*?(?=```)") << "```"
        | "`" >> reg(r"(?s).*?(?=`)") << "`"
        | reg(r"(?s)[^`].*")
    )


def parse_program(source: str) -> Program:
    parsed_blocks = DiscordParser.main.parse(source)

    if isinstance(parsed_blocks, Failure):
        raise Exception("Unclosed code blocks")
    
    no_blocks = parsed_blocks.unwrap()

    ast = ProgramParser.main.parse(no_blocks)

    if isinstance(ast, Failure):
        raise Exception(format_parse_error(ast.failure(), source))
    
    return ast.unwrap()


def format_parse_error(err: ParseError, source: str) -> str:
    found = re.search(r"(?<=but found ').*?(?=')", str(err))
    if found is None:
        last_line = source.split("\n")[-1]
        pointer = last_line + "\n" + " " * (len(last_line) - 1) + "^"
        return f"Found unexpected end of source\n{pointer}"
    else:
        found = found.group(0)
        try:
            line = re.findall(r"(?<=Line )\d+", str(err))[-1]
            char = re.findall(r"(?<=character )\d+", str(err))[-1]
            pointer = (
                source.split("\n")[int(line) - 1] + "\n" + " " * (int(char) - 1) + "^"
            )
            return f"Unexpected token {found}\nLine: {line}\nChar: {char}\n{pointer}"
        except IndexError:
            return f"Unexpected token {found}"
