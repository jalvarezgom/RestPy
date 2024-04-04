import numbers

from validators.base import BaseValidator


class StrValidator(BaseValidator):
    _error_message = "It must be a string."

    @classmethod
    def _run_validation(cls, value):
        if not isinstance(value, str):
            if isinstance(value, numbers.Number):
                value = str(value)
            else:
                return (None, {})
        return (value, {})
