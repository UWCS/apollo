from abc import ABC, abstractmethod

from utils import clean_brackets
from utils.exceptions import InternalError, WarningError


def trace2log(trace):
    trace = trace[1:]  # The first element is always an empty let statement
    if len(trace) > 5:  # Limit the size of the trace to reduce error message size
        trace = trace[:2] + ["..."] + trace[-3:]
    out = "Exception in\n    " + "\nin\n    ".join(
        [clean_brackets(str(t)) for t in reversed(trace)]
    )
    return out


# User errors


class RunTimeError(Exception, ABC):
    """Raised when an error occurs while evaluating a program"""

    @abstractmethod
    def __init__(self, trace, message="{trace}"):
        self.message = message.format(trace=trace2log(trace))
        super().__init__(self.message)


class UndefinedIdentifierError(RunTimeError):
    """Raised when an unexpected identifier is detected"""

    def __init__(
        self, trace, identifier, message="'{id}' is not defined in scope\n{trace}"
    ):
        self.message = message.format(trace=trace2log(trace), id=identifier)
        super().__init__([], self.message)


class CaseFailureError(RunTimeError):
    """Raised when the value given to a case statement has no matching pattern"""

    def __init__(self, trace, message="Case for input not found\n{trace}"):
        super().__init__(trace, message)


class ZeroDivisionError(RunTimeError):
    """Raised when dividing by zero"""

    def __init__(self, trace, message="Division by zero\n{trace}"):
        super().__init__(trace, message)


class ExcessiveDiceRollsError(WarningError, RunTimeError):
    """Raised when too many dice are rolled in a single command"""

    def __init__(
        self,
        trace,
        out="You requested an excessive number of dice rolls.",
        message="Number of total dice rolls exceeded limit\n{trace}",
    ):
        super().__init__(out, message.format(trace=trace2log(trace)))


class DiceInputError(RunTimeError, ABC):
    """Raised when there is an issue with the inputs of a dice roll"""

    @abstractmethod
    def __init__(self, trace, value, message="{value}\n{trace}"):
        self.message = message.format(trace=trace2log(trace), value=value)
        super().__init__([], self.message)


class FloatingPointDiceInputError(DiceInputError, ABC):
    """Raised when the number of rolls or sides of a dice roll is a non-integer"""

    pass


class FloatingPointDiceCountError(FloatingPointDiceInputError):
    """Raised when the number of rolls of a dice roll is a non-integer"""

    def __init__(
        self,
        trace,
        value,
        message="Requested dice roll had a non-integer count: {value}\n{trace}",
    ):
        super().__init__(trace, value, message)


class FloatingPointDiceSidesError(FloatingPointDiceInputError):
    """Raised when the number of sides of a dice roll is a non-integer"""

    def __init__(
        self,
        trace,
        value,
        message="Requested dice roll had a non-integer number of sides: {value}\n{trace}",
    ):
        super().__init__(trace, value, message)


class ZeroDiceInputError(DiceInputError):
    """Raised when the number of rolls or sides of a dice roll is zero"""

    pass


class ZeroDiceCountError(ZeroDiceInputError):
    """Raised when the number of rolls of a dice roll is zero"""

    def __init__(self, trace, message="Requested dice roll a count of zero\n{trace}"):
        super().__init__(trace, 0, message)


class ZeroDiceSidesError(ZeroDiceInputError):
    """Raised when the number of sides of a dice roll is zero"""

    def __init__(self, trace, message="Requested dice roll had zero sides\n{trace}"):
        super().__init__(trace, 0, message)


class NegativeDiceInputError(DiceInputError):
    """Raised when the number of rolls or sides of a dice roll is negative"""

    pass


class NegativeDiceCountError(NegativeDiceInputError):
    """Raised when the number of rolls of a dice roll is negative"""

    def __init__(
        self,
        trace,
        value,
        message="Requested dice roll had a negative count: {value}\n{trace}",
    ):
        super().__init__(trace, value, message)


class NegativeDiceSidesError(NegativeDiceInputError):
    """Raised when the number of sides of a dice roll is negative"""

    def __init__(
        self,
        trace,
        value,
        message="Requested dice roll had a negative number of sides: {value}\n{trace}",
    ):
        super().__init__(trace, value, message)


# Internal errors


class NoValueDefinedError(InternalError):
    """Raised when a parser token does not define a "value" attribute"""

    def __init__(self, trace, message='Parser token has no "value" attribute\n{trace}'):
        self.message = message.format(trace=trace2log(trace))
        super().__init__(self.message)


class NoRollCountDefinedError(InternalError):
    """Raised when a parser token does not define a "roll_count" attribute"""

    def __init__(
        self, trace, message='Parser token has no "roll_count" attribute\n{trace}'
    ):
        self.message = message.format(trace=trace2log(trace))
        super().__init__(self.message)
