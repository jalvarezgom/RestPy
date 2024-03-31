from exceptions.base import RESTpyException


class RESTpyStatusCodeException(RESTpyException):
    status_code = None
    base_message = 'Request - There was a problem with the request, check the response'

    @property
    def message(self):
        return f"[RESTpy] Exception:{self.base_message} | Status code: {self.status_code} | {self}"

class RESTpyLoginException(RESTpyStatusCodeException):
    status_code = 401
    base_message = "Request - Login error"

class RESTpyForbiddenException(RESTpyStatusCodeException):
    status_code = 403
    base_message = "Request - Forbidden"

class RESTpyTimeOutException(RESTpyStatusCodeException):
    status_code = 408
    base_message = "Request - Request timeout"

class RESTpyInternalServerErrorException(RESTpyStatusCodeException):
    status_code = 500
    base_message = "Request - Internal server error"
