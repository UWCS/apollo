import logging
import random
from abc import ABC, abstractmethod
from copy import copy
from enum import Enum, auto

import roll.exceptions as rollerr

# import * imports all tokens, operators, the Assignment class, and the root Program class
__all__ = [
    "TokenNumber",
    "TokenString",
    "TokenRoll",
    "TokenVariable",
    "TokenLet",
    "TokenFunction",
    "TokenApplication",
    "TokenOperator",
    "TokenTernary",
    "TokenCase",
    "Program",
    "Assignment",
    "Operator",
]


MAX_ROLLS = 1000


def isfunction(token):
    return isinstance(token, TokenFunction)


class Environment:
    def __init__(self, root):
        self.root = root
        self.closure = {}
        self.trace = []

    def copy(self):
        out = Environment(self.root)
        out.closure = self.closure.copy()
        out.trace = self.trace
        return out


class HashCounter:
    """A mutating object that records the variable IDs to be used in general hashing and eta-reduction hashing"""

    def __init__(self):
        self.__next_id = 0
        self.__next_scope_id = -1
        self.trace = []

    @property
    def next_id(self):
        return self.__next_id

    def pop_id(self):
        id = self.__next_id
        self.__next_id += 1
        return id

    @property
    def next_scope_id(self):
        return self.__next_scope_id

    def pop_scope_id(self):
        id = self.__next_scope_id
        self.__next_scope_id -= 1
        return id


def trace(func):
    """A decorator that updates the environment/counter to know its position in the current expression"""

    def wrapper(*args, **kwargs):
        # args[0] will be self (the expression token object)
        # args[1] should always be the env/map object
        args[1].trace.append(args[0])
        out = func(*args, **kwargs)
        args[1].trace.pop()
        return out

    return wrapper


class IToken(ABC):
    @trace
    @abstractmethod
    def reduce(self, env, counter):
        """Returns a fully reduced version of the token"""
        raise NotImplementedError

    @abstractmethod
    def substitute(self, old_to_new):
        """Returns a deep copy of the token where each variable with an ID in the map is replaced by a copy with the new ID"""
        raise NotImplementedError

    @abstractmethod
    def __str__(self):
        """Recursively constructs a string representation of the token"""
        raise NotImplementedError

    def dereference(self, env):
        """Attempts to deference the token if it is a pointer"""
        return self

    @trace
    @abstractmethod
    def hash_vars(self, counter, map):
        """Recursively sets the IDs of variables to be unique"""
        raise NotImplementedError


class IPure(ABC):
    @property
    @abstractmethod
    def pure(self):
        """Returns the value of a reduced token in Python primitives"""
        raise NotImplementedError


class TokenNumber(IToken, IPure):
    def __init__(self, value):
        self.__value = value
        logging.debug(self.__class__.__name__, self)

    @trace
    def reduce(self, env, counter):
        return self

    def substitute(self, _):
        return TokenNumber(self.__value)

    @trace
    def hash_vars(self, counter, map):
        pass

    def __str__(self):
        return str(self.__value)

    @property
    def pure(self):
        return self.__value

    def __eq__(self, other):
        return isinstance(other, TokenNumber) and self.__value == other.__value


class TokenString(IToken, IPure):
    def __init__(self, value):
        self.__value = value
        logging.debug(self.__class__.__name__, self)

    @trace
    def reduce(self, env, counter):
        return self

    def substitute(self, _):
        return TokenString(self.__value)

    @trace
    def hash_vars(self, counter, map):
        pass

    def __str__(self):
        unescaped = '"'
        escaped = r"\""
        return f'"{self.__value.replace(unescaped, escaped)}"'

    @property
    def pure(self):
        return self.__value

    def __eq__(self, other):
        return isinstance(other, TokenString) and self.__value == other.__value


class TokenRoll(IToken):
    def __init__(self, count, sides):
        self.count = count
        self.sides = sides
        logging.debug(self.__class__.__name__, self)

    @trace
    def reduce(self, env, counter):
        sides = self.sides.reduce(env, counter).pure
        if sides == 0:
            raise rollerr.ZeroDiceSidesError(env.trace)
        if sides < 0:
            raise rollerr.NegativeDiceSidesError(env.trace, sides)
        if int(sides) != sides:
            raise rollerr.FloatingPointDiceSidesError(env.trace, sides)
        count = self.count.reduce(env, counter).pure
        if count == 0:
            raise rollerr.ZeroDiceCountError(env.trace)
        if count < 0:
            raise rollerr.NegativeDiceCountError(env.trace, count)
        if int(count) != count:
            raise rollerr.FloatingPointDiceCountError(env.trace, count)
        if sides == 1:
            return TokenNumber(count)
        if count > MAX_ROLLS:
            raise rollerr.ExcessiveDiceRollsError(env.trace)
        return TokenNumber(sum(random.choices(range(1, sides + 1), k=count)))

    def substitute(self, old_to_new):
        return TokenRoll(
            self.count.substitute(old_to_new), self.sides.substitute(old_to_new)
        )

    @trace
    def hash_vars(self, counter, map):
        self.count.hash_vars(counter, map)
        self.sides.hash_vars(counter, map)

    def __str__(self):
        count = str(self.count)
        sides = str(self.sides)
        if not isinstance(self.count, TokenNumber):
            count = f"({count})"
        if not isinstance(self.sides, TokenNumber):
            sides = f"({sides})"
        return f"{count}d{sides}"


