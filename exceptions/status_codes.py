from http import HTTPStatus
from typing import List

from exceptions.base import RestPyRunnerException


class RestPyStatusCodeException(RestPyRunnerException):
    status_code: List[HTTPStatus] = None
    base_message = "Request - There was a problem with the request, check the response"

    @property
    def status_description(self):
        try:
            return self.status_code.description
        except AttributeError:
            return "Undefined status description"

    @property
    def message(self):
        return f"[RESTpy] Exception:{self.base_message}\nStatus code: {self.status_code} | {self} | Description: {self.status_description}"

    @classmethod
    def _validation(cls, response, **xtra_params):
        return response.status_code not in cls.status_code


class RestPyIsInformationalResponse(RestPyStatusCodeException):
    base_message = "Request - NO Informational response"

    @classmethod
    def _validation(cls, response, **xtra_params):
        return not 100 <= response.status_code < 200


class RestPyIsSuccessResponse(RestPyStatusCodeException):
    base_message = "Request - NO Success response"

    @classmethod
    def _validation(cls, response, **xtra_params):
        return not 200 <= response.status_code < 300


class RestPyIsRedirectResponse(RestPyStatusCodeException):
    base_message = "Request - NO Redirect response"

    @classmethod
    def _validation(cls, response, **xtra_params):
        return not 300 <= response.status_code < 400


class RestPyIsClientErrorResponse(RestPyStatusCodeException):
    base_message = "Request - NO Client error response"

    @classmethod
    def _validation(cls, response, **xtra_params):
        return not 400 <= response.status_code < 500


class RestPyIsServerErrorResponse(RestPyStatusCodeException):
    base_message = "Request - NO Server error response"

    @classmethod
    def _validation(cls, response, **xtra_params):
        return not 500 <= response.status_code < 600


class RestPyLoginException(RestPyStatusCodeException):
    status_code = [HTTPStatus.UNAUTHORIZED]
    base_message = "Request - Login error"


class RestPyForbiddenException(RestPyStatusCodeException):
    status_code = [HTTPStatus.FORBIDDEN]
    base_message = "Request - Forbidden"


class RestPyMethodNotAllowedException(RestPyStatusCodeException):
    status_code = [HTTPStatus.METHOD_NOT_ALLOWED]
    base_message = "Request - Method not allowed"


class RESTpyTimeOutException(RestPyStatusCodeException):
    status_code = [HTTPStatus.REQUEST_TIMEOUT]
    base_message = "Request - Request timeout"


class RestPyInternalServerErrorException(RestPyStatusCodeException):
    status_code = [HTTPStatus.INTERNAL_SERVER_ERROR]
    base_message = "Request - Internal server error"
