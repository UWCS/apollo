import re

from parsita import ParseError, TextParsers, lit, opt, reg, rep, rep1, rep1sep, repsep
from parsita.util import constant

from roll.ast import *


def bin_operator(xs):
    """xs = [item, [[sep, item], ... ]]"""

    def rec_operator(left, pairs):
        if len(pairs) == 0:
            return left
        op = TokenOperator(pairs[0][0], [left, pairs[0][1]])
        if len(pairs) == 1:
            return op
        return rec_operator(op, pairs[1:])

    item = xs[0]
    suffix = xs[1]
    return rec_operator(item, suffix)


def bin_operator_right(xs):
    """xs = [item, [[sep, item], ... ]]"""

    def rec_operator(pairs, right):
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


def mon_operator(xs):
    """xs = [unary_op, unary] OR primary"""
    if not isinstance(xs, list):
        return xs
    return TokenOperator(xs[0], [xs[1]])


def maybe_dice(xs):
    """unary & opt("d" >> unary)
    xs = [unary, [unary]]
    """
    if len(xs[1]) == 0:
        return xs[0]
    return TokenRoll(xs[0], xs[1][0])


def maybe_ternary(xs):
    """case & opt("?" >> expr << ":" & expr)
    xs = [case, []]
    """
    if len(xs[1]) == 0:
        return xs[0]
    return TokenTernary(xs[0], xs[1][0][0], xs[1][0][1])


def maybe_case(xs):
    """unary & opt(":" >> "(" >> rep1sep(case_pair, ";") << ")")
    xs = [unary, [[]]]
    """
    if len(xs[1]) == 0:
        return xs[0]
    return TokenCase(xs[0], xs[1][0])


def let(xs):
    """assignment = identifier << "=" & expr
    let_stmt = "let" >> rep1sep(assignment, ";") << "in" & expr
    xs = [[[id, expr]*], expr]
    """
    decls = xs[0]
    expr = xs[1]
    new_env = [Assignment(decl[0], decl[1]) for decl in decls]
    return TokenLet(new_env, expr)


def anon(xs):
    """rep1(identifier) & expr
    xs = [[id], expr]
    """
    ids = xs[0]
    expr = xs[1]
    if len(ids) == 1:
        return TokenFunction(ids[0], expr)
    return TokenFunction(ids[0], anon([ids[1:], expr]))


def maybe_application(xs):
    """xs = [expr, expr, ...]"""
    if len(xs) == 1:
        return xs[0]
    return TokenApplication(xs[0], xs[1:])


def function(xs):
    """identifier & func_decl
    xs = [id, expr]
    """
    return Assignment(xs[0], xs[1])


class ProgramParser(TextParsers):

    # Actual grammar
    split1 = lambda item, separator: item & rep(separator & item)
    split = lambda item, separator: opt(split1(item, separator))

    identifier = reg(r"[a-zA-Z]\w*")

    string = reg(r'".*?(?<!\\)(\\\\)*?"') | reg(r"'.*?(?<!\\)(\\\\)*?'") > (
        lambda s: TokenString(s[1:-1])
    )

    num_int = reg(r"\d+") > int
    num_float = reg(r"(\d*\.\d+|\d+\.\d*)") > float
    num_positive = num_float | num_int
    num_negative = "-" >> num > (lambda x: -x)
    num = num_negative | num_positive
    number = num > TokenNumber

    op_eq = lit("==") > constant(Operator.EQ)
    op_ne = lit("!=") > constant(Operator.NE)
    op_ge = lit(">=") > constant(Operator.GE)
    op_gt = lit(">") > constant(Operator.GT)
    op_le = lit("<=") > constant(Operator.LE)
    op_lt = lit("<") > constant(Operator.LT)
    op_and = lit("&") > constant(Operator.AND)
    op_or = lit("|") > constant(Operator.OR)
    op_add = lit("+") > constant(Operator.ADD)
    op_sub = lit("-") > constant(Operator.SUB)
    op_mul = lit("*") > constant(Operator.MUL)
    op_div = lit("/") > constant(Operator.DIV)
    op_pow = lit("^") > constant(Operator.POW)
    op_not = lit("!") > constant(Operator.NOT)
    op_neg = lit("-") > constant(Operator.NEG)

    equality_op = op_eq | op_ne
    comparison_op = op_ge | op_gt | op_le | op_lt
    logic_op = op_and | op_or
    term_op = op_add | op_sub
    factor_op = op_mul | op_div
    power_op = op_pow
    unary_op = op_neg | op_not

    case_pair = expr << "->" & expr

    assignment = identifier << "=" & expr
    let_stmt = "^" >> rep1sep(assignment, ";") << "$" & expr > let

    anon_func = (lit("\\") | lit("\\\\")) >> rep1(identifier) & "->" >> expr > anon

    variable = identifier > TokenVariable

    expr = rep1sep(equality, reg(r"\s*")) > maybe_application
    equality = split1(comparison, equality_op) > bin_operator
    comparison = split1(logic, comparison_op) > bin_operator
    logic = split1(term, logic_op) > bin_operator
    term = split1(factor, term_op) > bin_operator
    factor = split1(power, factor_op) > bin_operator
    power = split1(ternary, power_op) > bin_operator_right
    ternary = case & opt("?" >> expr << ":" & expr) > maybe_ternary
    case = dice & opt(lit("$") >> "(" >> rep1sep(case_pair, ";") << ")") > maybe_case
    dice = unary & opt("d" >> unary) > maybe_dice
    unary = unary_op & unary | primary > mon_operator
    primary = number | string | bracketed | let_stmt | anon_func | variable
    bracketed = "(" >> expr << ")"

    func = identifier & "=" >> expr > function

    program = repsep("@" >> func | expr, ";") << opt(";") > Program

    main = program


class DiscordParser(TextParsers):
    """Removes surrounding code blocks before the program can reach the main parser"""

    main = (
        "```" >> reg(r"(?s).*?(?=```)") << "```"
        | "`" >> reg(r"(?s).*?(?=`)") << "`"
        | reg(r"[^`](?s).*")
    )


def parse_program(source: str):
    try:
        no_blocks = DiscordParser.main.parse(source).or_die()
    except ParseError:
        raise ParseError("Unclosed code blocks")
    try:
        ast = ProgramParser.main.parse(no_blocks).or_die()
    except ParseError as e:
        raise ParseError(format_parse_error(e, source))
    return ast


def format_parse_error(err, source):
    found = re.search(r"(?<=but found ').*?(?=')", err.message)
    if found is None:
        last_line = source.split("\n")[-1]
        pointer = last_line + "\n" + " " * (len(last_line) - 1) + "^"
        return f"Found unexpected end of source\n{pointer}"
    else:
        found = found.group(0)
        try:
            line = re.findall(r"(?<=Line )\d+", err.message)[-1]
            char = re.findall(r"(?<=character )\d+", err.message)[-1]
            pointer = (
                source.split("\n")[int(line) - 1] + "\n" + " " * (int(char) - 1) + "^"
            )
            return f"Unexpected token {found}\nLine: {line}\nChar: {char}\n{pointer}"
        except IndexError:
            return f"Unexpected token {found}"