class TokenVariable(IToken):
    def __init__(self, name, id=None):
        self.name = name
        self.identifier = hash(name) if id is None else id
        logging.debug(self.__class__.__name__, self)

    @trace
    def reduce(self, env, counter):
        return self.dereference(env).reduce(env, counter)

    def substitute(self, old_to_new):
        return TokenVariable(
            self.name,
            old_to_new[self.identifier]
            if self.identifier in old_to_new
            else self.identifier,
        )

    @trace
    def hash_vars(self, counter, map):
        try:
            self.identifier = map[self.name]
        except KeyError:
            raise rollerr.UndefinedIdentifierError(counter.trace, self.name)

    def __str__(self):
        return f"{self.name}"  # _{self.identifier}"

    def dereference(self, env):
        id = self.identifier
        try:
            return env.closure[id].dereference(env)
        except KeyError:
            raise rollerr.UndefinedIdentifierError(env.trace, self.name)


class TokenLet(IToken):
    """declarations = [Assignment*]"""

    def __init__(self, declarations, expression):
        self.declarations = declarations
        self.expression = expression
        logging.debug(self.__class__.__name__, self)

    @trace
    def reduce(self, env, counter):
        new_env = self.update_env(env)
        return self.expression.reduce(new_env, counter)

    def substitute(self, old_to_new):
        # Remove variables from the mapping that are hidden by let declarations
        old_to_new = old_to_new.copy()
        for decl in self.declarations:
            old_to_new.pop(decl.identifier, None)
        # Copy the declarations
        new_decls = []
        for decl in self.declarations:
            new_decls.append(
                Assignment(
                    decl.name, decl.expression.substitute(old_to_new), decl.identifier
                )
            )
        # Copy the let body
        new_expr = self.expression.substitute(old_to_new)
        # Return reconstructed let statement
        return TokenLet(new_decls, new_expr)

    @trace
    def hash_vars(self, counter, map):
        new_map = map.copy()
        for i in range(len(self.declarations)):
            decl = self.declarations[i]
            new_map[decl.name] = counter.next_id
            self.declarations[i].identifier = counter.next_id
            counter.pop_id()
        for decl in self.declarations:
            decl.expression.hash_vars(counter, new_map)
        self.expression.hash_vars(counter, new_map)

    def update_env(self, env):
        new_env = env.copy()
        for decl in self.declarations:
            new_env.closure[decl.identifier] = decl.expression
        return new_env

    def __str__(self):
        return f"^{', '.join([f'{d.name}={d.expression}' for d in self.declarations])}${self.expression}"


class TokenFunction(IToken):
    def __init__(self, arg_name, expression, arg_id=None):
        self.arg_name = arg_name
        self.arg_id = arg_id if arg_id is not None else hash(arg_name)
        self.expression = expression
        logging.debug(self.__class__.__name__, self)

    @trace
    def reduce(self, env, counter):
        return self

    def substitute(self, old_to_new):
        # If the function arg hides a variable in the map, remove it
        if self.arg_id in old_to_new:
            old_to_new = old_to_new.copy()
            del old_to_new[self.arg_id]
        # Copy the function body
        new_expr = self.expression.substitute(old_to_new)
        # Return reconstructed function statement
        return TokenFunction(self.arg_name, new_expr, self.arg_id)

    @trace
    def hash_vars(self, counter, map):
        new_map = map.copy()
        new_map[self.arg_name] = counter.next_id
        self.arg_id = counter.next_id
        counter.pop_id()
        self.expression.hash_vars(counter, new_map)

    def __str__(self):
        return f"({self.arg_name}->{self.expression})"


