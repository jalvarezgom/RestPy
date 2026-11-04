from restpy.exceptions.base import RestPyException, RestPyRunnerException


class RestPyURLNotFoundException(RestPyException):
    """No registered endpoint matches the requested name or URL."""

    base_message = "URL not found"


class RestPyConnectionException(RestPyException):
    """A network failure other than a timeout (refused connection, DNS, SSL...)."""

    base_message = "Connection error"


class RestPyURLParamsException(RestPyException):
    """URL params are undeclared, or a placeholder in the URL was left unresolved."""

    base_message = "Invalid URL parameters"


class RestPyResponseTypeException(RestPyException):
    """The response data type is not supported by `DataTypeChoice.parse_response`."""


class RestPyRequestMethodException(RestPyRunnerException):
    """The HTTP verb is not among the endpoint's `request_methods`. Pass the endpoint as `url=`."""

    base_message = "Method not allowed"

    @classmethod
    def _validation(cls, value, **xtra_params):
        rp_url = xtra_params.get("url")
        return any([rp_url is None, value not in rp_url.request_methods])
