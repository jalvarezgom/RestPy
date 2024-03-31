import numbers

from validators.base import BaseValidator


class NumberValidator(BaseValidator):
    _error_message = 'It must be a number.'

    @classmethod
    def _run_validation(cls, value):
        if not isinstance(value, numbers.Number):
            return None, {}
        return value, {}