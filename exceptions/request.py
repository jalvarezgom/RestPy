from exceptions.base import RestPyException, RestPyRunnerException


class RestPyURLNotFoundException(RestPyException):
    base_message = "URL not found"


class RestPyResponseTypeException(RestPyException): ...


class RestPyRequestMethodException(RestPyRunnerException):
    base_message = "Method not allowed"

    @classmethod
    def _validation(cls, value, **xtra_params):
        rp_url = xtra_params.get("url")
        return any([rp_url is None, value not in rp_url.request_methods])