class TokenApplication(IToken):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs
        logging.debug(self.__class__.__name__, self)

    @trace
    def reduce(self, env, counter):
        # Apply as many arguments as possible (assumes the application is valid)
        # May result in a partially-applied function
        # Create declarations from lhs function(s)
        out = self.lhs.dereference(env)
        decls = []
        for expr in self.rhs:
            decls.append(Assignment(out.arg_name, expr, id=out.arg_id))
            out = (
                out.expression
            )  # Note: this used to attempt to .dereference() - I can't remember why but it seems to work without it
        # Substitute variables for scoped variables (allows recursion)
        substitutions = {}
        env = env.copy()
        for decl in decls:
            substitutions[decl.identifier] = counter.next_scope_id
            env.closure[counter.next_scope_id] = decl.expression
            counter.pop_scope_id()
        out = out.substitute(substitutions)
        # Check if the application was partial
        # If it was, extract the rest of the function arguments and put the Let token at the bottom
        if isfunction(out):
            func_path = [out]
            out = out.expression.dereference(env)
            while isfunction(out):
                func_path.append(out)
                out = out.expression.dereference(env)
            func_path[-1] = TokenFunction(
                func_path[-1].arg_name,
                TokenLet(decls, out),
                func_path[-1].arg_id - 1000,
            )
            for i in range(len(func_path) - 1, 0, -1):
                func_path[i - 1] = TokenFunction(
                    func_path[i - 1].arg_name,
                    func_path[i],
                    func_path[i - 1].arg_id - 1000,
                )
            result = func_path[0]
        # If it wasn't, return the fully applied function expression
        else:
            result = TokenLet(decls, out)
        return result.reduce(env, counter)

    def substitute(self, old_to_new):
        lhs = self.lhs.substitute(old_to_new)
        rhs = [expr.substitute(old_to_new) for expr in self.rhs]
        return TokenApplication(lhs, rhs)

    @trace
    def hash_vars(self, counter, map):
        self.lhs.hash_vars(counter, map)
        for expr in self.rhs:
            expr.hash_vars(counter, map)

    def __str__(self):
        return f"{self.lhs} {' '.join([str(expr) for expr in self.rhs])}"


class Operator(Enum):
    EQ = auto()
    NE = auto()
    GT = auto()
    GE = auto()
    LT = auto()
    LE = auto()
    AND = auto()
    OR = auto()
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    POW = auto()
    NOT = auto()
    NEG = auto()

    def __str__(self):
        mapping = {
            Operator.EQ: "==",
            Operator.NE: "!=",
            Operator.GE: ">=",
            Operator.GT: ">",
            Operator.LE: "<=",
            Operator.LT: "<",
            Operator.AND: "&",
            Operator.OR: "|",
            Operator.ADD: "+",
            Operator.SUB: "-",
            Operator.MUL: "*",
            Operator.DIV: "/",
            Operator.POW: "^",
            Operator.NOT: "!",
            Operator.NEG: "-",
        }
        return mapping[self]


class TokenOperator(IToken):
    mapping = {
        Operator.EQ: lambda xs: int(xs[0] == xs[1]),
        Operator.NE: lambda xs: int(xs[0] != xs[1]),
        Operator.GE: lambda xs: int(xs[0] >= xs[1]),
        Operator.GT: lambda xs: int(xs[0] > xs[1]),
        Operator.LE: lambda xs: int(xs[0] <= xs[1]),
        Operator.LT: lambda xs: int(xs[0] < xs[1]),
        Operator.AND: lambda xs: int(xs[0] and xs[1]),
        Operator.OR: lambda xs: int(xs[0] or xs[1]),
        Operator.ADD: lambda xs: xs[0] + xs[1],
        Operator.SUB: lambda xs: xs[0] - xs[1],
        Operator.MUL: lambda xs: xs[0] * xs[1],
        Operator.DIV: lambda xs: xs[0] / xs[1],
        Operator.POW: lambda xs: xs[0] ** xs[1],
        Operator.NOT: lambda xs: 0 if xs[0] else 1,
        Operator.NEG: lambda xs: -xs[0],
    }

    def __init__(self, op, args):
        self.op = op
        self.args = args
        logging.debug(self.__class__.__name__, self)

    @trace
    def reduce(self, env, counter):
        try:
            value = TokenOperator.mapping[self.op](
                [a.reduce(env, counter).pure for a in self.args]
            )
        except ZeroDivisionError:
            raise rollerr.ZeroDivisionError(env.trace)

        if value == True:
            value = 1
        elif value == False:
            value = 0
        return TokenNumber(value)

    def substitute(self, old_to_new):
        new_args = []
        for arg in self.args:
            new_args.append(arg.substitute(old_to_new))
        return TokenOperator(self.op, new_args)

    @trace
    def hash_vars(self, counter, map):
        for arg in self.args:
            arg.hash_vars(counter, map)

    def __str__(self):
        if len(self.args) == 1:
            return f"{self.op}{str(self.args[0])}"
        if len(self.args) == 2:
            return f"({str(self.args[0])}{self.op}{str(self.args[1])})"


