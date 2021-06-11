from utils.exceptions import InternalError, OutputTooLargeError, WarningError


def trace2log(trace):
    trace = trace[1:]  # The first element is always an empty let statement
    out = "Exception in\n    " + "\nin\n    ".join([str(t) for t in reversed(trace)])
    return out


"""User errors"""


class RunTimeError(Exception):
    """Raised when an error occurs while evaluating a program"""


class TypeError(RunTimeError):
    """Raised when types mismatch"""

    def __init__(self, message="Mismatched types"):
        self.message = message.format(expr=trace2log(trace))
        super().__init__(self.message)


class UndefinedIdentifierError(RunTimeError):
    """Raised when an unexpected identifier is detected"""

    def __init__(
        self, trace, identifier, message="'{id}' is not defined in scope\n{expr}"
    ):
        self.message = message.format(id=identifier, expr=trace2log(trace))
        super().__init__(self.message)


class CaseFailureError(RunTimeError):
    """Raised when the value given to a case statement has no matching pattern"""

    def __init__(self, trace, message="Case for input not found\n{expr}"):
        self.message = message.format(expr=trace2log(trace))
        super().__init__(self.message)


class ZeroDivisionError(RunTimeError):
    """Raised when dividing by zero"""

    def __init__(self, trace, message="Division by zero\n{expr}"):
        self.message = message.format(expr=trace2log(trace))
        super().__init__(self.message)


class DiceError(RunTimeError):
    """Raised when there is an issue with rolling dice"""


class ExcessiveDiceRollsError(WarningError):
    """Raised when too many dice are rolled in a single command"""

    def __init__(
        self,
        trace,
        out="You requested an excessive number of dice rolls.",
        message="Number of total dice rolls exceeded limit\n{expr}",
    ):
        self.out = out
        self.message = message.format(expr=trace2log(trace))
        super().__init__(self.message)


class FloatingPointDiceInputError(DiceError):
    """Raised when the number of rolls or sides of a dice roll is a non-integer"""


class FloatingPointDiceCountError(FloatingPointDiceInputError):
    """Raised when the number of rolls of a dice roll is a non-integer"""

    def __init__(
        self,
        trace,
        value,
        message="Requested dice roll had a non-integer count: {value}\n{expr}",
    ):
        self.value = value
        self.message = message.format(value=value, expr=trace2log(trace))
        super().__init__(self.message)


class FloatingPointDiceSidesError(FloatingPointDiceInputError):
    """Raised when the number of sides of a dice roll is a non-integer"""

    def __init__(
        self,
        trace,
        value,
        message="Requested dice roll had a non-integer number of sides: {value}\n{expr}",
    ):
        self.value = value
        self.message = message.format(value=value, expr=trace2log(trace))
        super().__init__(self.message)


class ZeroDiceInputError(DiceError):
    """Raised when the number of rolls or sides of a dice roll is zero"""


class ZeroDiceCountError(ZeroDiceInputError):
    """Raised when the number of rolls of a dice roll is zero"""

    def __init__(self, trace, message="Requested dice roll a count of zero\n{expr}"):
        self.message = message.format(expr=trace2log(trace))
        super().__init__(self.message)


class ZeroDiceSidesError(ZeroDiceInputError):
    """Raised when the number of sides of a dice roll is zero"""

    def __init__(self, trace, message="Requested dice roll had zero sides\n{expr}"):
        self.message = message.format(expr=trace2log(trace))
        super().__init__(self.message)


class NegativeDiceInputError(DiceError):
    """Raised when the number of rolls or sides of a dice roll is negative"""


class NegativeDiceCountError(NegativeDiceInputError):
    """Raised when the number of rolls of a dice roll is negative"""

    def __init__(
        self,
        trace,
        value,
        message="Requested dice roll had a negative count: {value}\n{expr}",
    ):
        self.value = value
        self.message = message.format(value=value, expr=trace2log(trace))
        super().__init__(self.message)


class NegativeDiceSidesError(NegativeDiceInputError):
    """Raised when the number of sides of a dice roll is negative"""

    def __init__(
        self,
        trace,
        value,
        message="Requested dice roll had a negative number of sides: {value}\n{expr}",
    ):
        self.value = value
        self.message = message.format(value=value, expr=trace2log(trace))
        super().__init__(self.message)


"""Internal errors"""


class NoValueDefinedError(InternalError):
    """Raised when a parser token does not define a "value" attribute"""

    def __init__(self, trace, message='Parser token has no "value" attribute\n{expr}'):
        self.message = message.format(expr=trace2log(trace))
        super().__init__(self.message)


class NoRollCountDefinedError(InternalError):
    """Raised when a parser token does not define a "roll_count" attribute"""

    def __init__(
        self, trace, message='Parser token has no "roll_count" attribute\n{expr}'
    ):
        self.message = message.format(expr=trace2log(trace))
        super().__init__(self.message)
