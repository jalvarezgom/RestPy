import datetime

from exceptions.validators import RestPyValidatorException


class BaseValidator:
    _base_message = "Field: {field_name} Value: {value} | MSG:"
    _error_message = None

    @classmethod
    def error_message(cls, error_fields={}):
        return f"{cls._error_message}".format(**error_fields)

    @classmethod
    def get_error_message(cls, error_fields={}, error_msg=None):
        return f"{cls.__name__} {cls._base_message} {error_msg}".format(**error_fields)

    @classmethod
    def validate(cls, field_name, original_value):
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
                lerror_msg.insert(0, "Lista de errores identificados:")
            error_fields["field_name"] = field_name
            error_fields["value"] = original_value
            error_msg = cls.get_error_message(error_fields, "\n".join(lerror_msg))
        if not isinstance(original_value, list):
            return (new_lvalues[0], error_msg)
        return (new_lvalues, error_msg)

    @classmethod
    def _run_validation(cls, value):
        raise NotImplementedError("Subclasses must implement this method.")


class ChoiceValidator(BaseValidator):
    _error_message = "Debe ser una opcion valida entre los choices {choice_class}"
    _choice_class = None

    @classmethod
    def _run_validation(cls, value):
        if value not in cls._choice_class:
            return (None, {"choice_class": cls._choice_class})
        return (value, {})


class DatetimeValidator(BaseValidator):
    _error_message = "Debe ser un objeto datetime o str con formato {format_date}"
    to_string = True
    format_date = None

    @classmethod
    def _run_validation(cls, value):
        if isinstance(value, datetime.datetime):
            value = datetime.datetime.strftime(value, cls.format_date) if cls.to_string else value
        else:
            if isinstance(value, str) and not cls.to_string:
                return (None, {"to_string": cls.to_string})
            try:
                value = datetime.datetime.strptime(value, cls.format_date)
            except Exception:
                return (None, {"format_date": cls.format_date})
        return (value, {})


class IgnoreCaseValidator(BaseValidator):
    @classmethod
    def _run_validation(cls, value):
        return (value, {})