class TokenTernary(IToken):
    def __init__(self, condition, true, false):
        self.condition = condition
        self.true = true
        self.false = false
        logging.debug(self.__class__.__name__, self)

    @trace
    def reduce(self, env, counter):
        return (
            self.true.reduce(env, counter)
            if self.condition.reduce(env, counter).pure
            else self.false.reduce(env, counter)
        )

    def substitute(self, old_to_new):
        condition = self.condition.substitute(old_to_new)
        true = self.true.substitute(old_to_new)
        false = self.false.substitute(old_to_new)
        return TokenTernary(condition, true, false)

    def rolls(self, env):
        return self.condition.rolls(env) + self.true.rolls(env) + self.false.rolls(env)

    @trace
    def hash_vars(self, counter, map):
        self.condition.hash_vars(counter, map)
        self.true.hash_vars(counter, map)
        self.false.hash_vars(counter, map)

    def __str__(self):
        return f"{self.condition}?{self.true}:{self.false}"


class TokenCase(IToken):
    def __init__(self, expression, pairs):
        self.expression = expression
        self.pairs = pairs
        logging.debug(self.__class__.__name__, self)

    @trace
    def reduce(self, env, counter):
        value = self.expression.reduce(env, counter).pure
        for pair in self.pairs:
            if value == pair[0].reduce(env, counter).pure:
                return pair[1].reduce(env, counter)
        raise rollerr.CaseFailureError(env.trace)

    def substitute(self, old_to_new):
        new_expr = self.expression.substitute(old_to_new)
        new_pairs = []
        for pair in self.pairs:
            new_pairs.append(
                [pair[0].substitute(old_to_new), pair[1].substitute(old_to_new)]
            )
        return TokenCase(new_expr, new_pairs)

    @trace
    def hash_vars(self, counter, map):
        self.expression.hash_vars(counter, map)
        for pair in self.pairs:
            pair[0].hash_vars(counter, map)
            pair[1].hash_vars(counter, map)

    def __str__(self):
        return f"{str(self.expression)}$({'; '.join([f'{x[0]}->{x[1]}' for x in self.pairs])})"


class Program:
    """Has a subset of a regular Token's functionality"""

    def __init__(self, expressions):
        # Sort program into function assignments and expressions
        self.expressions = []
        self.assignments = []
        for expr in expressions:
            if isinstance(expr, Assignment):
                # if expr.identifier not in self.assignments:
                #     self.assignments[expr.identifier] = []
                # self.assignments[expr.identifier].append(expr.expression)
                self.assignments.append(expr)
            else:
                self.expressions.append(expr)
        # Desugar program to a list of let statements
        self.lets = []
        for expr in self.expressions:
            self.lets.append(TokenLet(self.assignments, expr))
        # Create environment and hash counter
        self.environment = Environment(self)
        self.counter = HashCounter()
        # Debug
        logging.debug(self.__class__.__name__, self)

    def reduce(self):
        """Intentionally does not use the @trace decorator"""
        self.hash_vars()
        out = [let.reduce(self.environment, self.counter) for let in self.lets]
        return out

    def hash_vars(self):
        """Intentionally does not use the @trace decorator"""
        map = {}
        for a in self.assignments:
            map[a.name] = self.counter.next_id
            a.identifier = self.counter.next_id
            self.counter.pop_id()
        for a in self.assignments:
            a.expression.hash_vars(self.counter, map)
        for e in self.expressions:
            e.hash_vars(self.counter, map)

    def __str__(self):
        if len(self.expressions) == 1:
            return str(self.expressions[0])
        return f"<{' ; '.join([str(e) for e in self.expressions])}>"

    @property
    def string_rep(self):
        return self.StringRep(self.expressions, self.assignments)

    class StringRep:
        def __init__(self, expressions, assignments):
            self.expressions = [str(e) for e in expressions]
            self.assignment_names = [str(a.name) for a in assignments]
            self.assignment_exprs = [str(a.expression) for a in assignments]
            self.assignments = [
                (self.assignment_names[i], self.assignment_exprs[i])
                for i in range(len(assignments))
            ]


class Assignment:
    def __init__(self, name, expression, id=None):
        self.name = name
        self.expression = expression
        self.identifier = id if id is not None else hash(name)

    def __str__(self):
        return f"<{self.name}, {self.identifier}, {self.expression}>"
