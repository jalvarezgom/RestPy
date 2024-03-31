from exceptions.base import RestPyException


class RestPyAuthException(RestPyException):
    base_message = "Auth error"
