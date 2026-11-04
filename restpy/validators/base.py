import datetime

from restpy.exceptions.validators import RestPyValidatorException


class BaseValidator:
    """Base of the field validators; subclasses implement `_run_validation`.

    Validators are used through the class method `validate`, but `RESTpyField` expects an
    instance. A list value is validated item by item.
    """

    _base_message = "Field: {field_name} Value: {value} | MSG:"
    _error_message = None

    @classmethod
    def error_message(cls, error_fields=None):
        """Format the class's `_error_message` with `error_fields`."""
        return f"{cls._error_message}".format(**(error_fields or {}))

    @classmethod
    def get_error_message(cls, error_fields=None, error_msg=None):
        """Build the full message: validator name, field, value and `error_msg`."""
        return f"{cls.__name__} {cls._base_message} {error_msg}".format(**(error_fields or {}))

    @classmethod
    def validate(cls, field_name, original_value):
        """Validate a value.

        Returns:
            `(value, exception)`: the (possibly normalized) value and None, or None and a
            `RestPyValidatorException`. A None `original_value` passes as `(None, None)`.
        """
        (values, exception_msg) = cls._validate(field_name, original_value)
        if exception_msg:
            exception_msg = RestPyValidatorException(exception_msg)
        return (values, exception_msg)

    @classmethod
    def _validate(cls, field_name, original_value):
        if original_value is None:
            return (None, None)
        (new_lvalues, lerror_msg) = [], []
        lvalue = [original_value] if not isinstance(original_value, list) else original_value
        for idx, value in enumerate(lvalue):
            (nvalue, error_fields) = cls._run_validation(value)
            new_lvalues.append(nvalue)
            if nvalue is None:
                lerror_msg.append(f"idx: {idx} " + cls.error_message(error_fields))
        error_msg = None
        if not len(lerror_msg) == 0:
            if len(lerror_msg) > 1:
                lerror_msg.insert(0, "Errors found:")
            error_fields["field_name"] = field_name
            error_fields["value"] = original_value
            error_msg = cls.get_error_message(error_fields, "\n".join(lerror_msg))
        if not isinstance(original_value, list):
            return (new_lvalues[0], error_msg)
        return (new_lvalues, error_msg)

    @classmethod
    def _run_validation(cls, value):
        """Validate one item. Return `(new_value, error_fields)`; a `new_value` of None means invalid."""
        raise NotImplementedError("Subclasses must implement this method.")


class ChoiceValidator(BaseValidator):
    """Accept only values contained in `_choice_class` (an Enum, list or similar); set it in a subclass."""

    _error_message = "Must be one of the valid choices in {choice_class}"
    _choice_class = None

    @classmethod
    def _run_validation(cls, value):
        if value not in cls._choice_class:
            return (None, {"choice_class": cls._choice_class})
        return (value, {})


class DatetimeValidator(BaseValidator):
    """Accept a `datetime` or a `str` in `format_date` (ISO 8601 when it is None).

    With `to_string=True` the output is a `str`; with `False` it is a `datetime`.
    """

    _error_message = "Must be a datetime object or a str with format {format_date}"
    to_string = True
    format_date = None

    @classmethod
    def _run_validation(cls, value):
        error = (None, {"format_date": cls.format_date})
        if isinstance(value, datetime.datetime):
            return (datetime.datetime.strftime(value, cls.format_date) if cls.to_string else value, {})
        if not isinstance(value, str):
            return error
        try:
            parsed = datetime.datetime.strptime(value, cls.format_date) if cls.format_date else datetime.datetime.fromisoformat(value)
        except ValueError:
            return error
        return (value if cls.to_string else parsed, {})


class IgnoreCaseValidator(BaseValidator):
    """Accepts any value unchanged. Despite the name it does no case handling."""

    @classmethod
    def _run_validation(cls, value):
        return (value, {})
