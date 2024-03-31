from exceptions.base import RESTpyException


class RESTpyValidatorException(RESTpyException):
    base_message = "Validator error"