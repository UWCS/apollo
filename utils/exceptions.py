class WarningError(Exception):
    """Raised when a user request is flagged as potentially malicious"""

    """Should define __init__(self, out: str, message: str), where out is the user-facing reply"""


class OutputTooLargeError(WarningError):
    """Raised when a message is too long to send to Discord"""

    def __init__(
        self,
        out="Your requested output was too large!",
        message="Maximum Discord message length exceeded",
    ):
        self.out = out
        self.message = message
        super().__init__(self.message)


class InternalError(Exception):
    """Raised when something has gone wrong with the source code"""
