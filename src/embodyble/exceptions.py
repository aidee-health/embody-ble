"""Exceptions specific to this labrary."""


class EmbodyBleError(Exception):
    """Exception used as base exception for package errors."""

    def __init__(self, msg, error_code=None):
        super().__init__(msg)
        self.msg = msg
        self.error_code = error_code
