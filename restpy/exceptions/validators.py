from restpy.exceptions.base import RestPyException


class RestPyValidatorException(RestPyException):
    base_message = "Validator error"
