from exceptions.base import RestPyException


class RestPyValidatorException(RestPyException):
    base_message = "Validator error"


class RESTpyValidatorRequestMethodException(RestPyValidatorException):
    base_message = "Request method not supported"
